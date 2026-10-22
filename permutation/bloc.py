"""Permutation de positions par blocs (partie 1.4 du sujet).

La clé est une permutation ``p`` de ``range(l)``.  Elle décrit, pour un bloc de
``l`` caractères, la position d'arrivée de chaque caractère :

    p[i] = nouvelle position du caractère initialement en position i

Exemple du sujet, avec ``p = (3, 0, 2, 1)`` :

    clair        B O N J O U R
    positions    0 1 2 3 0 1 2 3
    arrivées     3 0 2 1 3 0 2 1
    chiffré      O J N B U R O

Le dernier bloc peut être plus court que ``l``.  On classe alors les premières
valeurs de la clé entre elles : c'est la convention qui redonne exactement
``BONJOUR -> OJNBURO`` et qui reste réversible.
"""

from __future__ import annotations

import re


# =============== CLÉ ===============

def _normaliser_cle(cle) -> tuple[int, ...]:
    """Transforme une clé en tuple d'entiers.

    Accepte ``"3021"``, ``"3 0 2 1"``, ``"3,0,2,1"``, une liste ou un tuple.
    Pour une longueur supérieure à 10, utiliser des séparateurs : ``"10 11 0"``.
    """
    if isinstance(cle, str):
        texte = cle.strip()
        if not texte:
            raise ValueError("La clé ne peut pas être vide.")

        # "3021" : un chiffre par position.  Au-delà de 10, il faut séparer.
        if texte.isdigit():
            valeurs = [int(c) for c in texte]
        else:
            valeurs = [int(x) for x in re.findall(r"\d+", texte)]
    else:
        try:
            valeurs = [int(x) for x in cle]
        except TypeError as exc:
            raise ValueError("La clé doit être une chaîne ou une séquence d'entiers.") from exc

    if not valeurs:
        raise ValueError("La clé ne peut pas être vide.")
    return tuple(valeurs)


def verifier_cle(cle) -> bool:
    """Vrai si la clé est une permutation de ``range(longueur)``."""
    try:
        p = _normaliser_cle(cle)
    except (ValueError, TypeError):
        return False
    return sorted(p) == list(range(len(p)))


def definir_cle(cle) -> tuple[int, ...]:
    """Définit et vérifie une clé.  Lève ``ValueError`` si elle est invalide."""
    p = _normaliser_cle(cle)
    if sorted(p) != list(range(len(p))):
        raise ValueError(
            "Clé invalide : les valeurs doivent être exactement 0, 1, ..., l-1."
        )
    return p


def cle_inverse(cle) -> tuple[int, ...]:
    """Permutation réciproque : ``inverse[p[i]] = i``."""
    p = definir_cle(cle)
    reciproque = [0] * len(p)
    for depart, arrivee in enumerate(p):
        reciproque[arrivee] = depart
    return tuple(reciproque)


def formater_cle(cle) -> str:
    """Forme lisible : ``3021`` pour l <= 10, ``3 0 2 1`` sinon."""
    p = definir_cle(cle)
    if len(p) <= 10:
        return "".join(str(x) for x in p)
    return " ".join(str(x) for x in p)


# =============== PERMUTATION ===============

def _ordre(permutation, taille: int) -> list[int]:
    """Ordre de lecture des sources dans un bloc de ``taille`` positions.

    Les indices sont classés par valeur de clé croissante.  Pour un bloc plein,
    c'est exactement la permutation ; pour un bloc incomplet, on classe les
    premières valeurs de la clé entre elles.
    """
    return sorted(range(taille), key=lambda i: (permutation[i], i))


def _rang(permutation, taille: int) -> list[int]:
    """Réciproque de ``_ordre`` sur un bloc de ``taille`` positions."""
    rang = [0] * taille
    for position, source in enumerate(_ordre(permutation, taille)):
        rang[source] = position
    return rang


def _permuter(texte: str, permutation, dechiffrer: bool = False) -> str:
    """Réordonne les positions de ``texte`` bloc par bloc."""
    longueur = len(permutation)
    if longueur == 0:
        raise ValueError("La clé ne peut pas être vide.")

    resultat = []
    for debut in range(0, len(texte), longueur):
        bloc = texte[debut:debut + longueur]
        ordre = _rang(permutation, len(bloc)) if dechiffrer else _ordre(permutation, len(bloc))
        resultat.append("".join(bloc[i] for i in ordre))
    return "".join(resultat)


def chiffrer(texte: str, cle) -> str:
    """Applique la permutation ``cle`` au texte clair."""
    return _permuter(texte, definir_cle(cle), dechiffrer=False)


def dechiffrer(texte: str, cle) -> str:
    """Retrouve le texte clair d'un cryptogramme avec la clé connue."""
    return _permuter(texte, definir_cle(cle), dechiffrer=True)


# =============== EXEMPLE DU SUJET ===============

if __name__ == "__main__":
    cle = "3021"
    clair = "BONJOUR"
    chiffre = chiffrer(clair, cle)
    print("Clé          :", formater_cle(cle))
    print("Clé inverse  :", formater_cle(cle_inverse(cle)))
    print("Clair        :", clair)
    print("Chiffré      :", chiffre)
    print("Déchiffré    :", dechiffrer(chiffre, cle))
