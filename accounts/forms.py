from django import forms
from matrix.core.equipage import MESSAGE_EQUIPAGE_OBLIGATOIRE, equipage_manquant
from .models import UserProfile, RoleAvailability


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "grade",
            "specialite",
            "matricule",
            "role",
            "fonction_coma",
            "equipage",
            "ship",
            "service",
            "sector",
            "section",
            "allowed_sectors",
        ]
        widgets = {
            "allowed_sectors": forms.SelectMultiple(attrs={"size": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Un rôle sans ligne RoleAvailability est actif (comme dans les Réglages).
        desactives = set(RoleAvailability.objects.filter(active=False).values_list("code", flat=True))
        self.fields["role"].choices = [c for c in self.fields["role"].choices if c[0] not in desactives]

    def clean(self):
        donnees = super().clean()
        if equipage_manquant(donnees.get("ship"), donnees.get("equipage")):
            self.add_error("equipage", MESSAGE_EQUIPAGE_OBLIGATOIRE)
        return donnees
