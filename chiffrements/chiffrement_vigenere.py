ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _decale(c, k):
    """Décale un caractère alphabétique de k rangs, en préservant la casse."""
    if c.upper() not in ALPHABET:
        return c
    base = "A" if c.isupper() else "a"
    return chr((ord(c) - ord(base) + k) % 26 + ord(base))


def _valider(cle):
    """Clé de Vigenère normalisée, lettres non vides exigées."""
    cle = cle.upper()
    if not cle or not all(c in ALPHABET for c in cle):
        raise ValueError("La clé doit être une chaîne de lettres non vide.")
    return cle


def chiffre_vigenere(texte, cle):
    """Chiffre un texte avec le chiffrement de Vigenère.

    La clé n'avance que sur les lettres (les espaces et la
    ponctuation ne consomment pas de caractère de clé).
    """
    cle = _valider(cle)

    resultat = ""
    i_cle = 0
    for c in texte:
        if c.upper() in ALPHABET:
            k = ord(cle[i_cle % len(cle)]) - ord("A")
            resultat += _decale(c, k)
            i_cle += 1
        else:
            resultat += c
    return resultat


def chiffre_vigenere_positions(texte, cle):
    """Vigenère positionnel : la clé se répète tous les len(cle) caractères.

    Contrairement à chiffre_vigenere, les espaces et la ponctuation consomment
    eux aussi un caractère de clé. C'est cette variante qu'impose une
    permutation de position, où le décalage doit dépendre de la position dans
    le bloc et non du nombre de lettres déjà vues.
    """
    cle = _valider(cle)

    return "".join(
        _decale(c, ord(cle[position % len(cle)]) - ord("A"))
        for position, c in enumerate(texte)
    )


def cle_inverse_vigenere(cle):
    """Clé de déchiffrement : chaque lettre est remplacée par son décalage opposé."""
    return "".join(chr((26 - (ord(c) - ord("A"))) % 26 + ord("A")) for c in cle.upper())


def dechiffre_vigenere(texte, cle):
    """Déchiffre un texte chiffré avec Vigenère (décalages inversés)."""
    return chiffre_vigenere(texte, cle_inverse_vigenere(cle))


def dechiffre_vigenere_positions(texte, cle):
    """Déchiffre un texte chiffré avec le Vigenère positionnel."""
    return chiffre_vigenere_positions(texte, cle_inverse_vigenere(cle))


# if __name__ == "__main__":
#     message = "ATTACK AT DAWN"
#     cle = "LEMON"
#     chiffre = chiffre_vigenere(message, cle)
#     print("Clair   :", message)
#     print("Clé     :", cle)
#     print("Chiffre :", chiffre)
#     print("Déchiffre :", dechiffre_vigenere(chiffre, cle))