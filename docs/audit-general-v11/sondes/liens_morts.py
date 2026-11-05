import re, json, collections
from django.test import Client
from django.contrib.auth.models import User
EXCL=("/static","/media","/accounts/logout","/logout","/admin","/service-worker")
def liens(html): return sorted({h for h in re.findall(r'href="(/[^"#?]*)"', html) if not h.startswith(EXCL)})
users=list(User.objects.filter(is_active=True).order_by("username").values_list("username",flat=True))
morts=collections.defaultdict(list); n=0; erreurs5=[]
for u in users:
    c=Client(raise_request_exception=False); c.force_login(User.objects.get(username=u))
    r=c.get("/",HTTP_HOST="localhost"); 
    if r.status_code!=200: morts[("/",r.status_code)].append(u); continue
    niv1=liens(r.content.decode()); vus={"/"}
    for h in niv1:
        rr=c.get(h,HTTP_HOST="localhost"); n+=1; vus.add(h)
        if rr.status_code>=500: erreurs5.append((u,h,rr.status_code))
        if rr.status_code in (403,404): morts[(h,rr.status_code,"niv1")].append(u)
        if rr.status_code==200 and "text/html" in rr.headers.get("Content-Type",""):
            for h2 in liens(rr.content.decode("utf-8","ignore")):
                if h2 in vus or h2.count("/")>5 and False: continue
                vus.add(h2); r2=c.get(h2,HTTP_HOST="localhost"); n+=1
                if r2.status_code>=500: erreurs5.append((u,h2,r2.status_code))
                if r2.status_code in (403,404): morts[(h2,r2.status_code,"niv2 via "+h)].append(u)
print("UTILISATEURS",len(users),"REQUETES",n)
print("ERREURS_5XX",erreurs5[:20],len(erreurs5))
agg=collections.Counter()
for (h,code,*rest),us in morts.items():
    gen=re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}","<uuid>",re.sub(r"/\d+","/<n>",h))
    agg[(gen,code)]+=len(us)
for (g,c),k in agg.most_common(30): print("MORT",c,g,"x",k)
for (h,code,*rest),us in sorted(morts.items(), key=lambda x:str(x[0])):
    print("DETAIL",code,h,rest,sorted(us))
