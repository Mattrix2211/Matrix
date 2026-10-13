# Missions à l'aveugle

Chaque mission est donnée **telle quelle** au marin concerné, avec seulement : persona, compte, adresse de l'application, résolution. Aucun menu, aucune page, aucun bouton. Les critères de réussite sont dans `criteres-coordinateur.md`, jamais transmis.

Priorité : **P1** parcours de démonstration (premier passage) · **P2** scénarios à risque (second passage, rôles complémentaires activés à la demande).

## Équipage permanent

| Id | Prio | Persona | Mission |
|---|---|---|---|
| M01 | P1 | Lucas | « Tu viens de prendre ton service. Retrouve ce que l'on attend de toi aujourd'hui et ce qui est prévu pour toi cette semaine. Dis-moi s'il y a quelque chose que tu dois confirmer avoir lu. » |
| M02 | P1 | Lucas | « Une tâche t'a été confiée mais il te manque une pièce pour la faire. Préviens ton responsable et assure-toi qu'il en soit informé. » |
| M03 | P1 | Julien | « Tu prends ton service à 07h30. Une intervention sur une installation t'a été confiée. Retrouve la consigne, consulte la documentation disponible, effectue le travail, puis signale la difficulté rencontrée à ton responsable. » *(Jeu de données absent pour ce compte : voir `personas-comptes.md`.)* |
| M04 | P2 | Julien | « Tu n'as pas pu saisir ton compte rendu sur le moment. Rends compte maintenant de ce que tu as fait hier, et prépare de quoi emporter sur papier. » |
| M05 | P1 | Claire | « Un travail est à confier à quelqu'un de ta section. Choisis la bonne personne en tenant compte de sa disponibilité, confie-lui le travail et assure-toi de savoir quand il sera fait. » |
| M06 | P1 | Claire | « Quelqu'un de ton équipe est bloqué. Débloque la situation ou fais-la remonter au bon échelon, puis vérifie que l'information a bien circulé. » |
| M07 | P2 | Claire | « Un collègue d'une autre section te demande de regarder ses travaux et de les réorganiser. Fais ce qui est de ton ressort. » |
| M08 | P1 | Antoine | « Prépare ta semaine de chef de service : repère ce qui est en retard, ce qui est bloqué et les risques de conflit avec les absences, les quarts ou les formations. Dis ce que tu demanderais à qui. » |
| M09 | P2 | Antoine | « Tu veux savoir où en est une installation importante de ton service et faire remonter un sujet technique au bon responsable. » |

## Rôles complémentaires (à activer uniquement pour le scénario ; profil copié de la page Notion)

| Id | Prio | Rôle / compte | Mission |
|---|---|---|---|
| M10 | P1 | Chef de liste (`chef_secteur_a`) | « Prépare la liste de quarts de la semaine prochaine pour ton secteur en tenant compte des absences et des qualifications, fais-la contrôler puis rends-la visible à l'équipe si tu en as la possibilité. Un marin te demande ensuite d'échanger un quart. » |
| M11 | P2 | Équipier d'un autre service (`equipier_elec_a`) | « On te parle d'une tâche de la propulsion. Essaie de la retrouver, puis vois ce qui t'est réservé. » |
| M12 | P1 | Équipage B à terre (`chef_secteur_b`) | « Tu es en période à terre. On a besoin de ton avis sur un sujet. Retrouve-le, réponds, puis essaie de t'occuper du reste de ton secteur. » |
| M13 | P1 | Commandements (`cdt_a`, `cdt_b`, `second_a`) | « Fais passer une consigne à tout l'équipage et assure-toi qu'elle a été prise en compte. Puis, côté relève entre équipages, fais ce qui est de ton ressort. » |
| M14 | P2 | COMAEQ (`coma_comaeq`) | « Regarde la journée du service courant et traite ce qui demande ton visa. » |
| M15 | P2 | COMANAV (`coma_comanav`) | « Identifie les installations indisponibles ou en dérive et ce qui est critique pour la conservation du bâtiment. » |
| M16 | P2 | Soutien à terre (`terre_classe`, `terre_securite`) | « Une demande du bord t'a été adressée. Réponds-y, consulte ce qui t'est destiné et vois si tu peux modifier quelque chose à bord. » |
| M17 | P2 | Référent formation (cf. écart personas) | « Une qualification arrive à échéance et une candidature t'est soumise. Instruis ce qui relève de toi. » |
| M18 | P2 | Administrateur de navire (`admin_navire`) | « Donne l'accès à un nouveau marin et règle ce qu'un chef peut faire, sans toucher à ce qui concerne un autre bâtiment. » |

## Couverture des parcours demandés

Accueil, calendrier/tâches/notifications (M01, M02) · affectation et suivi (M05, M06, M08) · quarts, gardes, échanges, publication (M10) · absences et conflits (M08, M10) · maintenance (M03, M09) · anomalies, demandes, réponses contextuelles (M02, M03, M12) · documentation et comptes rendus (M03, M04) · formations et qualifications (M17) · annonces et accusés (M01, M13) · double équipage et relève (M12, M13) · suivi technique COMANAV (M15) · service courant et COMAEQ (M14) · acteurs à terre (M16) · administration et limites (M07, M11, M18).
