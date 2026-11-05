# Audit 11 — Communication et notifications

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Contrôles d'accès exécutés ; les parcours de discussion complets, les accusés de lecture, les rappels planifiés et le Web Push ne sont pas rejoués.

| Contrôle | Résultat |
|---|---|
| Notifications : liste par API | chacun ne reçoit que les siennes (60, 2, 7, 0, 1, 0 selon le profil) |
| Marquer ou lire la notification d'autrui | 404 (web et API) |
| Fil de discussion d'un autre bâtiment | 404 pour `marin_abe_1` ; le suivi à terre d'une classe lit le fil d'un bâtiment suivi (200), conforme à la règle « consulte, commente » |
| Annonces : lecture d'une annonce ciblée sur le bâtiment A par un marin du bâtiment B ou un suivi à terre non rattaché | 404 |
| Annonces : création | formulaire absent (404) pour un équipier ; ouvert au chef de service, au second, au commandant (seuil `annonce_publication`) |
| Écriture d'un message dans un fil par API | 400 avec la charge d'essai : **non concluant** (champs mal choisis) |
| Niveaux d'annonce | le code utilise « Information / Important / Urgent » ; le cahier parle d'« Information / Important / Critique » (écart de vocabulaire, sans effet fonctionnel) |
| Archivage des notifications | absent (lue / non lue seulement), limitation déjà connue (ANO-012) |
| Rappels d'activation et d'échéance | évalués à la lecture des pages, pas de tâche planifiée dans la démonstration (ANO-013) |

## Anomalies

Aucune nouvelle ; ANO-012 et ANO-013 restent des limitations ouvertes. **Fonctionnalité volontairement abandonnée** : espaces de groupe et chat d'équipe (décision du 11/10/2026).

## Non vérifié

Mentions, pièces jointes, messages importants, Web Push en conditions réelles (HTTPS requis), tâche planifiée de rappel, accusés de lecture, charge.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Discussion contextuelle rejouée en navigateur : message d'un marin, visible du chef, réponse, **notification** du marin, fil d'un autre bâtiment en 404. Annonces : publication, accusé, suivi (1 accusé, 13 non lus). Observation à confirmer : les chefs de secteur de l'autre équipage reçoivent aussi les notifications « Compte rendu saisi » et « Anomalie signalée » d'un bâtiment à double équipage.

### Non vérifié ou dépendant d'une validation externe

Mentions, pièces jointes, Web Push (HTTPS requis), rappels planifiés (Celery).
