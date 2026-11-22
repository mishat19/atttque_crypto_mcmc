"""Substitution par décalage (César) : chiffrement, déchiffrement, attaque fréquentielle.

Ce module est la "couche crypto" utilisée par l'interface web (carte César).
Il encapsule simplement les fonctions de ``chiffrements.chiffrement_cesar``
et l'attaque par corrélation de fréquences.

À ne pas confondre avec ``mcmc/utils/substitution.py`` : ici la clé est un
décalage (26 clés possibles), là-bas la clé est une permutation des 26 lettres
(26! clés possibles), attaquée par MCMC.
"""

import sys
from pathlib import Path

# On ajoute la racine du dépôt au chemin d'import : le projet n'utilise pas de
# paquets installables (pas de setup.py / pyproject.toml), donc chaque module
# qui importe un module d'un autre dossier doit faire cette manipulation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.attaque_frequentielle import scores_decalages
from chiffrements.chiffrement_cesar import chiffre_cesar, dechiffre_cesar


def chiffre_cryptogramme(texte_clair, decalage):
    """Applique la clé (décalage César) pour produire un cryptogramme.

    Le modulo 26 ramène un décalage quelconque (par exemple 29 ou -1)
    dans l'intervalle 0..25 des décalages utiles.
    """
    return chiffre_cesar(texte_clair, decalage % 26)


def dechiffre_cryptogramme(cryptogramme, decalage):
    """Retrouve le texte clair d'un cryptogramme avec une clé connue."""
    return dechiffre_cesar(cryptogramme, decalage % 26)


def scores_attaque_frequentielle(cryptogramme):
    """Note de chaque décalage candidat (0 à 25).

    La note est la corrélation entre l'histogramme du cryptogramme et la
    distribution connue des lettres en français : plus elle est grande,
    plus le décalage est probable.
    """
    return scores_decalages(cryptogramme)


def attaque_frequentielle(cryptogramme):
    """Devine le décalage le plus probable puis le texte clair.

    Étapes : on calcule les 26 scores, on garde le meilleur, puis on
    déchiffre avec lui. Utilisé ici surtout comme exemple : l'interface web
    préfère afficher le classement complet (via ``scores_attaque_frequentielle``)
    pour laisser l'utilisateur cliquer sur un candidat différent du meilleur.
    """
    scores = scores_attaque_frequentielle(cryptogramme)
    meilleur_decalage = max(scores, key=scores.get)
    return {
        "decalage": meilleur_decalage,
        "texte_clair": dechiffre_cesar(cryptogramme, meilleur_decalage),
    }
