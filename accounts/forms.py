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
        # Filtrer les rôles disponibles (hors MASTER_ADMIN qui est réservé)
        active_codes = list(RoleAvailability.objects.filter(active=True).values_list("code", flat=True))
        if active_codes:
            self.fields["role"].choices = [c for c in self.fields["role"].choices if c[0] in active_codes]

    def clean(self):
        donnees = super().clean()
        if equipage_manquant(donnees.get("ship"), donnees.get("equipage")):
            self.add_error("equipage", MESSAGE_EQUIPAGE_OBLIGATOIRE)
        return donnees
