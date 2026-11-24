# Recette sur iPhone par réseau Wi-Fi privé temporaire — méthode proposée

Statut : **projet, non appliqué**. Aucun script n'est modifié et aucun accès réseau n'est ouvert tant que la méthode n'est pas validée.

## 1. Constat sur l'existant

- La démonstration (`lancer_demo.bat`, `scripts/preparer_instance_test.py --servir`) écoute en dur sur `127.0.0.1:8800` ; l'hôte « n'est jamais configurable ».
- Le script construit l'environnement du serveur en liste blanche (base SQLite de démonstration, courriel en mémoire, tâches Celery en mémoire, aucune clé d'envoi) et **refuse** de démarrer si les hôtes autorisés ne sont pas locaux (`verifier_isolement`).
- Le verrou L01 repose sur le marqueur d'instance de démonstration ; L05 (secrets de production) ne s'applique qu'hors `DEBUG`.
- L'instance de démonstration tourne avec `DJANGO_DEBUG=1`, en HTTP simple (cookies non « Secure », pas de redirection HTTPS).
- Conséquence : l'iPhone ne peut pas joindre la démonstration en l'état, et lancer `runserver` à la main sur une adresse réseau **contournerait les contrôles d'isolation du script** : ne pas le faire.

## 2. Méthode recommandée (à développer après accord)

Ajouter au script, sans changer son comportement par défaut, une option explicite et temporaire, par exemple `--servir --reseau-prive <adresse>` qui :

1. refuse toute adresse qui n'est pas une adresse privée (10.x, 172.16–31.x, 192.168.x) ou qui n'appartient pas à la machine ;
2. écoute **uniquement sur cette adresse** (jamais `0.0.0.0`) et ajoute cette seule adresse aux hôtes autorisés et aux origines CSRF de ce processus ; la configuration normale n'est pas modifiée ;
3. n'accepte que la base de démonstration marquée (L01 inchangé) ; en cas de doute, refus ;
4. exige de régénérer les comptes juste avant (`--reinitialiser`) : mots de passe aléatoires, non réutilisés d'une séance à l'autre ;
5. s'arrête seul après une durée limitée (120 min par défaut) ;
6. n'affiche ni mot de passe ni adresse en dehors de ce qui est nécessaire.

Les droits pare-feu et le choix du réseau sont des gestes de l'opérateur (§3), pas du script.

## 3. Procédure de séance (poste Windows, PowerShell administrateur pour le pare-feu)

**Avant**
1. Connecter le PC et l'iPhone au **même réseau Wi-Fi privé de confiance** (pas de réseau d'invités, hôtel, point d'accès public). Variante recommandée : **partage de connexion de l'iPhone** auquel se connecte le PC : réseau privé direct, sans routeur ni box.
2. Windows : profil réseau « Privé » ; relever l'adresse du PC (`ipconfig`) et celle de l'iPhone (Réglages > Wi-Fi > i).
3. Vérifier qu'**aucune redirection de port** n'existe sur la box (aucune création à faire) et que le port 8800 n'est pas exposé.
4. Préparer des comptes neufs : `python scripts\preparer_instance_test.py --reinitialiser`, puis lire les mots de passe sur le poste seulement.
5. Règle de pare-feu temporaire, limitée au port, au profil privé et à l'adresse de l'iPhone :
   `New-NetFirewallRule -DisplayName "Matrix recette iPhone" -Direction Inbound -Protocol TCP -LocalPort 8800 -RemoteAddress <adresse iPhone> -Profile Private -Action Allow`

**Pendant**
6. Lancer le serveur en mode réseau privé (option à créer) ; sur l'iPhone, ouvrir `http://<adresse du PC>:8800/` dans Safari.
7. Rôles à jouer : voir `PARCOURS_RECETTE_PO_V11.md` ; ne saisir que des données fictives.

**Après (fermeture obligatoire)**
8. Arrêter le serveur (Ctrl+C ou fin de durée).
9. `Remove-NetFirewallRule -DisplayName "Matrix recette iPhone"`.
10. Vérifier : `Get-NetTCPConnection -LocalPort 8800` ne renvoie plus d'écoute ; `Get-NetFirewallRule -DisplayName "Matrix recette iPhone"` renvoie une erreur (règle absente) ; désactiver le partage de connexion si utilisé.
11. Dans Safari : supprimer les données du site pour l'adresse utilisée. Recommencer par `--reinitialiser` à la séance suivante.

## 4. Risques et limites

- **Exposition** : tant que le serveur écoute, toute machine du réseau privé autorisée par le pare-feu peut atteindre la page de connexion ; la règle limitée à l'adresse de l'iPhone réduit l'exposition à un seul appareil. L'adresse d'un iPhone peut changer : revérifier avant de relancer.
- **Mode `DEBUG`** : la démonstration tourne avec `DEBUG` actif (traces d'erreur détaillées). Sur le réseau privé, une erreur peut montrer des chemins et des réglages à l'appareil connecté. Acceptable pour une séance courte avec données fictives et un seul appareil autorisé ; pas pour un usage plus large.
- **Pas de HTTPS** : la connexion et le cookie de session circulent en clair sur le Wi-Fi. Risque limité par le réseau privé et les données fictives, mais à ne jamais réutiliser un mot de passe réel.
- **Safari et contexte sécurisé** : en HTTP simple (hors `localhost`), Safari ne fournit pas un contexte sécurisé. Conséquences : pas de service worker, pas d'installation en application web avec fonctions hors ligne, **pas de Web Push** (sur iOS, le push exige HTTPS et une application ajoutée à l'écran d'accueil), certaines API (presse-papiers, capteurs, caméra) peuvent être refusées. Le fichier `push.js` ne pourra pas être éprouvé, et la démonstration désactive de toute façon l'envoi réel de notifications.
- **HTTPS auto-signé** : possible (certificat local installé et approuvé sur l'iPhone), mais cela impose d'installer un profil de confiance sur l'appareil et d'ajuster la configuration (cookies « Secure »). Non recommandé à ce stade : à réserver à une recette spécifique des notifications.
- **Hors périmètre** : performances réelles en mer, réseaux navire, mode hors connexion.

## 5. Ce qui reste à décider

1. Valider la méthode (option du script plus procédure) ou préférer la simulation sur le poste.
2. Réseau retenu : partage de connexion iPhone (recommandé) ou Wi-Fi privé domestique.
3. Durée maximale d'une séance.
