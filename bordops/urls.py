from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from .views import logout_then_login, SettingsView
from django.conf import settings
from django.conf.urls.static import static
from .views import global_search

urlpatterns = [
    path("admin/", admin.site.urls),
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
    path("calendar/", include("calendar_app.urls")),
    path("users/", include("accounts.web_urls")),
    path("parametre/", SettingsView.as_view(), name="settings"),
    path("maintenance/", include("maintenance.web_urls")),
    path("logistics/", include("logistics.web_urls")),
    path("", include("assets.web_urls")),
    path("search/", global_search, name="global-search"),
    path("", login_required(TemplateView.as_view(template_name="dashboard/index.html")), name="home"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "BordOps Administration"
admin.site.site_title = "BordOps Admin"
admin.site.index_title = "Gestion à bord"
