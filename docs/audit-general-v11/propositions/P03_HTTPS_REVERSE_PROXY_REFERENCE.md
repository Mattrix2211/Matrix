# P03 — Architecture de référence HTTPS : reverse proxy avec terminaison TLS (DP-10)

**Statut : documentation d'étude ; non déployée ; à valider par les responsables SIC avant tout déploiement.** Aucune règle de sécurité militaire n'est inventée ici : les points qui relèvent de la politique SSI sont signalés comme tels.

## 1. Schéma

```
Poste du bord ──HTTPS (certificat interne)──▶ Reverse proxy (TLS) ──HTTP, boucle locale ou socket──▶ Serveur d'application Matrix ──▶ PostgreSQL / Redis (boucle locale)
```

Le proxy porte le certificat, l'application n'écoute que sur la boucle locale (ou un socket Unix) : **elle ne doit pas être joignable autrement que par le proxy**.

## 2. Réglages Django nécessaires (validés par simulation)

Essai réalisé avec un module de réglages complémentaire hors dépôt (`sondes/config/reglages_proxy.py`) et le client de test, mode production (`DJANGO_DEBUG=0`), script `sondes/prod_proxy_reglages.py` :

| Réglage | Valeur de référence | Pourquoi | Aujourd'hui dans le dépôt |
|---|---|---|---|
| `SECURE_PROXY_SSL_HEADER` | `("HTTP_X_FORWARDED_PROTO", "https")` | sans lui, l'application croit être en HTTP et redirige en boucle (301) | **absent** (`None`), non pilotable par l'environnement |
| `CSRF_TRUSTED_ORIGINS` | `["https://<nom-interne-du-serveur>"]` | l'`Origin` d'un formulaire HTTPS doit être reconnu | figé sur `localhost:8000` (HTTP), non pilotable |
| `ALLOWED_HOSTS` | nom interne du serveur | contrôle de l'en-tête `Host` | **pilotable** (`DJANGO_ALLOWED_HOSTS`) |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT` | vrais en production | cookies jamais envoyés en clair | **déjà** liés à `DEBUG=0` |
| `SECURE_HSTS_SECONDS` | valeur croissante (par exemple 3600 puis 31536000) après validation | oblige les navigateurs à rester en HTTPS | absent (avertissement `security.W004`) |
| `USE_X_FORWARDED_HOST` | faux (le proxy transmet `Host` tel quel) | évite de faire confiance à un en-tête de plus | défaut Django |

Résultats de la simulation :

| Essai | Résultat |
|---|---|
| requête du proxy avec `X-Forwarded-Proto: https` | 200 |
| requête en HTTP direct, sans en-tête | 301 vers HTTPS |
| requête du proxy avec `X-Forwarded-Proto: http` | 301 |
| formulaire de connexion avec `Origin` cohérent | 200 |
| formulaire avec `Origin` étranger | **403** (protection CSRF active) |
| cookies de session et CSRF | marqués `Secure` ; en-tête `Strict-Transport-Security` émis |

## 3. Conditions de confiance envers le proxy (point de sécurité)

Faire confiance à `X-Forwarded-Proto` revient à croire quiconque l'envoie : **un client qui atteindrait directement l'application pourrait se faire passer pour une connexion HTTPS** (essai : l'application répond 200 à un client direct qui envoie l'en-tête). Conditions cumulatives :
1. l'application n'écoute que sur la boucle locale ou un socket, jamais sur l'interface du réseau du bord ;
2. le proxy **écrase** toujours l'en-tête (il ne le retransmet jamais tel que reçu) ;
3. un seul proxy dans la chaîne, ou chaîne entièrement maîtrisée ;
4. règles de pare-feu locales interdisant l'accès direct au port de l'application ;
5. journalisation du proxy conservée (c'est lui qui voit l'adresse du poste).

## 4. Exemple de configuration du proxy (à adapter)

```
server {
    listen 443 ssl;
    server_name <nom-interne>;
    ssl_certificate     /chemin/certificat.pem;
    ssl_certificate_key /chemin/cle.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;      # valeur fixe, jamais $http_x_forwarded_proto
        proxy_set_header X-Forwarded-For $remote_addr;  # jamais retransmis tel que reçu
    }
    location /media-interne/ { internal; alias /chemin/vers/media/; }   # déjà documenté pour MEDIA_ACCEL_REDIRECT
}
server { listen 80; server_name <nom-interne>; return 301 https://$host$request_uri; }
```

Le dépôt ne déclare **aucun serveur d'application** (gunicorn, waitress, uvicorn) : il est à choisir, à installer hors ligne et à superviser (reprise après redémarrage). Le service de fichiers du service worker et le Web Push exigent un contexte sécurisé : HTTPS est aussi une condition fonctionnelle.

## 5. Options de certificats internes (réseau sans Internet)

| Option | Principe | Avantages | Points d'attention |
|---|---|---|---|
| **A — PKI de l'organisation** | certificat émis par l'autorité interne existante | confiance déjà présente sur les postes ; conforme à la politique | délais de demande ; renouvellement ; à confirmer avec les responsables SIC |
| **B — Autorité locale du bord** (outil de PKI léger) | une AC dédiée au bâtiment signe le certificat du serveur | autonome, renouvellement local | l'AC doit être installée sur chaque poste ; protection de la clé de l'AC ; validation SSI |
| **C — Certificat auto-signé** | un certificat unique par serveur | immédiat | avertissements navigateur sur postes partagés, habituation à les ignorer : déconseillé hors essai |

Dans tous les cas : durée de vie courte, procédure de renouvellement écrite, nom de serveur stable (le certificat y est lié), distribution de l'AC sur les postes partagés, sauvegarde de la clé.

## 6. Liste de contrôle pour la validation SIC

Architecture et segmentation ; propriété de l'AC et durée des certificats ; chiffrement entre proxy et application (nécessaire ou non en boucle locale) ; pare-feu local ; journalisation et conservation ; supervision du proxy et de l'application ; compatibilité des navigateurs des postes ; Web Push (clé VAPID, contexte sécurisé) ; procédure de coupure et de reprise.

## 7. Travaux nécessaires côté produit (non lancés)

Rendre `SECURE_PROXY_SSL_HEADER` et `CSRF_TRUSTED_ORIGINS` configurables par l'environnement ; documenter l'installation de référence ; choisir et déclarer le serveur d'application ; tester l'installation sur une machine vierge. Voir AUD-011.
