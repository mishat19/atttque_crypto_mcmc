"""Permutation de positions par blocs (partie 1.4 du sujet).

La clé est une permutation ``p`` de ``range(l)``.  Elle décrit, pour un bloc de
``l`` caractères, la position d'arrivée de chaque caractère :

    p[i] = nouvelle position du caractère initialement en position i

Exemple du sujet, avec ``p = (3, 0, 2, 1)`` :

    clair        B O N J O U R
    positions    0 1 2 3 0 1 2 3
    arrivées     3 0 2 1 3 0 2 1
    chiffré      O J N B U R O

Lecture du tableau : la lettre B (position 0) doit arriver en position 3,
O (position 1) en position 0, N (position 2) en position 2, J en position 1.
On obtient bien "OJNBURO".

Le dernier bloc peut être plus court que ``l``.  On classe alors les premières
valeurs de la clé entre elles (voir ``_ordre``) : c'est la convention qui redonne
exactement ``BONJOUR -> OJNBURO`` et qui reste réversible.

Ce module est utilisé par le moteur MCMC (``mcmc/main.py``) et par la carte
"Permutation" de l'interface web (via ``permutation/cryptogramme.py``).
"""

import re


# =============== CLÉ ===============

def _normaliser_cle(cle) -> tuple[int, ...]:
    """Transforme une clé en tuple d'entiers.

    Accepte "3021", "3 0 2 1", "3,0,2,1", une liste ou un tuple.
    Au-delà de 10 positions, séparer les valeurs : "10 11 0".

    Deux cas pour une chaîne :
    - "3021" est une suite de chiffres : chaque chiffre est une position ;
    - "3 0 2 1" ou "10,0,1" : on extrait tous les groupes de chiffres avec
      une expression régulière, ce qui permet d'avoir des indices à 2 chiffres.
    """
    if isinstance(cle, str):
        texte = cle.strip()
        if not texte:
            raise ValueError("La clé ne peut pas être vide.")

        if texte.isdigit():
            valeurs = [int(c) for c in texte]
        else:
            valeurs = [int(x) for x in re.findall(r"\d+", texte)]
    else:
        # Une séquence (liste, tuple...) est acceptée à condition que ses
        # éléments soient convertibles en entiers.
        try:
            valeurs = [int(x) for x in cle]
        except TypeError as exc:
            raise ValueError("La clé doit être une chaîne ou une séquence d'entiers.") from exc

    if not valeurs:
        raise ValueError("La clé ne peut pas être vide.")
    return tuple(valeurs)


def verifier_cle(cle) -> bool:
    """Vrai si la clé est une permutation de ``range(longueur)``.

    Une clé valide contient exactement une fois chaque entier de 0 à l-1.
    Trier la clé et la comparer à [0, 1, ..., l-1] vérifie cette propriété
    en une seule ligne : cela interdit à la fois les doublons et les trous.
    """
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
    """Permutation réciproque : ``inverse[p[i]] = i``.

    Si la clé de chiffrement dit "la position i va en p[i]", la clé de
    déchiffrement doit dire "la position p[i] revient en i".
    """
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
    """Indices du bloc triés par valeur de clé (gère le dernier bloc incomplet).

    Pour un bloc complet de taille l, c'est l'inverse de la permutation.
    Pour un bloc plus court, on ne trie que les positions 0..taille-1 : les
    valeurs de clé absentes sont simplement ignorées, ce qui rend le
    chiffrement réversible quel que soit le dernier bloc.

    Le ``i`` dans la clé de tri sert de départage en cas d'égalité (défensif).
    """
    return sorted(range(taille), key=lambda i: (permutation[i], i))


def _rang(permutation, taille: int) -> list[int]:
    """Réciproque de ``_ordre`` sur un bloc de ``taille`` positions.

    ``rang[source] = position`` : pour la source numéro ``source``, cette
    fonction donne le rang qu'elle occupe une fois le bloc réordonné.
    """
    rang = [0] * taille
    for position, source in enumerate(_ordre(permutation, taille)):
        rang[source] = position
    return rang


def _permuter(texte: str, permutation, dechiffrer: bool = False) -> str:
    """Réordonne les positions de ``texte`` bloc par bloc.

    Le texte est découpé en blocs de ``len(permutation)`` caractères.
    - au chiffrement, on lit le bloc dans l'ordre ``_ordre`` (tri des clés) ;
    - au déchiffrement, on lit dans l'ordre ``_rang`` (ordre inverse).

    Les deux orientations sont réciproques : dechiffrer(chiffrer(t)) == t.
    """
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
    # Petit auto-test exécutable : python permutation/bloc.py
    cle = "3021"
    clair = "BONJOUR"
    chiffre = chiffrer(clair, cle)
    print("Clé          :", formater_cle(cle))
    print("Clé inverse  :", formater_cle(cle_inverse(cle)))
    print("Clair        :", clair)
    print("Chiffré      :", chiffre)
    print("Déchiffré    :", dechiffrer(chiffre, cle))
