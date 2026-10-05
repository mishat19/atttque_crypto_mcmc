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

from chiffrements.attaque_frequentielle import FREQUENCES_FR, scores_decalages
from chiffrements.chiffrement_cesar import chiffre_cesar, dechiffre_cesar


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
    return scores_decalages(cryptogramme)


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