# Audit 18 — Cohérence globale et stratégie (synthèse transversale)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Elle croise les 19 autres rapports, tous partiels sauf l'audit 20 (clos avec réserves). Elle ne peut pas être définitive tant que les vérifications listées dans `09_BILAN_DES_AUDITS.md` ne sont pas faites.

## 1. Cinq problèmes transversaux

| N° | Problème | Audits | Anomalies | Cause commune |
|---|---|---|---|---|
| T1 | **Droits fondés sur le niveau** plutôt que sur la fonction : l'administrateur technique, le commandant et les COMA franchissent des circuits qui ne sont pas les leurs | 06, 09, 12, 02 | AUD-014, 015, 022 | registre de seuils exprimé en niveaux ; ordre `ADMIN_NAVIRE` > `COMMANDANT` |
| T2 | **Organisation du bord : modifiable mais pas gouvernée** : suppression physique, archivage sans effet, périmètre déduit d'un champ vide, structure hors de portée d'un non-développeur | 02, 03, 14, 20 | AUD-019, 020, 021, 028, DP-03 | trois mécanismes indépendants (suppression, périmètre, archivage) jamais pensés ensemble |
| T3 | **Interface et serveur ne disent pas la même chose** : liens affichés puis refusés, accueil non filtré comme la fiche | 04, 05, 06, 08 | AUD-008, 016, 027 | masquage réécrit à chaque écran au lieu d'une règle unique |
| T4 | **Mise en service et exploitation non cadrées** : démonstration non isolée, HTTPS impossible derrière un proxy, pas de serveur d'application, sauvegarde absente, tâches de fond sans supervision | 03, 15, 17 | AUD-009, 010, 011, 017, 031, 032 | le dépôt est organisé pour le développement ; aucun mode « bord » défini |
| T5 | **Suite verte, parcours rouges** : 3 829 tests verts coexistent avec les constats ci-dessus ; pas de test navigateur ni d'intégration continue | 16, 13 | AUD-002, 003, 029, 030 | tests écrits pour les règles actuelles, pas pour l'intention métier |

## 2. Contradictions entre sources

| Sujet | Source A | Source B | Traitement |
|---|---|---|---|
| Passation | « maintenue en V1, configurable » (complément d'octobre) | « retirée par la PR #7, différée » | DP-02 |
| QR codes | « hors V1 » | route de scan active | DP-06 |
| Administrateur technique | « gère la plateforme, pas le fonctionnement métier » (Cahier §5) | niveau supérieur au commandant (code) | T1 |
| Chaîne « inspection → ticket » | documentée comme générale | limitée au matériel mobile | AUD-023 |
| Principe « Internet n'existe pas » | « aucun CDN » (REFERENCE, cahier) | charte `DESIGN_SYSTEM.md` générique propose un lien Google Fonts | Matrix auto-héberge : conforme |

## 3. Fonctionnalités orphelines ou résiduelles

QR (scan actif, usage hors V1) ; Rondes (modèles sans test ni route) ; champs `archived` (aucun effet) ; `boto3` et `django-storages` (probablement inutiles) ; vocabulaire de quart (musique, homme mort) cadré mais non implémenté ; clé de registre `structure_navire_ecriture` (API seulement, sans écran).

## 4. Dépendances entre corrections (ordre recommandé)

1. **P0 sans dépendance** : garde-fou de la démonstration (AUD-009) ; interdiction de la suppression physique d'une unité avec historique (AUD-020, premier niveau de P04).
2. **Socle de désignation** (P02, option A puis B) : avant les écrans de structure, car la fonction « gestion de la structure » en dépend.
3. **États de rattachement** (P01) avec archivage effectif (AUD-028) : prérequis de l'assistant de transfert (P04, options 2 et 3) et de l'import de personnel (DP-11).
4. **Déploiement de référence** (P03) : indépendant du fonctionnel, dépend des responsables SIC ; à lancer en parallèle.
5. **Tests** : chaque correction ajoute son test ; tests navigateur versionnés (AUD-003) et CI hors ligne (AUD-002) avant la première fusion de correctifs.

## 5. Ce que la synthèse ne peut pas encore dire

Voir `09_BILAN_DES_AUDITS.md` : calendrier, maintenance, communication, formation, documentation et mobilité n'ont pas été parcourus de bout en bout en navigateur ; le jugement sur « les marins travaillent-ils efficacement » reste ouvert.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Synthèse définitive : voir `../00_SYNTHESE_EXECUTIVE.md` et `../09_BILAN_DES_AUDITS.md`.

### Non vérifié ou dépendant d'une validation externe

Dépend des réserves des autres audits.
