"""Tests du rôle transverse « responsable de classe de navire »
(org.models.ResponsableClasseNavire), tâche Notion « Dashboards transverses
par spécialité et par classe de navire »."""
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from org.models import ResponsableClasseNavire


class ResponsableClasseNavireModeleTests(TestCase):
    def test_un_meme_marin_ne_peut_pas_etre_designe_deux_fois_pour_la_meme_classe(self):
        marin = User.objects.create_user(username="marin", password="pass")
        ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=marin)
        with self.assertRaises(IntegrityError):
            ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=marin)

    def test_un_marin_peut_etre_responsable_de_plusieurs_classes(self):
        marin = User.objects.create_user(username="marin2", password="pass")
        ResponsableClasseNavire.objects.create(classe_navire="La Fayette", user=marin)
        ResponsableClasseNavire.objects.create(classe_navire="Suffren", user=marin)
        self.assertEqual(ResponsableClasseNavire.objects.filter(user=marin).count(), 2)
