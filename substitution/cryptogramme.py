"""Substitution par décalage (César) : chiffrement, déchiffrement, attaque fréquentielle."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.attaque_frequentielle import scores_decalages
from chiffrements.chiffrement_cesar import chiffre_cesar, dechiffre_cesar


def chiffre_cryptogramme(texte_clair, decalage):
    """Applique la clé (décalage César) pour produire un cryptogramme."""
    return chiffre_cesar(texte_clair, decalage % 26)


def dechiffre_cryptogramme(cryptogramme, decalage):
    """Retrouve le texte clair d'un cryptogramme avec une clé connue."""
    return dechiffre_cesar(cryptogramme, decalage % 26)


def scores_attaque_frequentielle(cryptogramme):
    """Note de chaque décalage candidat (0 à 25)."""
    return scores_decalages(cryptogramme)


def attaque_frequentielle(cryptogramme):
    """Devine le décalage le plus probable puis le texte clair."""
    scores = scores_attaque_frequentielle(cryptogramme)
    meilleur_decalage = max(scores, key=scores.get)
    return {
        "decalage": meilleur_decalage,
        "texte_clair": dechiffre_cesar(cryptogramme, meilleur_decalage),
    }
