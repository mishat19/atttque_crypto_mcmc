"""Prépare un test : chiffre un texte clair connu avec une clé aléatoire."""
from utils.initialisation import cle_aleatoire
from utils.score import lire_texte
from utils.substitution import LETTRES

CHEMIN_CLAIR = "clair.txt"      # texte français, différent de reference.txt
CHEMIN_CHIFFRE = "chiffre.txt"
LONGUEUR = 1500                 # nombre de caractères à chiffrer

clair = lire_texte(CHEMIN_CLAIR)[:LONGUEUR]

cle_chiffrement = cle_aleatoire()
table = dict(zip(LETTRES, cle_chiffrement))
chiffre = "".join(table.get(c, c) for c in clair)

with open(CHEMIN_CHIFFRE, "w", encoding="utf-8") as f:
    f.write(chiffre)

cle_dechiffrement = "".join(LETTRES[cle_chiffrement.index(c)] for c in LETTRES)
print("Clé de déchiffrement attendue :", cle_dechiffrement)
print("Clair  :", clair[:70])
print("Chiffré:", chiffre[:70])

# +--------------------------------------------+
# |   ____      _    ____  ____  _____ _       |
# |  |  _ \    / \  |  _ \|  _ \| ____| |      |
# |  | |_) |  / _ \ | |_) | |_) |  _| | |      |
# |  |  _ <  / ___ \|  __/|  __/| |___| |___   |
# |  |_| \_\/_/   \_\_|   |_|   |_____|_____|  |
# |                                            |
# |  Demander au prof sur quel critère garder  |
# |  les meilleures clés                       |
# +--------------------------------------------+