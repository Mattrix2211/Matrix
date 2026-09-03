from rest_framework import serializers
from .models import UserProfile, GradeChoice, SpecialityChoice, RoleAvailability
from django.contrib.auth.models import User
from matrix.core.scopes import is_master_admin, resoudre_affectation_dans_perimetre

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def validate(self, attrs):
        """Valide que le navire/service/secteur/section de destination
        appartient au périmètre de l'appelant, exactement comme le fait déjà
        l'annuaire web (cf. matrix/core/scopes.py::
        resoudre_affectation_dans_perimetre) : un COMMANDANT ou un
        ADMIN_NAVIRE ne peut affecter un profil qu'à son propre navire (ou à
        un service/secteur/section qui en dépend) ; MASTER_ADMIN (et un
        superutilisateur) garde une liberté totale sur la flotte entière.

        Avant correction, cette API acceptait n'importe quel id de navire/
        service/secteur/section transmis dans le payload sans vérifier qu'il
        appartenait au périmètre de l'appelant (même classe de faille que
        celle corrigée côté web dans create_user/edit_user/bulk_update_*).
        """
        request = self.context.get("request")
        acting_user = getattr(request, "user", None)
        if acting_user is None or is_master_admin(acting_user):
            return attrs
        ship = attrs.get("ship")
        service = attrs.get("service")
        sector = attrs.get("sector")
        section = attrs.get("section")
        if ship is None and service is None and sector is None and section is None:
            return attrs
        ok, *_ = resoudre_affectation_dans_perimetre(
            acting_user,
            ship_id=ship.id if ship else None,
            service_id=service.id if service else None,
            sector_id=sector.id if sector else None,
            section_id=section.id if section else None,
        )
        if not ok:
            raise serializers.ValidationError(
                "Unité, service, secteur ou section invalide, ou hors de votre périmètre."
            )
        return attrs


class GradeChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeChoice
        fields = "__all__"


class SpecialityChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialityChoice
        fields = "__all__"


class RoleAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAvailability
        fields = "__all__"
