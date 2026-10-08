"""Les comptes rendus existants passent d'un index par libellé à un index par `cle` de ligne de fiche."""
from django.db import migrations


def _table(version):
    """{libellé: cle} des lignes de la version ; un libellé en double est ambigu et reste tel quel."""
    vus, doubles = {}, set()
    for item in version.items.all():
        if item.label in vus:
            doubles.add(item.label)
        vus[item.label] = str(item.cle)
    return {label: cle for label, cle in vus.items() if label not in doubles}


def _convertir(donnees, table):
    """Même contenu, clés réécrites ; rejouable (une clé déjà convertie n'est pas dans la table)."""
    if not isinstance(donnees, dict):
        return donnees
    return {table.get(cle, cle): valeur for cle, valeur in donnees.items()}


def _reindexer(apps, inverse):
    MaintenanceExecution = apps.get_model("maintenance", "MaintenanceExecution")
    tables = {}
    executions = MaintenanceExecution.objects.exclude(version_fiche=None).select_related("version_fiche")
    for execution in executions.iterator(chunk_size=500):
        version = execution.version_fiche
        if version.pk not in tables:
            table = _table(version)
            tables[version.pk] = {cle: label for label, cle in table.items()} if inverse else table
        results = _convertir(execution.results, tables[version.pk])
        mesures = _convertir(execution.measurements, tables[version.pk])
        if (results, mesures) != (execution.results, execution.measurements):
            MaintenanceExecution.objects.filter(pk=execution.pk).update(results=results, measurements=mesures)


def indexer_par_cle(apps, schema_editor):
    _reindexer(apps, inverse=False)


def indexer_par_libelle(apps, schema_editor):
    _reindexer(apps, inverse=True)


class Migration(migrations.Migration):
    dependencies = [("maintenance", "0008_compte_rendu_historique")]
    operations = [migrations.RunPython(indexer_par_cle, indexer_par_libelle)]
