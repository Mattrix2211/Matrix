# Nouveaux écarts du logiciel (NE-01 à NE-07)

## NE-01 — Bouton « Exécuter » affiché sans droit d'exécution

| Rubrique | Contenu |
|---|---|
| **Constat** | La liste de maintenance affiche « Exécuter » pour des occurrences que le serveur refuse (403) à l'utilisateur ; le bouton « M'assigner » existe aussi. |
| **Profils concernés** | marins ; chefs de section |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/navigateur_droits.md |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-02 — Lignes de tickets cliquables sans lien ni focus clavier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les lignes de la liste des tickets s'ouvrent par un gestionnaire de clic sur la ligne seulement ; non accessible au clavier. |
| **Profils concernés** | tous profils |
| **Niveau de preuve** | [C] |
| **Preuve** | matrix/templates/logistics/ticket_list.html (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-03 — Redirection HTTPS sans réglage de proxy inverse

| Rubrique | Contenu |
|---|---|
| **Constat** | SECURE_SSL_REDIRECT est actif en production sans réglage de proxy TLS ; comportement derrière un proxy non testé. |
| **Profils concernés** | exploitants ; SIC |
| **Niveau de preuve** | [C][?] |
| **Preuve** | chapitre « Exploitation » du dossier technique |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-04 — QR codes liés au nom d'hôte de la requête

| Rubrique | Contenu |
|---|---|
| **Constat** | Le QR d'un équipement encode l'adresse absolue de la requête ; un QR imprimé depuis un autre nom d'hôte pointe vers une adresse erronée ; non documenté avant l'audit. |
| **Profils concernés** | exploitants ; gestionnaires de matériel |
| **Niveau de preuve** | [C] |
| **Preuve** | assets/views.py (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-05 — Codes de refus 404 et 403 hétérogènes

| Rubrique | Contenu |
|---|---|
| **Constat** | L'équipier reçoit 404 sur certaines pages d'écriture (nouvelle documentation, passation) et 403 sur la plupart des autres ; masquage volontaire ou incohérence non documentée. |
| **Profils concernés** | marins |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/navigateur_droits.md |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-06 — Synthèse de passation lisible par l'équipage sortant

| Rubrique | Contenu |
|---|---|
| **Constat** | Les chefs de l'équipage sortant, passé à terre, lisent la synthèse figée ; conforme au code, mais l'écart A14 les concerne aussi. |
| **Profils concernés** | chefs de l'équipage sortant |
| **Niveau de preuve** | [N] |
| **Preuve** | audit_preuves/a14_navigateur_chef_section.png |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

## NE-07 — Message de fin de compte rendu inexact pour une installation

| Rubrique | Contenu |
|---|---|
| **Constat** | À la fin d'un compte rendu non conforme, l'écran annonce « Un ticket correctif sera (ou a été) ouvert automatiquement » pour toute échéance, y compris celle d'une installation, pour laquelle le code ne crée aucun ticket (navigateur, 14/11/2026 : échéance « En validation », 0 ticket créé). Le lien « signaler une anomalie » de cet écran n'apparaît que pour un relevé chiffré hors plage, pas pour un contrôle non conforme. |
| **Profils concernés** | marins ; chefs de section ; responsables des installations |
| **Niveau de preuve** | [N][C] |
| **Preuve** | audit_preuves/maintenance_non_conforme_installation_fin_de_compte_rendu.png ; matrix/templates/maintenance/_execute_done.html:3-4 (accès restreint) |
| **Statut** | documenté, non arbitré (pas une autorisation de modifier le logiciel) |

