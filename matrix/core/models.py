from django.conf import settings
from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class OwnedModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_%(class)s_set"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_%(class)s_set"
    )

    class Meta:
        abstract = True


class Brouillon(TimeStampedModel):
    """Saisie en cours enregistrée côté serveur (docs/UX.md §5.4).

    Un seul brouillon actif par (utilisateur, clé). La clé est un identifiant
    stable de la forme « formulaire:objet » (ex. « compte-rendu:42 »). Un
    brouillon est strictement personnel : jamais lisible par un autre
    utilisateur, jamais partagé. Il est transitoire (purgé après la durée de
    conservation) : la donnée métier, elle, est tracée par l'AuditLog au moment
    de l'enregistrement définitif.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="brouillons")
    cle = models.CharField("clé du formulaire", max_length=120)
    contenu = models.JSONField("contenu des champs", default=dict)
    libelle = models.CharField("libellé", max_length=200, blank=True, default="")
    url = models.CharField("adresse de reprise", max_length=300, blank=True, default="")

    class Meta:
        verbose_name = "brouillon"
        verbose_name_plural = "brouillons"
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user", "cle"], name="brouillon_unique_par_utilisateur_et_cle")]

    def __str__(self):
        return f"{self.cle} ({self.user})"
