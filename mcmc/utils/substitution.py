"""Substitution mono-alphabétique des 26 lettres (l'espace reste inchangé).

Convention de la clé de déchiffrement utilisée par le MCMC :

    cle_dechiffrement[i] = lettre claire de la lettre chiffrée LETTRES[i]

C'est la clé que la chaîne de Markov explore.  La clé de chiffrement est son
inverse :

    cle_chiffrement[i] = lettre chiffrée de la lettre claire LETTRES[i]
"""

import string

LETTRES = string.ascii_uppercase


def verifier_cle(cle) -> bool:
    """Vrai si ``cle`` est une permutation des 26 lettres."""
    return (
        isinstance(cle, str)
        and len(cle) == len(LETTRES)
        and set(cle) == set(LETTRES)
    )


def cle_inverse(cle):
    """Passe d'une clé de déchiffrement à la clé de chiffrement (et inversement).

    L'opération est involutive : ``cle_inverse(cle_inverse(k)) == k``.
    """
    if not verifier_cle(cle):
        raise ValueError("Clé invalide : il faut une permutation des 26 lettres.")
    return "".join(LETTRES[cle.index(c)] for c in LETTRES)


def dechiffrer(texte, cle):
    """Remplace chaque lettre chiffrée par sa lettre claire ; l'espace reste inchangé."""
    if not verifier_cle(cle):
        raise ValueError("Clé de déchiffrement invalide.")
    correspondance = dict(zip(LETTRES, cle))
    return "".join(correspondance.get(c, c) for c in texte)


def chiffrer(texte, cle):
    """Chiffre avec une clé de chiffrement ; l'espace reste inchangé."""
    if not verifier_cle(cle):
        raise ValueError("Clé de chiffrement invalide.")
    correspondance = dict(zip(LETTRES, cle))
    return "".join(correspondance.get(c, c) for c in texte)
