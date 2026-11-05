# Matrice de conformité — version finale de la 3ᵉ passe

Commit audité `1c37f22`, 2026-11-05. États : **V-C** vérifié conforme ; **V-NC** vérifié non conforme ; **PC** partiellement conforme ; **NV** non vérifié ; **DIFF** volontairement différé ; **ABS** absent, sans exigence de développement ; **ARB** à arbitrer. Un état « V-C » est limité au périmètre écrit dans la colonne Preuve.

| Exigence | Intitulé | État | Preuve | Audit |
|---|---|---|---|---|
| EX-001 | Matrix = plateforme quotidienne, GMAO = un module | PC | 22 applications dont la GMAO en un module ; accueil rejoué (7 profils) ; la valeur quotidienne n'est pas mesurable sans usage réel | 04, 05 |
| EX-002 | Aucune règle susceptible d'évoluer en dur | V-NC partiel | 35 actions réglables par bâtiment, mais 55 comparaisons en dur (AUD-022) et structure non autonome (AUD-019) | 02 |
| EX-003 | Internet n'existe pas | V-C (code statique) | aucune ressource externe (gabarits, styles, scripts ; 7 profils en navigateur) ; réseau réel non testé | 15 |
| EX-004 | Tout est traçable, jamais d'écrasement silencieux | PC | AuditLog sur visas, stock, maintenance critique, désignations ; mais suppression d'unités sans trace par personne touchée (AUD-020) | 14, 15 |
| EX-005 | Proposer → valider → publier | PC | circuit de la feuille rejoué ; voies directes sur listes publiées (AUD-015) ; documents/RETEX non rejoués | 09, 12 |
| EX-006 | Administration distribuée | PC | seuils et modules par bâtiment : oui ; structure : non (AUD-019) | 02 |
| EX-007 | Droits non déduits du seul grade ; vérification côté serveur | PC | contrôles serveur confirmés (1 407 + 196 essais) ; plusieurs droits par niveau (AUD-014) | 06 |
| EX-008 | Non-surcharge | NV | 6 à 13 cartes d'accueil, 23 à 29 liens de menu : densité non comparée aux maquettes | 05 |
| EX-009 | Tolérance aux coupures bord–terre | DIFF | Phase 7 volontairement différée | 13 |
| EX-010 | Le marin voit sa journée à l'ouverture | PC | accueil fonctionnel pour 7 profils ; liens morts (AUD-016) ; justesse du contenu non évaluée | 04 |
| EX-011 | Calendrier unique | V-C (structure) | 7 sources dans un même flux ; conflits non détectés (D-06 au backlog) | 07 |
| EX-012 | Calendrier, colonne vertébrale du pilotage | NV | vues collectives et pilotage non rejoués | 07 |
| EX-013 | Recherche universelle | NV | champ présent, non testé | 05 |
| EX-014 | Notifications explicites | NV | contenu non évalué ; accès par propriétaire conforme | 11 |
| EX-020 | Chef de liste | PC | désignation et droits de gestion rejoués ; modification d'une liste publiée par proposition absente (D-05 A) | 09 |
| EX-021 | Génération automatique abandonnée | V-C | aucun générateur dans quarts/ | 09, 19 |
| EX-022 | Aucun rythme de quart en dur ; régimes | PC | aucune durée en dur hors affichage ; régimes nommés non implémentés (cadrage sans GO) | 09, 19 |
| EX-023 | « Hommes morts » et « de musique » | ABS (cadrage) | aucune occurrence dans le code ; développement non autorisé | 19 |
| EX-024 | Fraction de service : postes requis pourvus | NV | module postes présent ; composition-type de fraction non vérifiée | 12 |
| EX-025 | Feuille de service ≠ tableau de quart | V-C (structure) | la feuille n'agrège pas les quarts | 09 |
| EX-026 | Rédaction de la feuille réservée aux rédacteurs désignés | V-C sur 1c37f22 ; V-NC sur main | création (11 profils), écritures (16 profils), lectures (13 × 3 états), circuit en navigateur ; deux jeux de données | 06, 09 |
| EX-027 | Feuille par équipage, validation COMAEQ | V-C avec réserve | COMAEQ strict, rédacteurs par équipage, pas d'échappement inter-équipage ; visas intermédiaires élargis (AUD-014) | 06 |
| EX-028 | Échange de service | NV | 7 échanges en démonstration, tous les états ; flux non rejoué | 09 |
| EX-029 | Service à quai, garde, quart distincts | PC | modèles distincts (Quart, ServiceGarde) ; non rejoué | 09 |
| EX-030 | Hiérarchie configurable par navire | PC | hiérarchie présente ; modification non autonome (AUD-019) ; sections facultatives non exercées (DP-03) | 02 |
| EX-031 | Service rattaché à son COMA, visa résolu par service | PC | `Service.commandant_adjoint` ; résolution par niveau dans deux circuits (P05) | 19 |
| EX-032 | Visa COMA : attente sans titulaire | PC | feuille rejouée ; autres circuits non rejoués | 19 |
| EX-033 | Double équipage A/B, relève, lecture seule à terre | PC | séparation des équipages vérifiée (création, désignation, lecture) ; relève et passation non rejouées ; passation à arbitrer (DP-02) | 06 |
| EX-034 | Commandement à terre sans écriture métier | PC | refus 403 du suivi de classe dans toutes les écritures sondées | 06 |
| EX-035 | Second : vision globale, écritures limitées | PC | ne publie pas, ne déclare pas de mouvement ; désigne des chefs de liste (décision ouverte) | 06 |
| EX-036 | Adjudant de compagnie, OSS | DIFF | aucune implémentation, conforme à l'absence de GO | 19 |
| EX-037 | Pas de « chef de groupement » / « CAN » | V-C | aucune occurrence | 19 |
| EX-038 | Organismes à terre comme unités | DIFF | consolidation V1 en cours | 19 |
| EX-040 | Fiche flotte : circuit en 7 étapes | NV | non rejoué | 08 |
| EX-041 | Fiche d'installation adaptable | NV | non rejoué | 08 |
| EX-042 | Compte rendu notifié au chef de secteur, sans visa | V-NC partiel | par l'API : ni ticket ni notification pour une installation non conforme (AUD-023) ; chemin web non rejoué | 08 |
| EX-043 | Complémentarité SSF, identifiants stables | PC | UUID sur tickets et installations ; pas d'interface SSF | 13 |
| EX-044 | Discussions contextuelles via threads | PC | fils par objet, accès par propriétaire et périmètre conformes ; écriture d'un message non concluante | 11 |
| EX-045 | Annonces par niveau et périmètre | PC | ciblage bâtiment conforme (404 hors cible) ; niveau « Urgent » au lieu de « Critique » | 11 |
| EX-046 | Logistique : stocks, prêts, retours, inventaires | PC | stock et mouvements conformes ; prêts/retours/inventaires de matériel différés | 10 |
| EX-047 | Documentation, formations, RETEX | PC | accès et validation de qualification vérifiés ; circuits non rejoués ; faible couverture de test (AUD-030) | 12 |
| EX-048 | QR codes hors V1 | V-NC | route /scan/<uuid>/ fonctionnelle (DP-06) | 08, 19 |
| EX-049 | PÉPIN / CRAT / RAV/c | DIFF | absents, conforme | 19 |
| EX-050 | PC fixe 1366×768 ; mobile dégradé proprement | PC | 1366×768 et 375×667 : aucun débordement, aucune erreur console (échantillon) ; tablette, impression non testées | 05 |
| EX-051 | Interface sobre, aide contextuelle | NV | maquettes non comparées | 05 |
| EX-052 | Tout en français | PC | gabarits et messages observés en français ; page technique en anglais seulement avec DEBUG ; code non relu | 05 |
| EX-053 | SQLite (dev) et PostgreSQL (prod) | V-C | suite complète OK sur les deux (3 829 tests ; 20 ignorés sous SQLite exécutés et OK sous PostgreSQL) | 14, 17 |
| EX-054 | Rondes retirées | V-C | routes absentes ; résidu de modèles (AUD-007) | 12, 19 |

## Synthèse

| État | Nombre |
|---|---|
| PC | 22 |
| V-C | 9 |
| NV | 9 |
| DIFF | 4 |
| V-NC | 3 |
| ABS | 1 |

Total : 48 exigences recensées. Aucune exigence n'est déclarée conforme sur la seule existence du code. Les exigences numérotées EX-015 à EX-019 et EX-039 n'existent pas dans le référentiel (numérotation par blocs thématiques).
