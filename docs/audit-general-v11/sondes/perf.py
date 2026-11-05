import time, statistics
from django.test import Client
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
pages=["/","/rapports/bilan/","/quarts/","/calendar/","/maintenance/gestion/occurrences/","/logistics/tickets/","/taches/","/dashboard/comanav/","/assets/"]
for u in ("chef_service_a","cdt_a"):
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u))
    for p in pages:
        t=[]; 
        for i in range(8):
            with CaptureQueriesContext(connection) as q:
                s=time.perf_counter(); r=c.get(p,HTTP_HOST="localhost"); t.append(time.perf_counter()-s)
        print("PERF",u,p,r.status_code,"médiane %.0f ms"%(statistics.median(t)*1000),"min %.0f max %.0f"%(min(t)*1000,max(t)*1000),"requêtes SQL",len(q),"taille %d Ko"%(len(r.content)//1024))
from django.contrib.auth.models import User as U
