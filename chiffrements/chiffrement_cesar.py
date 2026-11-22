"""Chiffrement de César : décalage fixe appliqué à toutes les lettres.

C'est la brique de base réutilisée partout :
- par l'interface web pour la carte "César" ;
- par l'attaque fréquentielle (chaque colonne de Vigenère est un César) ;
- par la substitution MCMC via ``mcmc/utils/substitution.py`` (autre clé).

L'alphabet utilisé est l'alphabet latin de 26 lettres (A-Z, a-z).
Les accents, la ponctuation, les espaces et les chiffres ne sont pas décalés :
ils sont recopiés tels quels dans le résultat.
"""

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def chiffre_cesar(texte, decalage):
    """Chiffre un texte avec le chiffrement de César (décalage vers la droite).

    Formule : C = (P + decalage) mod 26, où P est le rang de la lettre claire
    (A=0, B=1, ... Z=25). Le modulo 26 fait "reboucler" Z vers A.
    """
    resultat = ""
    for c in texte:
        # On travaille sur c.upper() pour tester l'appartenance à l'alphabet,
        # mais on garde la casse d'origine pour le caractère de sortie.
        if c.upper() in ALPHABET:
            # "A" si la lettre est majuscule, "a" sinon : c'est l'origine
            # des codes ASCII (65 pour A, 97 pour a) utilisée pour le calcul.
            base = "A" if c.isupper() else "a"
            resultat += chr((ord(c) - ord(base) + decalage) % 26 + ord(base))
        else:
            resultat += c  # on garde intactes les espaces, accents, ponctuation...
    return resultat


def dechiffre_cesar(texte, decalage):
    """Déchiffre un texte chiffré avec César (décalage inverse).

    Un décalage de +3 est annulé par un décalage de -3 : on réutilise donc
    directement la fonction de chiffrement avec le décalage opposé.
    """
    return chiffre_cesar(texte, -decalage)
