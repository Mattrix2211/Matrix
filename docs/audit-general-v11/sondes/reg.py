from matrix.core.role_thresholds import REGISTRE_ACTIONS
for a in REGISTRE_ACTIONS:
    print("REG|%s|%s|%s|%s|second=%s"%(a.cle,a.categorie if hasattr(a,'categorie') else getattr(a,'groupe',''),a.portee,a.defaut.name,getattr(a,'ouverte_au_second',None)))
