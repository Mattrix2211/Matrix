"""Processus Django indépendant, piloté par le test de cohérence multi-processus.

Chaque commande reçue s'exécute comme une requête (ou une tâche Celery) : le
cache local du processus est donc celui d'un vrai worker web ou Celery."""


def serveur(connexion):
    import django

    django.setup()
    from celery.signals import task_postrun, task_prerun
    from django.core.management import call_command

    import matrix.celery  # noqa: F401  (branche les signaux de tâche)
    from matrix.core.config_version import fermer_contexte, ouvrir_contexte
    from matrix.core.modules import module_actif
    from matrix.core.role_thresholds import seuil_role
    from org.models import ModuleActivation, RoleThresholdConfig, Ship

    def preparer():
        call_command("migrate", verbosity=0)

    def creer_navire():
        return Ship.objects.create(name="Unité deux processus", code="DEUX-PROC").pk

    def lire_seuil(ship_id, cle):
        return seuil_role(cle, ship_id).name

    def ecrire_seuil(ship_id, cle, nom):
        config, _ = RoleThresholdConfig.objects.get_or_create(ship_id=ship_id)
        config.thresholds[cle] = nom
        config.save(update_fields=["thresholds", "updated_at"])

    def lire_module(ship_id, module):
        return module_actif(module, ship_id)

    def basculer_module(ship_id, module, actif):
        ModuleActivation.objects.update_or_create(ship_id=ship_id, module=module, defaults={"active": actif})

    def nettoyer(ship_id):
        Ship.objects.filter(pk=ship_id).delete()

    commandes = {
        "creer_navire": creer_navire, "lire_seuil": lire_seuil, "ecrire_seuil": ecrire_seuil, "lire_module": lire_module,
        "basculer_module": basculer_module, "nettoyer": nettoyer,
    }
    while True:
        nom, args, en_tache = connexion.recv()
        if nom == "arreter":
            return
        try:
            if nom == "preparer":
                resultat = preparer()
            else:
                if en_tache:
                    task_prerun.send(sender=None)
                else:
                    ouvrir_contexte()
                try:
                    resultat = commandes[nom](*args)
                finally:
                    if en_tache:
                        task_postrun.send(sender=None)
                    else:
                        fermer_contexte()
            connexion.send(("ok", resultat))
        except Exception as erreur:  # remonté au test parent
            connexion.send(("erreur", repr(erreur)))
