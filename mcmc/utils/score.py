import math
import string
import unicodedata
from collections import Counter

ALPHABET = string.ascii_uppercase + " "  # 27 symboles


def normaliser(texte):
    """
    Renvoie le texte sans accents, en majuscules, avec seulement des lettres et des espaces.
    """
    for lig, rempl in (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE")):
        texte = texte.replace(lig, rempl)
    decompose = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in decompose if unicodedata.category(c) != "Mn")
    filtre = "".join(c if c in ALPHABET else " " for c in sans_accents.upper())
    return " ".join(filtre.split())


def lire_texte(chemin):
    """
    Lit un fichier UTF-8 et renvoie le texte normalisé.
    """
    with open(chemin, encoding="utf-8") as f:
        return normaliser(f.read())


def compter_bigrammes(texte):
    """
    {(x, y): nombre de bigrammes xy dans le texte}.
    """
    return Counter(zip(texte, texte[1:]))


def construire_r(reference):
    """
    r(x, y) = 1 + nb de bigrammes xy dans la référence.

    Couples absents de la référence : r = 1, donc r^f = 1, inutile de les stocker.
    """
    return {couple: 1 + n for couple, n in compter_bigrammes(reference).items()}


def score_texte(texte_dechiffre, r):
    """
    S(k) = produit des r(x,y)^f_k(x,y), avec f_k = 1 + comptes.
    """
    f = compter_bigrammes(texte_dechiffre)
    return math.prod(rr ** (1 + f[couple]) for couple, rr in r.items())


def calculer_score(texte_chiffre, cle, r, dechiffrer):
    """
    S(k) = produit des r(x,y)^f_k(x,y), avec f_k = 1 + comptes.
    """
    return score_texte(dechiffrer(texte_chiffre, cle), r)