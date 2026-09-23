ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _decale(c, k):
    """Décale un caractère alphabétique de k rangs, en préservant la casse."""
    if c.upper() not in ALPHABET:
        return c
    base = "A" if c.isupper() else "a"
    return chr((ord(c) - ord(base) + k) % 26 + ord(base))


def chiffre_vigenere(texte, cle):
    """Chiffre un texte avec le chiffrement de Vigenère.

    La clé n'avance que sur les lettres (les espaces et la
    ponctuation ne consomment pas de caractère de clé).
    """
    cle = cle.upper()
    if not cle or not all(c in ALPHABET for c in cle):
        raise ValueError("La clé doit être une chaîne de lettres non vide.")

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


def dechiffre_vigenere(texte, cle):
    """Déchiffre un texte chiffré avec Vigenère (décalages inversés)."""
    cle_inverse = "".join(chr((26 - (ord(c) - ord("A"))) % 26 + ord("A")) for c in cle.upper())
    return chiffre_vigenere(texte, cle_inverse)


# if __name__ == "__main__":
#     message = "ATTACK AT DAWN"
#     cle = "LEMON"
#     chiffre = chiffre_vigenere(message, cle)
#     print("Clair   :", message)
#     print("Clé     :", cle)
#     print("Chiffre :", chiffre)
#     print("Déchiffre :", dechiffre_vigenere(chiffre, cle))