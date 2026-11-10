import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')
application = get_wsgi_application()

from matrix.core.instance_demo import exiger_pas_de_base_de_demo_en_production  # noqa: E402

exiger_pas_de_base_de_demo_en_production()  # un serveur d'application ne passe pas par les checks de manage.py
