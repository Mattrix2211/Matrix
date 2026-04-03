from django import forms
from .models import UserProfile, RoleAvailability


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "grade",
            "specialite",
            "matricule",
            "role",
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
