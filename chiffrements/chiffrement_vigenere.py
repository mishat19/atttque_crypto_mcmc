"""Chiffrement de Vigenère : un décalage César différent par lettre.

La clé est un mot, par exemple "ORACLE" :
    clair       S O U P E ...
    clé         O R A C L E O R A C L ...   (répétée)
    décalages   14 17 0 2 11 4 ...

La lettre de clé A vaut 0, B vaut 1, ..., Z vaut 25.

Deux variantes coexistent dans le projet :
- ``chiffre_vigenere``       : la clé avance seulement sur les lettres ;
- ``chiffre_vigenere_positions`` : la clé avance sur TOUS les caractères,
  espaces compris. C'est cette variante qu'utilise le chiffrement combiné
  "Vigenère + permutation" (``permutation/cryptogramme.py``).
"""

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _decale(c, k):
    """Décale un caractère alphabétique de k rangs, en préservant la casse.

    k est le décalage issu de la clé (0..25). Les caractères qui ne sont pas
    des lettres A-Z/a-z sont renvoyés inchangés.
    """
    if c.upper() not in ALPHABET:
        return c
    base = "A" if c.isupper() else "a"
    return chr((ord(c) - ord(base) + k) % 26 + ord(base))


def _valider(cle):
    """Clé de Vigenère normalisée, lettres non vides exigées.

    On met la clé en majuscules pour pouvoir calculer ses décalages.
    Une clé vide ou contenant un chiffre/un accent est refusée : sinon
    ``ord(c) - ord('A')`` produirait des valeurs incohérentes.
    """
    cle = cle.upper()
    if not cle or not all(c in ALPHABET for c in cle):
        raise ValueError("La clé doit être une chaîne de lettres non vide.")
    return cle


def chiffre_vigenere(texte, cle):
    """Chiffre avec Vigenère ; la clé n'avance que sur les lettres.

    ``i_cle`` compte les lettres réellement rencontrées. Les espaces ne
    consomment pas de lettre de clé : les mots restent séparés, ce qui rend
    l'attaque fréquentielle par colonnes possible.
    """
    cle = _valider(cle)

    resultat = ""
    i_cle = 0
    for c in texte:
        if c.upper() in ALPHABET:
            # Le modulo permet de recycler la clé quand le texte est plus long.
            k = ord(cle[i_cle % len(cle)]) - ord("A")
            resultat += _decale(c, k)
            i_cle += 1
        else:
            resultat += c
    return resultat


def chiffre_vigenere_positions(texte, cle):
    """Vigenère positionnel : la clé avance sur tous les caractères, espaces compris.

    Ici c'est la position brute ``position`` qui indexe la clé. Les espaces
    sont donc aussi décalés (un espace devient une lettre et inversement) :
    le texte chiffré ne garde aucune trace des séparateurs de mots.
    """
    cle = _valider(cle)

    return "".join(
        _decale(c, ord(cle[position % len(cle)]) - ord("A"))
        for position, c in enumerate(texte)
    )


def cle_inverse_vigenere(cle):
    """Clé de déchiffrement : chaque lettre est remplacée par son décalage opposé.

    Si la clé de chiffrement est "A" (0), l'inverse est "A" (0) ;
    si elle est "C" (2), l'inverse est "Y" (24), car 2 + 24 = 26 ≡ 0 mod 26.
    """
    return "".join(chr((26 - (ord(c) - ord("A"))) % 26 + ord("A")) for c in cle.upper())


def dechiffre_vigenere(texte, cle):
    """Déchiffre un texte chiffré avec Vigenère (décalages inversés).

    On réutilise le chiffrement avec la clé inversée : C + (-k) = P.
    """
    return chiffre_vigenere(texte, cle_inverse_vigenere(cle))


def dechiffre_vigenere_positions(texte, cle):
    """Déchiffre un texte chiffré avec le Vigenère positionnel."""
    return chiffre_vigenere_positions(texte, cle_inverse_vigenere(cle))
