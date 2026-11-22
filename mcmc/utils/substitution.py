"""Substitution mono-alphabétique des 26 lettres (l'espace reste inchangé).

 cle_chiffrement[i]   = lettre chiffrée de la lettre claire LETTRES[i]
 cle_dechiffrement[i] = lettre claire de la lettre chiffrée LETTRES[i]  (explorée par le MCMC)

Exemple : avec la clé de chiffrement "BCDEFGHIJKLMNOPQRSTUVWXYZA" (décalage
de 1), la clé de déchiffrement est "ZABCDEFGHIJKLMNOPQRSTUVWXY".

Cette clé est une permutation de 26 lettres : il y en a 26! ≈ 4·10^26,
beaucoup trop pour une recherche exhaustive. D'où l'échantillonnage MCMC.
"""

import string

LETTRES = string.ascii_uppercase


def verifier_cle(cle) -> bool:
    """Vrai si ``cle`` est une permutation des 26 lettres.

    La longueur garantit qu'aucune lettre n'est manquante ni surnuméraire,
    et l'égalité des ensembles garantit qu'il n'y a aucun doublon.
    """
    return (
        isinstance(cle, str)
        and len(cle) == len(LETTRES)
        and set(cle) == set(LETTRES)
    )


def cle_inverse(cle):
    """Passe de la clé de chiffrement à celle de déchiffrement (et inversement).

    ``LETTRES.index(c)`` donne le rang de la lettre chiffrée c ; la lettre
    claire correspondante est celle qui occupe ce même rang dans LETTRES.
    L'opération est involutive : inverse(inverse(k)) = k.
    """
    if not verifier_cle(cle):
        raise ValueError("Clé invalide : il faut une permutation des 26 lettres.")
    return "".join(LETTRES[cle.index(c)] for c in LETTRES)


def dechiffrer(texte, cle):
    """Remplace chaque lettre chiffrée par sa lettre claire ; l'espace reste inchangé."""
    if not verifier_cle(cle):
        raise ValueError("Clé de déchiffrement invalide.")
    # zip associe chaque lettre chiffrée (LETTRES) à son image claire (cle).
    # dict.get(c, c) laisse inchangés les caractères hors alphabet (espaces).
    correspondance = dict(zip(LETTRES, cle))
    return "".join(correspondance.get(c, c) for c in texte)


def chiffrer(texte, cle):
    """Chiffre avec une clé de chiffrement ; l'espace reste inchangé."""
    if not verifier_cle(cle):
        raise ValueError("Clé de chiffrement invalide.")
    correspondance = dict(zip(LETTRES, cle))
    return "".join(correspondance.get(c, c) for c in texte)
