from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.static import serve as serve_static
from .views import logout_then_login, SettingsView
from django.conf import settings
from django.conf.urls.static import static
from .views import global_search
from dashboard.web_views import TableauDeBordView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Le Service Worker doit être servi à la racine (scope "/") pour couvrir
    # tout le site, pas seulement /static/js/ (limite du scope Web Push par
    # défaut : la portée est celle du chemin de service du fichier).
    path(
        "service-worker.js",
        serve_static,
        {"document_root": settings.BASE_DIR / "matrix" / "static" / "js", "path": "service-worker.js"},
        name="service-worker",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    # Raccourcis conviviaux
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", logout_then_login, name="logout"),
    path("api/accounts/", include("accounts.urls")),
    path("api/org/", include("org.urls")),
    path("api/assets/", include("assets.urls")),
    path("api/maintenance/", include("maintenance.urls")),
    path("api/logistics/", include("logistics.urls")),
    path("api/training/", include("training.urls")),
    path("api/threads/", include("threads.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("dashboard/", include("dashboard.web_urls")),
    path("calendar/", include("calendar_app.urls")),
    path("users/", include("accounts.web_urls")),
    path("parametre/", SettingsView.as_view(), name="settings"),
    path("maintenance/", include("maintenance.web_urls")),
    path("logistics/", include("logistics.web_urls")),
    path("formations/", include("training.web_urls")),
    path("", include("assets.web_urls")),
    path("", include("reports.web_urls")),
    path("search/", global_search, name="global-search"),
    path("", TableauDeBordView.as_view(), name="home"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Matrix Administration"
admin.site.site_title = "Matrix Admin"
admin.site.index_title = "Gestion à bord"
