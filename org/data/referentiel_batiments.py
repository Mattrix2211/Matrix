"""Référentiel des bâtiments : circulaire n°469/ARM/EMM/OPS/SCEM/NP du 16 avril 2025, annexe II (situation au 01/04/2025).

Données transcrites du référentiel Notion « Référentiel des bâtiments Marine nationale ». Le statut d'une unité listée en 2025
est « référence 2025, à vérifier » : ce n'est pas une attestation d'activité en 2026. Les libellés des types reprennent
le code de la circulaire ; ils se corrigent en administration.
"""
from datetime import date

SOURCE_URL = "https://www.defense.gouv.fr/sites/default/files/marine/liste%20des%20navires%20de%20la%20Marine%20nationale.pdf"
SOURCE_DATE = date(2025, 4, 1)

# (type, nom, numéro de coque, trigramme, port-base)
INVENTAIRE_2025 = [
    ("SNLE", "Le Triomphant", "S 616", "TRI", "Brest"), ("SNLE", "Le Téméraire", "S 617", "TMR", "Brest"),
    ("SNLE", "Le Vigilant", "S 618", "VGL", "Brest"), ("SNLE", "Le Terrible", "S 619", "TRB", "Brest"),
    ("SNA", "Améthyste", "S 605", "AMT", "Toulon"), ("SNA", "Perle", "S 606", "PLE", "Toulon"),
    ("SNA", "Suffren", "S 635", "SFE", "Toulon"), ("SNA", "Duguay-Trouin", "S 636", "DGN", "Toulon"),
    ("PA", "Charles de Gaulle", "R 91", "CDG", "Toulon"),
    ("PHA", "Mistral", "L 9013", "MTL", "Toulon"), ("PHA", "Tonnerre", "L 9014", "TNR", "Toulon"),
    ("PHA", "Dixmude", "L 9015", "DXM", "Toulon"),
    ("FDA", "Forbin", "D 620", "FRB", "Toulon"), ("FDA", "Chevalier Paul", "D 621", "CHP", "Toulon"),
    ("FREMM", "Aquitaine", "D 650", "AQN", "Brest"), ("FREMM", "Normandie", "D 651", "NMD", "Brest"),
    ("FREMM", "Provence", "D 652", "PCE", "Toulon"), ("FREMM", "Languedoc", "D 653", "LGC", "Toulon"),
    ("FREMM", "Auvergne", "D 654", "AVG", "Brest"), ("FREMM", "Bretagne", "D 655", "BTE", "Brest"),
    ("FREMM DA", "Alsace", "D 656", "ALS", "Toulon"), ("FREMM DA", "Lorraine", "D 657", "LRN", "Toulon"),
    ("FLF", "La Fayette", "F 710", "LFY", "Toulon"), ("FLF", "Surcouf", "F 711", "SCF", "Toulon"),
    ("FLF", "Courbet", "F 712", "CRB", "Toulon"), ("FLF", "Aconit", "F 713", "ACN", "Toulon"),
    ("FLF", "Guépratte", "F 714", "GPE", "Toulon"),
    ("FS", "Floréal", "F 730", "FLR", "Port des Galets"), ("FS", "Prairial", "F 731", "PRL", "Papeete"),
    ("FS", "Nivôse", "F 732", "NVS", "Port des Galets"), ("FS", "Ventôse", "F 733", "VNS", "Fort-de-France"),
    ("FS", "Vendémiaire", "F 734", "VDR", "Nouméa"), ("FS", "Germinal", "F 735", "GML", "Fort-de-France"),
    ("PHM", "Commandant Blaison", "F 793", "BLS", "Brest"), ("PHM", "Enseigne de vaisseau Jacoubet", "F 794", "JCB", "Brest"),
    ("PHM", "Commandant Ducuing", "F 795", "DCG", "Toulon"), ("PHM", "Commandant Birot", "F 796", "BRT", "Toulon"),
    ("PHM", "Commandant Bouan", "F 797", "BOU", "Toulon"),
    ("PAG", "La Confiance", "P 733", "CFE", "Dégrad-des-Cannes"), ("PAG", "La Résolue", "P 734", "RSL", "Dégrad-des-Cannes"),
    ("PAG", "La Combattante", "P 735", "CBE", "Fort-de-France"),
    ("POM", "Auguste Bénébig", "P 779", "ANG", "Nouméa"), ("POM", "Teriieroo a Teriierooiteraï", "P 780", "TIO", "Papeete"),
    ("PAT", "Arago", "P 675", "ARG", "Brest"), ("PAT", "Le Malin", "P 701", "MLN", "Port des Galets"),
    ("PSP", "Flamant", "P 676", "FLT", "Cherbourg"), ("PSP", "Cormoran", "P 677", "CRM", "Cherbourg"),
    ("PSP", "Pluvier", "P 678", "PLV", "Cherbourg"),
    ("P40", "Fulmar", "P 740", "FUL", "Saint-Pierre-et-Miquelon"),
    ("PP", "L'Astrolabe", "P 800", "ASB", "Port des Galets"),
    ("BCR", "Somme", "A 631", "SME", "Brest"),
    ("BRF", "Jacques Chevallier", "A 725", "JQR", "Toulon"),
    ("CMT", "Andromède", "M 643", "AND", "Brest"), ("CMT", "Pégase", "M 644", "PEG", "Brest"),
    ("CMT", "Croix du Sud", "M 646", "CXS", "Brest"), ("CMT", "L'Aigle", "M 647", "AGL", "Brest"),
    ("CMT", "Lyre", "M 648", "LYR", "Toulon"), ("CMT", "Sagittaire", "M 650", "SGT", "Brest"),
    ("CMT", "Céphée", "M 652", "CPH", "Brest"), ("CMT", "Capricorne", "M 653", "CPR", "Toulon"),
    ("BEGM", "Thétis", "A 785", "THT", "Brest"),
    ("BRS", "Antarès", "M 770", "ATR", "Brest"), ("BRS", "Altaïr", "M 771", "ALR", "Brest"),
    ("BRS", "Aldébaran", "M 772", "ADN", "Brest"),
    ("BBPD", "Vulcain", "M 611", "VLC", "Cherbourg"), ("BBPD", "Achéron", "A 613", "ACR", "Toulon"),
    ("BBPD", "Styx", "M 614", "STX", "Brest"), ("BBPD", "Pluton", "M 622", "PLT", "Toulon"),
    ("BSAOM", "D'Entrecasteaux", "A 621", "DTT", "Nouméa"), ("BSAOM", "Bougainville", "A 622", "BVL", "Papeete"),
    ("BSAOM", "Champlain", "A 623", "CPN", "Port des Galets"), ("BSAOM", "Dumont d'Urville", "A 624", "DDL", "Fort-de-France"),
    ("BSAM", "Loire", "A 602", "LOR", "Toulon"), ("BSAM", "Rhône", "A 603", "RNE", "Brest"),
    ("BSAM", "Seine", "A 604", "SNE", "Toulon"), ("BSAM", "Garonne", "A 605", "GRE", "Brest"),
    ("BH2C", "Lapérouse", "A 791", "LPO", "Brest"), ("BH2C", "Borda", "A 792", "BDA", "Brest"),
    ("BH2C", "Laplace", "A 793", "LPC", "Brest"),
    ("BHO", "Beautemps-Beaupré", "A 758", "BBP", "Brest"),
    ("BEM", "Monge", "A 601", "MNG", "Brest"),
    ("BRE", "Dupuy de Lôme", "A 759", "DPL", "Brest"),
    ("BSP", "Alizé", "A 645", "ALZ", "Toulon"),
    ("CTS", "Gapeau", "L 9090", "GAP", "Hyères"),
    ("ERF", "Caouanne", "Y 690", "CAN", "Dégrad-des-Cannes"),
    ("BE", "Léopard", "A 748", "LPD", "Brest"), ("BE", "Panthère", "A 749", "PTR", "Brest"),
    ("BE", "Jaguar", "A 750", "JGR", "Brest"), ("BE", "Lynx", "A 751", "LYX", "Brest"),
    ("BE", "Guépard", "A 752", "GPR", "Brest"), ("BE", "Chacal", "A 753", "CHL", "Brest"),
    ("BE", "Tigre", "A 754", "TGR", "Brest"), ("BE", "Lion", "A 755", "LIO", "Brest"),
    ("BIN", "Glycine", "A 770", "GLY", "Brest"), ("BIN", "Églantine", "A 771", "EGL", "Brest"),
    ("GOELETTE", "Étoile", "A 649", "ETL", "Brest"), ("GOELETTE", "Belle Poule", "A 650", "BPO", "Brest"),
    ("COTRE", "Mutin", "A 652", "MUT", "Brest"),
    ("YAWL", "La Grande Hermine", "A 653", "GHR", "Brest"),
    ("RPC50", "Estérel", "A 641", "EST", "Toulon"), ("RPC50", "Luberon", "A 642", "LUB", "Toulon"),
    ("RPC12", "Maïto", "A 636", "MTO", "Fort-de-France"), ("RPC12", "Maroa", "A 637", "MRA", "Papeete"),
    ("RPC12", "Manini", "A 638", "MNN", "Papeete"),
]

# Gendarmerie maritime : catégorie distincte (circulaire 2025).
GENDARMERIE_2025 = [
    ("PCG", "Armoise", "P 719", "ARE", "Cherbourg"), ("PCG", "Géranium", "P 720", "GER", "Lorient"),
    ("PCG", "Jonquille", "P 721", "JQL", "Toulon"), ("PCG", "Violette", "P 722", "VLT", "Pointe-à-Pitre"),
    ("PCG", "Jasmin", "P 723", "JSM", "Papeete"),
    ("VCSM", "Adour", "P 603", "ADR", "Dzaoudzi"), ("VCSM", "Elorn", "P 601", "ELR", "Concarneau"),
    ("VCSM", "Scarpe", "P 604", "SCP", "La Rochelle"), ("VCSM", "Verdon", "P 602", "VRD", "Dzaoudzi"),
    ("VCSM", "Argens", "P 608", "ARS", "Saint-Raphaël"), ("VCSM", "Dumbéa", "P 606", "DBA", "Nouméa"),
    ("VCSM", "Gravona", "P 610", "GRV", "Ajaccio"), ("VCSM", "Vertonne", "P 605", "VRT", "Les Sables-d'Olonne"),
    ("VCSM", "Yser", "P 607", "YSR", "Dieppe"), ("VCSM", "Charente", "P 613", "CHT", "Cayenne"),
    ("VCSM", "Hérault", "P 609", "HRL", "Sète"), ("VCSM", "Mahury", "P 623", "MHY", "Cayenne"),
    ("VCSM", "Maury", "P 612", "MAY", "Gruissan"), ("VCSM", "Odet", "P 611", "ODT", "Dzaoudzi"),
    ("VCSM", "Organabo", "P 624", "OGB", "Kourou"), ("VCSM", "Tech", "P 614", "TEC", "Port-Vendres"),
    ("VCSM", "Trieux", "P 616", "TRX", "Saint-Malo"), ("VCSM", "Escaut", "P 618", "ESC", "Brest"),
    ("VCSM", "Huveaune", "P 619", "HUV", "Marseille"), ("VCSM", "Vésubie", "P 617", "VSB", "Nice"),
    ("VCSM", "Esteron", "P 622", "ESR", "Le Havre"), ("VCSM", "Sèvre", "P 620", "SEV", "Pornichet"),
    ("VCSM", "Penfeld", "P 615", "PFD", "Brest"), ("VCSM", "Aber Wrac'h", "P 621", "ABW", "Brest"),
    ("VCSM NG", "Maroni", "P 692", "MRI", "Le Havre"), ("VCSM NG", "Oyapock", "P 693", "OAK", "Dunkerque"),
    ("VCSM NG", "Aber Ildut", "P 694", "AIT", "Boulogne-sur-Mer"),
]

# Unités en essais à la date de la circulaire : (type, nom, coque, trigramme, date de prise en charge ou d'admission, commentaire).
# Ne jamais les fusionner avec « en service ». Le port-base n'est pas fourni par le référentiel.
ESSAIS_2025 = [
    ("FDI", "Amiral Ronarc'h", "D 660", "RNH", date(2022, 10, 28), "PAE 28/10/2022", True),
    ("POM", "Auguste Techer", "P 781", "AUR", date(2023, 12, 1), "PAE 01/12/2023", True),
    ("SNA", "Tourville", "S 637", "TVE", date(2024, 3, 15), "PAE 15/03/2024", True),
    ("BRF", "Jacques Stosskopf", "A 726", "JSF", date(2024, 4, 1), "PAE 01/04/2024", True),
    ("POM", "Jean Tranape", "P 782", "JTP", date(2025, 3, 1), "PAE 01/03/2025", True),
    ("DRONE SURFACE GUERRE DES MINES", "Canopus", "O 701", "CNP", date(2024, 12, 20),
     "Prise en charge 20/12/2024. Sans équipage à bord : aucune feuille de service.", False),
]

# Mises à jour publiques postérieures (statut à part, jamais généralisé à la flotte).
# (nom, coque, statut, date, source, commentaire)
MISES_A_JOUR = [
    ("Amiral Ronarc'h", "D 660", "LIVRE", date(2025, 10, 17),
     "https://www.defense.gouv.fr/dga/actualites/dga-commande-cinquieme-fregate-defense-dintervention-fdi-naval-group",
     "Livrée à la Marine le 17/10/2025, en déploiement de longue durée (DGA 02/04/2026). Livraison ne vaut pas admission au service actif."),
    ("Tourville", "S 637", "CONFIRME", date(2025, 1, 1),
     "https://www.defense.gouv.fr/dga/actualites/marin-nucleaire-dattaque-sna-rubis-debute-son-transfert-jusquau-dispositif-mise-leau",
     "Admis au service actif en 2025 (source DGA, octobre 2026)."),
]

# SNA De Grasse : livré en juin 2026, admission annoncée comme prochaine ; numéro de coque non fourni, à ne pas inventer.
SNA_DE_GRASSE = {
    "nom": "De Grasse", "statut": "LIVRE", "statut_au": date(2026, 6, 1),
    "source_url": "https://www.defense.gouv.fr/dga/actualites/marin-nucleaire-dattaque-sna-rubis-debute-son-transfert-jusquau-dispositif-mise-leau",
    "commentaire": "Livré en juin 2026 ; admission au service actif annoncée comme prochaine. Numéro de coque à vérifier.",
}
