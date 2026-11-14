# Anomalies du dossier (audit)

| Id | Gravité | Constat | Traitement prévu | Statut |
|---|---|---|---|---|
| AUD-001 | Bloquante (diffusion) | L'en-tête de chaque page dit « mention de diffusion large (ancienne édition) » et le fichier s'appelle « à large diffusion (ancienne édition) », alors que la couverture et le chapitre 3 disent que la classification n'est pas validée. La couverture annonce « … | P0-1 | ouverte — à traiter par la refonte |
| AUD-002 | Majeure | `matrix/templates/quarts/feuille_service_detail.html:18` contient un bouton « Imprimer » (`window.print()`, classe `no-print`) ; le guide visuel p.25 le montre | P0-2 | ouverte — à traiter par la refonte |
| AUD-003 | Majeure | Le guide visuel (64 captures, 5 parcours) et cet audit ont rejoué ces écrans | P0-4 | ouverte — à traiter par la refonte |
| AUD-004 | Majeure | Le module `rondes` n'a aucune vue et a été retiré de l'interface (chap. 2, 12 ; A8 ; `rondes/models.py` seul) | P0-2 | ouverte — à traiter par la refonte |
| AUD-005 | Majeure | `matrix/templates/components/parcours.html` ; visible sur toutes les captures d'accueil du guide | P0-2 | ouverte — à traiter par la refonte |
| AUD-006 | Majeure | Détection : légende dans les 6 % supérieurs de la page. S10 vu : illisible (5,0 pt), diagramme en pelote | P0-6 | ouverte — à traiter par la refonte |
| AUD-007 | Majeure (précisée en phase 2 : le bouton « M'assigner » existe aussi dans la liste) | La liste de maintenance affiche « Exécuter » sur toutes les lignes pour un équipier ; `/maintenance/occurrences/4/execute/` répond 403 pour lui. Le guide p.13 montre ces boutons sans explication | P0-2 | ouverte — à traiter par la refonte |
| AUD-008 | Majeure | Les fichiers de test ne sont dans aucun dépôt (rapport de qualification : « non conservés ») ; une copie est maintenant archivée dans `audit_preuves/tests_verification/` et relancée : 29 tests OK | P0-5 | ouverte — à traiter par la refonte |
| AUD-009 | Majeure | `RAPPORT_CLOTURE_G0.md` §3 : « Pages quasi vides : Aucune dans les deux PDF » | AUD-034 | fusionnée dans AUD-034 |
| AUD-010 | Majeure | 29 captures non utilisées (64 − 35). Les lignes de tickets sont cliquables (`onclick`, `ticket_list.html:28`) : ma capture automatique cherchait un lien `<a>` | P0-2 | ouverte — à traiter par la refonte |
| AUD-011 | Majeure | Les PDF ne contiennent ni synthèse de 2 pages (valeur, maturité, limites, risques) ni lecture de la `SYNTHESE_ECARTS_PAR_CRITICITE.md` (fichier restreint hors PDF) | P1-1 | ouverte — à traiter par la refonte |
| AUD-012 | Majeure | [V] p.2 ; [A] grep | P0-4 / P1-2 | ouverte — à traiter par la refonte |
| AUD-013 | Majeure | Écrans importants absents : accusé de réception d'une annonce, fiche d'installation (relevés, entretien), échange de tour, Documentation/RETEX, bas de l'accueil (indicateurs, bloc Supervision), prêt à appareiller avec session ouverte, vue mobile (le chapitre … | P1-3 | ouverte — à traiter par la refonte |
| AUD-014 | Mineure | [V] captures `p_maintenance_1_saisie`, `p_anomalie_3_description`, `parametres` | P2 | ouverte — à traiter par la refonte |
| AUD-015 | Mineure | [V] | P2 | ouverte — à traiter par la refonte |
| AUD-016 | Mineure | [A] différence de pixels 0,0 à 4,6 % | P1-3 | ouverte — à traiter par la refonte |
| AUD-017 | Mineure | [V] p.21 ; [A] grep | P2 | ouverte — à traiter par la refonte |
| AUD-018 | Mineure | [V] ; étendue non mesurée [?] | P2 | ouverte — à traiter par la refonte |
| AUD-019 | Mineure | [V] p.1, 14, 82 | P2 | ouverte — à traiter par la refonte |
| AUD-020 | Mineure | [A][V] `schemas_lisibilite.csv` | AUD-036 | fusionnée dans AUD-036 |
| AUD-021 | Mineure | Recomptage `def test_` indenté : 3 912 [C] ; 3 963 exécutés non rejoués [R] | P2 | ouverte — à traiter par la refonte |
| AUD-022 | Amélioration | [C][N][V] | P1-6 | ouverte — à traiter par la refonte |
| AUD-023 | Amélioration | [A] S02… absents de la liste des schémas ; [V] | P1-2 | ouverte — à traiter par la refonte |
| AUD-024 | Amélioration | [C] `settings.py:422-424` ; plan des chapitres | P1-4 | ouverte — à traiter par la refonte |
| AUD-025 | Mineure | [N] `navigateur_droits.md` | P1-3 | ouverte — à traiter par la refonte |
| AUD-026 | Amélioration | [?] | P1-6 | ouverte — à traiter par la refonte |
| AUD-027 | Mineure | [C] `ticket_list.html:28` | P2 | ouverte — à traiter par la refonte |
| AUD-028 | Mineure | [V] listing | P2 | ouverte — à traiter par la refonte |
| AUD-029 | Mineure | [V] | P2 | ouverte — à traiter par la refonte |
| AUD-030 | Mineure | « scan web `assets/scan/<uuid>/` » : le chemin réel est `/scan/<uuid>/` (`assets/web_urls.py:72` ; annexe C correcte) | P0-2 | ouverte — à traiter par la refonte |
| AUD-031 | Majeure | Annexe générée de 4 900 mots (79 % de l'annexe F) : lignes tronquées par « … » (« Une correcti… », « L… »), fragments de tableau (« \ | P0-6 | ouverte — à traiter par la refonte |
| AUD-032 | Mineure | Tableaux Markdown non rendus : p.37 (« Routes web », source `restreint/13_logistique_technique.md:20-22`) et p.79 (§23.9, source `23_configuration_deploiement_exploitation.md:119-123`, tableau collé au paragraphe) apparaissent en barres verticales brutes | P0-6 | ouverte — à traiter par la refonte |
| AUD-033 | Majeure | Des plages de décisions sont citées comme « cible, non développée » alors que certaines sont déjà réalisées : `DEC-PER-01` (tâches périodiques générées depuis les fiches) et `DEC-PER-04` (historiques conservés) vs `maintenance/tasks.py:66` et … | P0-3 | ouverte — à traiter par la refonte |
| AUD-034 | Majeure | Densité : 18 pages du à large diffusion (ancienne édition) et 26 du restreint sont remplies à moins de 70 % (11 et 15 à moins de 50 %) ; les compléments techniques (1 à 3 pages par chapitre) répètent chacun un cartouche de 5 lignes ; le restreint ne contient … | P1-8 (architecture) | ouverte — à traiter par la refonte |
| AUD-035 | Majeure | Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel : seule la légende dit « cible » ; l'image seule (cadre, couleur, mention) est identique à S16, S20, S30, S32 | P0-7 | ouverte — à traiter par la refonte |
| AUD-036 | Mineure | Sur 42 schémas : 22 bons, 7 moyens, 10 faibles (listes de cases sans information relationnelle : S02, S14, S22, S24, S27, S36, S37, S38, S40, S42), 1 difficile (S09), 1 illisible (S10) ; S02 montre 6 groupes quand le tableau juste dessous en compte 11 | P1-5 | ouverte — à traiter par la refonte |
| AUD-037 | Mineure | Rubriques « bis » : traces d'édition (insertions tardives) | P2 | ouverte — à traiter par la refonte |
| AUD-038 | Mineure | Deux chiffres pour le même inventaire ; l'annexe F.4 est datée de l'ensemble 4 et n'est plus à jour (la branche compte d'autres commits) | P2 | ouverte — à traiter par la refonte |

