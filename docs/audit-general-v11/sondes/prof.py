import cProfile, pstats, io
from django.test import Client
from django.contrib.auth.models import User
c=Client(raise_request_exception=False); c.force_login(User.objects.get(username="chef_service_a"))
c.get("/rapports/bilan/",HTTP_HOST="localhost")
pr=cProfile.Profile(); pr.enable(); c.get("/rapports/bilan/",HTTP_HOST="localhost"); pr.disable()
s=io.StringIO(); pstats.Stats(pr,stream=s).sort_stats("cumulative").print_stats(60)
for l in s.getvalue().splitlines():
    if any(k in l for k in ("reports","render","template","sparkline","svg","graph","bilan")) and "site-packages/django/test" not in l: print("PROF",l.strip()[:170])
