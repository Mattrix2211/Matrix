import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')
import django
django.setup()
from django.contrib.auth import get_user_model

U = get_user_model()
username = 'admin'
password = 'adminpass'
email = 'admin@example.com'
if not U.objects.filter(username=username).exists():
    U.objects.create_superuser(username, email, password)
    print('created')
else:
    print('exists')
