from chiffrements.chiffrement_vigenere import chiffre_vigenere, dechiffre_vigenere

def chiffre_vigenere_cryptogramme(texte_clair, decalage):
    """Applique la clé (décalage César) pour produire un cryptogramme."""
    return chiffre_vigenere(texte_clair, decalage % 26)


def dechiffre_vigenere_cryptogramme(cryptogramme, decalage):
    """Retrouve le texte clair d'un cryptogramme avec une clé connue."""
    return dechiffre_vigenere(cryptogramme, decalage % 26)