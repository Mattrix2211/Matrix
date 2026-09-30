from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Roles, UserProfile, GradeChoice, SpecialityChoice, RoleAvailability
from django.contrib.auth.models import User
from matrix.core.scopes import is_master_admin, resoudre_affectation_dans_perimetre

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]

class UserProfileSerializer(serializers.ModelSerializer):
    # Le compte lié n'est jamais modifiable ni réassignable via le profil.
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "id", "user", "role", "grade", "specialite", "fonction_service", "matricule",
            "date_naissance", "notification_time", "notification_time_soir",
            "ship", "service", "sector", "section", "equipage", "allowed_sectors",
            "created_at", "updated_at",
        )
        # `allowed_sectors` (accès à d'autres secteurs) se gère uniquement
        # depuis l'annuaire web, avec ses contrôles de périmètre.
        read_only_fields = ("id", "allowed_sectors", "created_at", "updated_at")

    def update(self, instance, validated_data):
        """Traduit le refus « titulaire de poste COMA / commandant en second »
        (levé par UserProfile.save) en erreur 400 avec son message français,
        au lieu d'une erreur serveur 500."""
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as erreur:
            raise serializers.ValidationError({"equipage": erreur.messages})

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
        # Seule la gestion de la flotte entière peut créer un MASTER_ADMIN :
        # sinon un administrateur de bord pourrait s'élever lui-même.
        if attrs.get("role") == Roles.MASTER_ADMIN:
            raise serializers.ValidationError({"role": "Vous ne pouvez pas attribuer ce rôle."})
        equipage = attrs.get("equipage")
        if equipage is not None:
            navire_cible = attrs.get("ship") or getattr(self.instance, "ship", None)
            if navire_cible is None or equipage.ship_id != navire_cible.id:
                raise serializers.ValidationError(
                    {"equipage": "Cet équipage n'appartient pas à l'unité du marin."}
                )
            ok, *_ = resoudre_affectation_dans_perimetre(acting_user, ship_id=equipage.ship_id)
            if not ok:
                raise serializers.ValidationError({"equipage": "Équipage hors de votre périmètre."})
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
        fields = ("id", "name", "active")


class SpecialityChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialityChoice
        fields = ("id", "name", "active")


class RoleAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAvailability
        fields = ("id", "code", "active")
