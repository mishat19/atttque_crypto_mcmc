import random
import string
from collections import Counter

LETTRES = string.ascii_uppercase


def cle_aleatoire():
    # génère une clé k aléatoire
    k = "".join(random.sample(LETTRES, len(LETTRES)))
    return k


def ordre_frequences(texte):
    """
    Lettres triées de la plus fréquente à la moins fréquente.
    """
    comptes = Counter(texte)
    return sorted(LETTRES, key=lambda c: comptes[c], reverse=True)


def cle_heuristique(chiffre, reference):
    """i-ème lettre la plus fréquente du chiffré -> i-ème lettre la plus fréquente du français."""

    association = dict(zip(ordre_frequences(chiffre), ordre_frequences(reference)))
    return "".join(association[c] for c in LETTRES)


def cle_aleatoire_positions(longueur):
    """Permutation aléatoire de ``0..longueur-1`` pour le chiffrement par blocs."""
    if longueur < 2:
        raise ValueError("La longueur de clé doit être au moins 2.")
    cle = list(range(longueur))
    random.shuffle(cle)
    return tuple(cle)


def cle_identite_positions(longueur):
    """Permutation identité : utile comme point de départ déterministe."""
    if longueur < 1:
        raise ValueError("La longueur de clé doit être positive.")
    return tuple(range(longueur))