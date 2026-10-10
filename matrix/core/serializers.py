from rest_framework import serializers

from .mixins import build_scope_q


class ReferencesDansPerimetreMixin:
    """Refuse (400) qu'un champ relationnel pointe vers un objet hors du
    périmètre de l'appelant (navire/service/secteur/section), avec la même
    traduction de périmètre que la lecture (`build_scope_q`).

    Le serializer déclare `references_perimetre = {"champ": (chemins...)}` ;
    chaque chemin est celui attendu par `build_scope_q` (préfixe ou dict).
    Sans périmètre défini (ex. administrateur général), aucune restriction,
    comme pour la lecture."""

    references_perimetre = {}

    def validate(self, attrs):
        attrs = super().validate(attrs)
        utilisateur = getattr(self.context.get("request"), "user", None)
        if utilisateur is None:
            return attrs
        for champ, chemins in self.references_perimetre.items():
            cible = attrs.get(champ)
            if cible is None:
                continue
            modele = type(cible)
            if not modele.objects.filter(build_scope_q(utilisateur, *chemins), pk=cible.pk).exists():
                raise serializers.ValidationError({champ: "Cet élément est hors de votre périmètre."})
        return attrs
