"""Cryptogrammes de substitution monalphabétique par décalage (César).

Trois opérations sont fournies.

1. Chiffrement :
   Appliquer une clé de chiffrement à un texte clair pour obtenir un
   cryptogramme (utilisation du chiffrement de César).

2. Déchiffrement :
   Déchiffrer un texte chiffré avec une clé connue (utilisation du
   déchiffrement de César).

3. Attaque fréquentielle :
   Retrouver texte clair et clé sans la connaître en comparant les
   fréquences des lettres du cryptogramme avec celles du français.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.chiffrement_cesar import ALPHABET, chiffre_cesar, dechiffre_cesar

# Fréquence des lettres en français (pourcentage, somme ≈ 100).
FREQUENCES_FR = {
    "A": 8.11, "B": 0.81, "C": 3.38, "D": 4.28, "E": 17.69,
    "F": 1.13, "G": 1.19, "H": 0.74, "I": 7.31, "J": 0.18,
    "K": 0.02, "L": 5.69, "M": 2.74, "N": 7.11, "O": 5.23,
    "P": 3.01, "Q": 1.36, "R": 6.55, "S": 8.09, "T": 7.07,
    "U": 5.74, "V": 1.32, "W": 0.04, "X": 0.46, "Y": 0.30,
    "Z": 0.12,
}


def chiffre_cryptogramme(texte_clair, decalage):
    """Applique la clé (décalage César) pour produire un cryptogramme."""
    return chiffre_cesar(texte_clair, decalage % 26)


def dechiffre_cryptogramme(cryptogramme, decalage):
    """Retrouve le texte clair d'un cryptogramme avec une clé connue."""
    return dechiffre_cesar(cryptogramme, decalage % 26)


def scores_attaque_frequentielle(cryptogramme):
    """Note de chaque decalage candidat (0 a 25).

    Chaque decalage est note par la correlation entre les frequences
    observees dans le cryptogramme et les frequences connues du francais :
    plus la note est haute, plus le decalage est probable.
    """
    lettres = "".join(c for c in cryptogramme.upper() if c in ALPHABET)
    if not lettres:
        raise ValueError("Le cryptogramme ne contient aucune lettre.")

    effectif = len(lettres)
    scores = {}
    for decalage in range(26):
        score = 0.0
        for c in ALPHABET:
            frequence = lettres.count(c) / effectif
            suppose_clair = chr((ord(c) - ord("A") - decalage) % 26 + ord("A"))
            score += frequence * FREQUENCES_FR[suppose_clair]
        scores[decalage] = score
    return scores


def attaque_frequentielle(cryptogramme):
    """Attaque frequentielle : devine le decalage puis le texte clair.

    Le meilleur score donne la cle la plus probable.
    """
    scores = scores_attaque_frequentielle(cryptogramme)
    meilleur_decalage = max(scores, key=scores.get)
    return {
        "decalage": meilleur_decalage,
        "texte_clair": dechiffre_cesar(cryptogramme, meilleur_decalage),
    }


# if __name__ == "__main__":
#     message = "UN TEXTE ASSEZ LONG POUR QUE L ATTAQUE FREQUENTIELLE SOIT PRECISE SUR LE TEXTE"
#     cle = 4
#     crypto = chiffre_cryptogramme(message, cle)
#     print("Clair        :", message)
#     print("Cle          :", cle)
#     print("Cryptogramme :", crypto)
#     print("Dechiffre    :", dechiffre_cryptogramme(crypto, cle))
#     resultat = attaque_frequentielle(crypto)
#     print("Cle trouvee  :", resultat["decalage"])
#     print("Texte clair  :", resultat["texte_clair"])