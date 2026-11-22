"""États initiaux de la chaîne MCMC.

Le départ n'influe pas sur la loi stationnaire (la chaîne est irréductible),
mais un bon départ fait gagner beaucoup de temps : c'est le rôle de la
"chauffe" (burn-in) puis des redémarrages.
"""

import random
import string
from collections import Counter

LETTRES = string.ascii_uppercase


def cle_aleatoire():
    # génère une clé k aléatoire
    # random.sample sans remplacement : chaque lettre apparaît exactement
    # une fois, donc le résultat est bien une permutation des 26 lettres.
    k = "".join(random.sample(LETTRES, len(LETTRES)))
    return k


def ordre_frequences(texte):
    """Lettres triées de la plus fréquente à la moins fréquente."""
    comptes = Counter(texte)
    # Counter[c] vaut 0 pour une lettre absente : elle arrive en fin de liste.
    return sorted(LETTRES, key=lambda c: comptes[c], reverse=True)


def cle_heuristique(chiffre, reference):
    """i-ème lettre la plus fréquente du chiffré -> i-ème lettre la plus fréquente du français.

    C'est l'attaque fréquentielle "naïve" : dans une substitution
    monoalphabétique, la lettre chiffrée la plus fréquente est probablement E,
    la deuxième probablement A ou S, etc. On construit une clé de
    *déchiffrement* : ``association[lettre_chiffree] = lettre_claire``.

    La clé obtenue est souvent déjà très proche de la bonne réponse : le MCMC
    n'a plus qu'à corriger quelques échanges.
    """
    association = dict(zip(ordre_frequences(chiffre), ordre_frequences(reference)))
    return "".join(association[c] for c in LETTRES)


def cle_aleatoire_positions(longueur):
    """Permutation aléatoire de 0..longueur-1."""
    if longueur < 2:
        raise ValueError("La longueur de clé doit être au moins 2.")
    cle = list(range(longueur))
    # shuffle mélange en place ; comme la liste de départ contient chaque
    # entier une fois, le résultat reste une permutation bijective.
    random.shuffle(cle)
    return tuple(cle)
