ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def chiffre_cesar(texte, decalage):
    """Chiffre un texte avec le chiffrement de César (décalage vers la droite)."""
    resultat = ""
    for c in texte:
        if c.upper() in ALPHABET:
            base = "A" if c.isupper() else "a"
            resultat += chr((ord(c) - ord(base) + decalage) % 26 + ord(base))
        else:
            resultat += c  # on garde intactes les espaces, accents, ponctuation...
    return resultat


def dechiffre_cesar(texte, decalage):
    """Déchiffre un texte chiffré avec César (décalage inverse)."""
    return chiffre_cesar(texte, -decalage)


# if __name__ == "__main__":
#     message = "ATTACK AT DAWN"
#     chiffre = chiffre_cesar(message, 3)
#     print("Clair   :", message)
#     print("Chiffre :", chiffre)
#     print("Déchiffre :", dechiffre_cesar(chiffre, 3))