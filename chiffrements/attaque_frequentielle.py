"""Attaque fréquentielle d'un chiffre polyalphabétique de période L.

Les positions j, j+L, j+2L... forment un César, attaqué par sa distribution de lettres.

Principe général
----------------
Dans un chiffre de Vigenère de période L, toutes les lettres dont l'indice
vaut j modulo L ont reçu le même décalage. Elles forment donc une "colonne"
qui est un simple chiffre de César. Si le texte est assez long, on peut
retrouver le décalage de chaque colonne en comparant son histogramme de
lettres à celui du français : c'est ``scores_decalages``.

Le mode ``flux="positions"`` couvre le chiffre combiné (Vigenère positionnel
puis permutation par blocs) : la clé se répète sur les positions brutes, et
les lettres d'une même colonne sont ensuite réordonnées. Une fois les
décalages trouvés, il reste à deviner l'ordre des colonnes : on essaie
toutes les permutations (L! hypothèses) et on garde celle dont le texte
démêlé a le meilleur score de bigrammes.
"""

import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.chiffrement_cesar import ALPHABET, dechiffre_cesar

# Fréquence des lettres en français (pourcentage, somme ≈ 100).
# Source : distribution classique du français écrit. On l'utilise comme
# "référence" : pour chaque décalage possible, on calcule la somme des
# fréquences observées × fréquences supposées du clair.
FREQUENCES_FR = {
    "A": 8.11, "B": 0.81, "C": 3.38, "D": 4.28, "E": 17.69,
    "F": 1.13, "G": 1.19, "H": 0.74, "I": 7.31, "J": 0.18,
    "K": 0.02, "L": 5.69, "M": 2.74, "N": 7.11, "O": 5.23,
    "P": 3.01, "Q": 1.36, "R": 6.55, "S": 8.09, "T": 7.07,
    "U": 5.74, "V": 1.32, "W": 0.04, "X": 0.46, "Y": 0.30,
    "Z": 0.12,
}

# Poids log approximatifs des bigrammes du français, utiles pour retrouver
# l'ordre des positions quand le flux a ete melange par une permutation.
# Les bigrammes très fréquents (LE, ET, DE...) ont un poids élevé ; les couples
# rares valent 1, donc log(1) = 0 : ils n'apportent aucune information.
_BIGRAM_LOG = {
    "LE": 125, "DE": 112, "ES": 100, "EN": 96, "TE": 85, "RE": 75, "NT": 70,
    "ON": 65, "LA": 60, "LI": 55, "SE": 50, "ME": 48, "NE": 45, "DU": 42,
    "QU": 40, "EU": 38, "QUE": 35, "TU": 33, "ET": 120, "UN": 30, "DI": 28,
    "CE": 26, "RA": 24, "MA": 22, "SA": 21, "ST": 20, "UR": 19, "SU": 18,
    "PA": 17, "RI": 16, "RO": 15, "CO": 14, "AI": 13, "VE": 12, "EL": 11,
    "EM": 9, "IL": 8, "PR": 7, "CH": 6, "TR": 5, "PO": 4, "OR": 4, "TA": 3,
    "PE": 3, "MI": 2, "MO": 2, "BE": 2, "OC": 1, "EX": 1, "PL": 1,
}


def _log_bigram(a, b):
    # Le .get(..., 1) donne log(1) = 0 pour un bigramme inconnu.
    return math.log(_BIGRAM_LOG.get(a + b, 1))


def _score_bigram(texte):
    """Note moyenne par bigramme francophone d'un texte (majuscules uniquement).

    On fait une moyenne et non une somme pour pouvoir comparer des textes de
    longueurs différentes (les blocs sont de tailles variables).
    """
    score = 0.0
    nombre = 0
    for i in range(len(texte) - 1):
        a, b = texte[i], texte[i + 1]
        # On ignore les caractères hors alphabet (espaces, accents, ponctuation).
        if "A" <= a <= "Z" and "A" <= b <= "Z":
            score += _log_bigram(a, b)
            nombre += 1
    return score / max(nombre, 1)


def _ordre(permutation, taille: int) -> list[int]:
    """Indices d'un bloc tries par valeur de permutation (dernier bloc incomplet inclus).

    Exemple avec p = (3, 0, 2, 1) et taille = 4 :
    les valeurs 0, 1, 2, 3 sont aux indices 1, 3, 2, 0, donc _ordre renvoie
    [1, 3, 2, 0]. Cet ordre est utilisé pour lire le bloc réordonnée.
    """
    return sorted(range(taille), key=lambda i: (permutation[i], i))


def _unmixer(texte_partiel, permutation, periode: int) -> str:
    """Annule le melange de positions bloc par bloc.

    ``texte_partiel`` est le texte dont le Vigenere a ete retire colonne par
    colonne mais dont les positions restent melangees.  Rendre ``permutation``
    replace chaque caractere a sa position d'origine dans son bloc.

    Le texte est découpé en blocs de ``periode`` caractères (le dernier peut
    être plus court). Dans chaque bloc, ``ordre`` donne l'indice source de
    chaque destination ; on écrit donc ``replace[source] = bloc[destination]``.
    """
    resultat = []
    for debut in range(0, len(texte_partiel), periode):
        bloc = texte_partiel[debut:debut + periode]
        taille = len(bloc)
        ordre = _ordre(permutation, taille)
        replace = [""] * taille
        for destination, source in enumerate(ordre):
            replace[source] = bloc[destination]
        resultat.append("".join(replace))
    return "".join(resultat)


def _recuperer_permutation(texte_partiel, decalages, periode: int) -> tuple[int, ...]:
    """Cherche l'ordre de permutation qui remet le texte partiel en clair francais.

    Teste toutes les permutations de ``range(periode)`` et retient celle dont
    le demelange obtient le meilleur score bigramme.

    Attention : la complexité est en L! (pour L = 8, 40 320 essais). C'est
    pour cela que l'interface web limite la période et que le côté MCMC
    propose une autre stratégie pour retrouver l'ordre des positions.
    ``decalages`` est reçu pour garder la signature explicite de l'étape ;
    le score porte sur le texte déjà corrigé colonne par colonne.
    """
    meilleur_score = None
    meilleure_permutation = None
    for candidate in itertools.permutations(range(periode)):
        candidate_texte = _unmixer(texte_partiel, candidate, periode)
        score = _score_bigram(candidate_texte)
        if meilleur_score is None or score > meilleur_score:
            meilleur_score = score
            meilleure_permutation = candidate
    return meilleure_permutation


def _indices(texte, flux):
    """Indices sur lesquels la clé se répète : "lettres" (Vigenère) ou "positions" (permutation)."""
    if flux == "lettres":
        # Vigenère classique : les espaces ne comptent pas dans la clé.
        return [i for i, c in enumerate(texte) if c.upper() in ALPHABET]
    if flux == "positions":
        # Vigenère positionnel : tous les caractères comptent, y compris les
        # espaces devenus des lettres après chiffrement.
        return list(range(len(texte)))
    raise ValueError("Flux inconnu : 'lettres' ou 'positions'.")


def colonnes(texte, periode, flux="lettres"):
    """Découpe le texte en `periode` colonnes d'indices de même décalage.

    ``indices[j::periode]`` prend un indice sur L : la colonne j contient
    exactement les caractères chiffrés avec la même lettre de clé.
    ``min(periode, len(indices))`` évite de créer des colonnes vides si le
    texte est plus court que la période.
    """
    if periode < 1:
        raise ValueError("La periode doit etre un entier positif.")
    indices = _indices(texte, flux)
    return [indices[j::periode] for j in range(min(periode, len(indices)))]


def scores_decalages(texte):
    """Note chaque décalage (0 à 25) par corrélation avec les fréquences du français.

    Pour un décalage d, on suppose que la lettre chiffrée c provient de la
    lettre claire (c - d) mod 26. La note est la somme, sur toutes les lettres
    observées, de fréquence_observée(c) × fréquence_française(clair_supposé).
    C'est une corrélation : le bon décalage maximise la ressemblance.
    """
    lettres = "".join(c for c in texte.upper() if c in ALPHABET)
    if not lettres:
        raise ValueError("Le cryptogramme ne contient aucune lettre.")

    effectif = len(lettres)
    observe = {c: lettres.count(c) / effectif for c in ALPHABET}
    scores = {}
    for decalage in range(26):
        score = 0.0
        for c in ALPHABET:
            suppose_clair = chr((ord(c) - ord("A") - decalage) % 26 + ord("A"))
            score += observe[c] * FREQUENCES_FR[suppose_clair]
        scores[decalage] = score
    return scores


def attaque_frequentielle_colonnes(cryptogramme, periode, flux="lettres"):
    """Retrouve un décalage par colonne du cryptogramme.

    Retourne un dictionnaire complet destiné à l'interface web : décalages,
    clé lue, fiabilité (écart entre le meilleur et le deuxième score),
    détails par colonne, texte partiellement déchiffré et permutation trouvée.
    """
    if periode > len(cryptogramme):
        raise ValueError("La periode ne peut pas depasser la taille du cryptogramme.")

    clair = list(cryptogramme)
    resultats = []
    decalages = []
    ecarts = []
    permutation = None

    # Étape 1 : attaquer chaque colonne comme un César indépendant.
    for index, indices in enumerate(colonnes(cryptogramme, periode, flux)):
        colonne = "".join(cryptogramme[i] for i in indices)
        notes = scores_decalages(colonne)
        classement = sorted(notes.items(), key=lambda kv: kv[1], reverse=True)
        decalage, score = classement[0]
        # L'écart avec le deuxième meilleur score mesure la confiance :
        # s'il est faible, l'attaque hésite entre deux décalages.
        ecart = score - classement[1][1]
        decalages.append(decalage)
        ecarts.append(ecart)

        # On applique immédiatement le décalage trouvé dans le texte de sortie.
        corrigee = dechiffre_cesar(colonne, decalage)
        for i, c in zip(indices, corrigee):
            clair[i] = c

        resultats.append({
            "colonne": index,
            "decalage": decalage,
            "score": round(score, 4),
            "ecart": round(ecart, 4),
            "lettres": len(indices),
            "notes": [{"decalage": d, "score": round(s, 4)} for d, s in classement],
        })

    texte = "".join(clair)
    cle_lue = "".join(chr(ord("A") + d) for d in decalages)
    positions_melangees = flux == "positions"

    # Étape 2 (mode permutation uniquement) : retrouver l'ordre des colonnes.
    if flux == "positions" and len(texte) >= 200:
        # decalages[k] est le decalage en position de sortie k = mot[inv_perm[k]].
        # Pour retrouver le mot cle dans son ordre naturel : mot[j] = decalages[permutation[j]].
        # Sous 200 caracteres, le score bigramme n'est pas assez fiable pour
        # deviner l'ordre ; on garde alors l'ordre des colonnes (lettres trouvees,
        # seul l'ordre manque).
        permutation = _recuperer_permutation(texte, decalages, periode)
        cle_lue = "".join(
            chr(ord("A") + decalages[permutation[j]]) for j in range(periode)
        )
        texte = _unmixer(texte, permutation, periode)
        positions_melangees = False

    return {
        "flux": flux,
        "periode": len(decalages),
        "decalages": decalages,
        "cle_lue": cle_lue,
        # La fiabilité globale est le plus mauvais des écarts : c'est le
        # maillon faible de l'attaque.
        "fiabilite": round(min(ecarts), 4) if ecarts else 0.0,
        "positions_melangees": positions_melangees,
        "colonnes": resultats,
        "texte": texte,
        "permutation": permutation,
    }
