"""Statistiques de bigrammes et score de crédibilité d'une clé.

Rappel de la formule du sujet :

    S(k) = ∏_{(x,y)} r(x,y)^{f_k(x,y)}

    r(x,y) = 1 + nombre de bigrammes xy dans le texte de référence
    f_k(x,y) = 1 + nombre de bigrammes xy dans le texte déchiffré avec k

Le produit porte sur les 27² couples (x,y).  Pour un couple absent de la
référence, r(x,y) = 1, donc son facteur vaut 1 : il est inutile de le stocker.

Interprétation : si l'on modélise le français par une chaîne de Markov d'ordre
1, la vraisemblance d'un texte T est ∏ p(x,y)^{nombre de xy dans T}.  Le score
est donc (à un facteur constant près) une vraisemblance lissée : plus il est
grand, plus le texte déchiffré ressemble au français.  Avec un a priori uniforme
sur les clés, la loi a posteriori de la clé est proportionnelle à S(k).

Le MCMC travaille en logarithme pour éviter des entiers de plusieurs milliers
de chiffres :

    log S(k) = Σ (1 + f_k(x,y)) · log r(x,y)
"""

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


def lire_chiffre(chemin):
    """Lit un cryptogramme sans modifier ses espaces.

    ``normaliser`` remplace les suites d'espaces par un seul espace.  C'est
    souhaitable pour un texte naturel, mais destructeur pour un cryptogramme
    issu d'une permutation de positions : deux espaces peuvent devenir
    voisins.  On se contente donc de retirer les fins de ligne.
    """
    with open(chemin, encoding="utf-8") as f:
        return f.read().replace("\r", "").replace("\n", "")


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


def construire_log_r(reference):
    """Version logarithmique de ``r`` : ``log(1 + nombre de bigrammes)``."""
    return {
        couple: math.log1p(n)
        for couple, n in compter_bigrammes(reference).items()
    }


def score_texte(texte_dechiffre, r):
    """
    S(k) = produit des r(x,y)^f_k(x,y), avec f_k = 1 + comptes.

    Version « naïve » en produit d'entiers, conservée pour les tests et pour
    vérifier la version logarithmique.
    """
    f = compter_bigrammes(texte_dechiffre)
    return math.prod(rr ** (1 + f[couple]) for couple, rr in r.items())


def score_log(texte_dechiffre, log_r):
    """Calcule ``log S(k)`` sans construire le produit géant.

    Le terme ``Σ log r(x,y)`` correspond aux ``+1`` de f_k et est constant pour
    une référence donnée ; on l'inclut pour que la valeur affichée soit
    exactement le logarithme du score du sujet.
    """
    f = compter_bigrammes(texte_dechiffre)
    baseline = sum(log_r.values())
    return baseline + sum(
        nombre * log_r[couple]
        for couple, nombre in f.items()
        if couple in log_r
    )


def calculer_score(texte_chiffre, cle, r, dechiffrer):
    """
    S(k) = produit des r(x,y)^f_k(x,y), avec f_k = 1 + comptes.
    """
    return score_texte(dechiffrer(texte_chiffre, cle), r)


def calculer_score_log(texte_chiffre, cle, log_r, dechiffrer):
    """Version logarithmique de ``calculer_score``."""
    return score_log(dechiffrer(texte_chiffre, cle), log_r)
