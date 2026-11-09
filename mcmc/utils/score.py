"""Statistiques de bigrammes et score de crédibilité d'une clé.

Rappel de la formule du sujet :

    S(k) = ∏_{(x,y)} r(x,y)^{f_k(x,y)}

    r(x,y) = 1 + nombre de bigrammes xy dans le texte de référence
    f_k(x,y) = 1 + nombre de bigrammes xy dans le texte déchiffré avec k

Pour un couple absent de la référence, r(x,y) = 1 : inutile de le stocker.
On travaille en logarithme pour éviter des entiers gigantesques :

    log S(k) = Σ (1 + f_k(x,y)) · log r(x,y)
"""

import math
import string
import unicodedata
from collections import Counter

ALPHABET = string.ascii_uppercase + " "  # 27 symboles


def normaliser(texte):
    """Texte sans accents, en majuscules, avec seulement des lettres et des espaces."""
    for lig, rempl in (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE")):
        texte = texte.replace(lig, rempl)
    decompose = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in decompose if unicodedata.category(c) != "Mn")
    filtre = "".join(c if c in ALPHABET else " " for c in sans_accents.upper())
    return " ".join(filtre.split())


def lire_texte(chemin):
    """Lit un fichier UTF-8 et renvoie le texte normalisé."""
    with open(chemin, encoding="utf-8") as f:
        return normaliser(f.read())


def lire_chiffre(chemin):
    """Lit un cryptogramme sans fusionner les espaces (une permutation peut
    rendre deux espaces voisins)."""
    with open(chemin, encoding="utf-8") as f:
        return f.read().replace("\r", "").replace("\n", "")


def compter_bigrammes(texte):
    """{(x, y): nombre de bigrammes xy dans le texte}."""
    return Counter(zip(texte, texte[1:]))


def construire_r(reference):
    """r(x, y) = 1 + nb de bigrammes xy dans la référence."""
    return {couple: 1 + n for couple, n in compter_bigrammes(reference).items()}


def construire_log_r(reference):
    """log r(x, y) = log(1 + nb de bigrammes xy)."""
    return {
        couple: math.log1p(n)
        for couple, n in compter_bigrammes(reference).items()
    }


def score_texte(texte_dechiffre, r):
    """S(k) calculé directement (produit d'entiers), sert à vérifier score_log."""
    f = compter_bigrammes(texte_dechiffre)
    return math.prod(rr ** (1 + f[couple]) for couple, rr in r.items())


def score_log(texte_dechiffre, log_r):
    """log S(k). Le terme Σ log r(x,y) correspond aux +1 de f_k."""
    f = compter_bigrammes(texte_dechiffre)
    baseline = sum(log_r.values())
    return baseline + sum(
        nombre * log_r[couple]
        for couple, nombre in f.items()
        if couple in log_r
    )


def calculer_score_log(texte_chiffre, cle, log_r, dechiffrer):
    """log S(k) du texte déchiffré avec la clé k."""
    return score_log(dechiffrer(texte_chiffre, cle), log_r)
