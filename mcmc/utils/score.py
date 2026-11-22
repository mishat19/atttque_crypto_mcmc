"""Statistiques de bigrammes et score de crédibilité d'une clé.

Rappel de la formule du sujet :

    S(k) = ∏_{(x,y)} r(x,y)^{f_k(x,y)}

    r(x,y) = 1 + nombre de bigrammes xy dans le texte de référence
    f_k(x,y) = 1 + nombre de bigrammes xy dans le texte déchiffré avec k

Interprétation : un bigramme fréquent en français (LE, DE, ET...) qui
apparaît aussi dans le texte déchiffré fait grimper le score. Un bigramme
impossible en français est pénalisé parce que r vaut 1 et que le déchiffrement
consomme une occurrence qui aurait pu aller à un meilleur bigramme.

Pour un couple absent de la référence, r(x,y) = 1 : inutile de le stocker.
On travaille en logarithme pour éviter des entiers gigantesques :

    log S(k) = Σ (1 + f_k(x,y)) · log r(x,y)
"""

import math
import string
import unicodedata
from collections import Counter

# 26 lettres + l'espace = 27 symboles. L'espace compte comme une "lettre" :
# le bigramme "L E" (avec espace) est très informatif en français.
ALPHABET = string.ascii_uppercase + " "  # 27 symboles


def normaliser(texte):
    """Texte sans accents, en majuscules, avec seulement des lettres et des espaces.

    Étapes :
    1. on déplie les ligatures œ/æ en deux lettres pour ne pas perdre de
       caractères (sinon "œuvre" deviendrait "uvr") ;
    2. NFD décompose "é" en "e" + accent combinant, qu'on supprime (catégorie
       Unicode Mn) ;
    3. tout ce qui n'est ni A-Z ni espace est remplacé par un espace ;
    4. ``" ".join(filtre.split())`` fusionne les espaces consécutifs.
    """
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
    rendre deux espaces voisins).

    Contrairement à ``lire_texte``, on ne normalise pas ici : chaque position
    du cryptogramme est significative pour la permutation. On retire juste
    les retours à la ligne pour obtenir un flux continu.
    """
    with open(chemin, encoding="utf-8") as f:
        return f.read().replace("\r", "").replace("\n", "")


def compter_bigrammes(texte):
    """{(x, y): nombre de bigrammes xy dans le texte}.

    ``zip(texte, texte[1:])`` fabrique les paires de caractères consécutifs :
    "ABCA" -> (A,B), (B,C), (C,A). Counter les décompte en un dictionnaire.
    """
    return Counter(zip(texte, texte[1:]))


def construire_r(reference):
    """r(x, y) = 1 + nb de bigrammes xy dans la référence."""
    return {couple: 1 + n for couple, n in compter_bigrammes(reference).items()}


def construire_log_r(reference):
    """log r(x, y) = log(1 + nb de bigrammes xy).

    ``math.log1p(n)`` calcule log(1 + n) avec une meilleure précision que
    ``math.log(1 + n)`` quand n est petit.
    """
    return {
        couple: math.log1p(n)
        for couple, n in compter_bigrammes(reference).items()
    }


def score_texte(texte_dechiffre, r):
    """S(k) calculé directement (produit d'entiers), sert à vérifier score_log.

    Le résultat est énorme (des milliers de puissances) : cette fonction n'est
    utilisée que dans les tests, pour vérifier l'égalité mathématique avec
    ``score_log``.
    """
    f = compter_bigrammes(texte_dechiffre)
    return math.prod(rr ** (1 + f[couple]) for couple, rr in r.items())


def score_log(texte_dechiffre, log_r):
    """log S(k). Le terme Σ log r(x,y) correspond aux +1 de f_k.

    En développant log S = Σ (1 + f_k) log r, on sépare :
    - ``baseline = Σ log r`` : constant, indépendant de la clé ;
    - ``Σ f_k(x,y) · log r(x,y)`` : la partie qui dépend du déchiffrement.

    Les bigrammes du texte déchiffrés absents de la référence n'ont pas de
    log r stocké (r = 1, log r = 0) : on les ignore avec le ``if``.
    """
    f = compter_bigrammes(texte_dechiffre)
    baseline = sum(log_r.values())
    return baseline + sum(
        nombre * log_r[couple]
        for couple, nombre in f.items()
        if couple in log_r
    )


def calculer_score_log(texte_chiffre, cle, log_r, dechiffrer):
    """log S(k) du texte déchiffré avec la clé k.

    ``dechiffrer`` est passé en paramètre (injection de dépendance) : c'est
    ce qui permet d'utiliser exactement le même moteur MCMC pour les lettres
    et pour les positions.
    """
    return score_log(dechiffrer(texte_chiffre, cle), log_r)
