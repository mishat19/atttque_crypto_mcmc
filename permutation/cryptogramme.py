"""Permutation de position combinée au chiffrement de Vigenère.

La clé est un mot ("LEMON") :
- chaque lettre donne le décalage Vigenère de sa position dans le bloc ;
- l'ordre alphabétique des lettres donne la permutation des positions.

Exemple avec "LEMON" (longueur 5) :
    lettres triées : E(1) L(0) M(2) N(4) O(3)
    permutation    : [1, 0, 2, 4, 3]
    décalages      : L=11, E=4, M=12, O=14, N=13

Chiffrement : Vigenère positionnel puis permutation. Déchiffrement : l'inverse.

Ce module alimente la carte "Permutation" de l'interface web. Il n'est PAS
utilisé par le MCMC, qui attaque directement la permutation pure de
``permutation/bloc.py``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.chiffrement_cesar import ALPHABET
from chiffrements.chiffrement_vigenere import (
    chiffre_vigenere_positions,
    cle_inverse_vigenere,
    dechiffre_vigenere_positions,
)
from permutation.bloc import _ordre, _rang, _permuter


# =============== 1. CLÉ ===============

def _normaliser(mot_cle):
    """Mot en majuscules, sans espaces.

    On accepte "le mon" ou "LEMON" : les espaces sont retirés pour que la
    longueur de la clé soit bien le nombre de lettres utiles.
    """
    if not isinstance(mot_cle, str):
        raise ValueError("La clé doit être un mot.")
    return "".join(mot_cle.upper().split())


def _permutation_depuis(mot):
    """Rang de chaque position quand on trie les lettres de la clé.

    Pour "LEMON", trier les lettres par ordre alphabétique parcourt les
    positions dans l'ordre [1, 0, 2, 4, 3] (E, L, M, N, O). En écrivant
    ``permutation[position] = rang``, on obtient pour chaque position
    originale son rang dans l'ordre trié : ici [1, 0, 2, 4, 3]. Ce rang est
    la permutation appliquée aux blocs.
    """
    longueur = len(mot)
    permutation = [0] * longueur
    for rang, position in enumerate(sorted(range(longueur), key=lambda i: (mot[i], i))):
        permutation[position] = rang
    return permutation


def verifier_cle(cle) -> bool:
    """Vrai si la clé (mot ou dict de definir_cle) est valide.

    Deux représentations sont acceptées :
    - une chaîne de lettres (le mot clé saisi par l'utilisateur) ;
    - le dictionnaire produit par ``definir_cle``, qui contient déjà la
      permutation ; on vérifie alors qu'elle est bien bijective.
    """
    if isinstance(cle, dict):
        longueur = cle.get("longueur")
        permutation = cle.get("permutation")
        if not isinstance(longueur, int) or not isinstance(permutation, list):
            return False
        if len(permutation) != longueur or longueur <= 0:
            return False
        return sorted(permutation) == list(range(longueur))

    mot = _normaliser(cle)
    return bool(mot) and all(c in ALPHABET for c in mot)


def definir_cle(mot_cle) -> dict:
    """Définit la clé à partir d'un mot.

    Un mot aux lettres déjà triées (ABCD, AAAA...) donne la permutation identité.
    Le dictionnaire retourné contient trois champs :
      "mot"         -> les décalages Vigenère ;
      "longueur"    -> la taille d'un bloc ;
      "permutation" -> l'ordre dans lequel on réarrange les positions.
    """
    mot = _normaliser(mot_cle)
    if not verifier_cle(mot):
        raise ValueError("La clé doit être un mot non vide uniquement formé de lettres.")
    return {"mot": mot, "longueur": len(mot), "permutation": _permutation_depuis(mot)}


def cle_inverse(cle) -> dict:
    """Inverse de la clé : décalages opposés et permutation réciproque.

    Au déchiffrement on applique la permutation d'abord, puis Vigenère.
    C'est l'ordre inverse du chiffrement (Vigenère puis permutation), donc
    il faut inverser les deux composants et inverser leur ordre d'application.
    """
    cle = _exiger(cle)
    reciproque = [0] * cle["longueur"]
    for depart, arrivee in enumerate(cle["permutation"]):
        reciproque[arrivee] = depart

    return {
        "mot": cle_inverse_vigenere(cle["mot"]),
        "longueur": cle["longueur"],
        "permutation": reciproque,
    }


def _exiger(cle) -> dict:
    """Valide la clé et la renvoie sous forme de dictionnaire."""
    if not verifier_cle(cle):
        raise ValueError("Clé invalide : mot non vide de lettres, permutation bijective.")
    return cle if isinstance(cle, dict) else definir_cle(cle)


# =============== 2. ET 4. CHIFFREMENT / DÉCHIFFREMENT ===============

def chiffre_cryptogramme(texte_clair, cle) -> str:
    """Applique la clé (Vigenère positionnel puis permutation) pour produire un cryptogramme."""
    cle = _exiger(cle)
    # _permuter travaille par blocs de len(permutation), comme dans bloc.py.
    return _permuter(chiffre_vigenere_positions(texte_clair, cle["mot"]), cle["permutation"])


def dechiffre_cryptogramme(cryptogramme, cle) -> str:
    """Retrouve le texte clair d'un cryptogramme avec une clé connue."""
    cle = _exiger(cle)
    return dechiffre_vigenere_positions(
        _permuter(cryptogramme, cle["permutation"], dechiffrer=True),
        cle["mot"],
    )


# =============== POURQUOI EST-CE DIFFICILE À ATTAQUER ? ===============
#
# La permutation conserve les lettres : l'histogramme ne change pas, mais les
# bigrammes voisins sont cassés, donc la méthode de Kasiski ne marche plus et
# le texte reste illisible même avec les bons décalages. Il reste L! ordres
# possibles pour remettre les colonnes en place.
# En revanche chaque colonne garde un décalage unique : l'attaque fréquentielle
# par colonnes retrouve encore les lettres (26·L hypothèses), seul l'ordre manque.
