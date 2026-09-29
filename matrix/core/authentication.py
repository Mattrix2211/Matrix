"""Authentification DRF appliquant la lecture seule de l'équipage à terre
(double équipage) à TOUTES les vues de l'API, quelle que soit leur classe de
permission. Remplace SessionAuthentication et BasicAuthentication dans
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']."""
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS

MESSAGE_LECTURE_SEULE = "Votre équipage est à terre : le bâtiment est en lecture seule pour vous."


class _LectureSeuleMixin:
    def authenticate(self, request):
        resultat = super().authenticate(request)
        if resultat is None:
            return None
        from org.equipages import ecriture_autorisee_a_terre, est_en_lecture_seule

        user = resultat[0]
        if (
            request.method not in SAFE_METHODS
            and not ecriture_autorisee_a_terre(request.method, request.path)
            and est_en_lecture_seule(user)
        ):
            raise PermissionDenied(MESSAGE_LECTURE_SEULE)
        return resultat


class SessionAuthentificationLectureSeule(_LectureSeuleMixin, SessionAuthentication):
    pass


class BasicAuthentificationLectureSeule(_LectureSeuleMixin, BasicAuthentication):
    pass
