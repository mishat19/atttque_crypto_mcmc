"""Attaque fréquentielle d'un chiffre polyalphabétique de période L.

Les positions j, j+L, j+2L... forment un César, attaqué par sa distribution de lettres.
"""

import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.chiffrement_cesar import ALPHABET, dechiffre_cesar

# Fréquence des lettres en français (pourcentage, somme ≈ 100).
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
    return math.log(_BIGRAM_LOG.get(a + b, 1))


def _score_bigram(texte):
    """Note moyenne par bigramme francophone d'un texte (majuscules uniquement)."""
    score = 0.0
    nombre = 0
    for i in range(len(texte) - 1):
        a, b = texte[i], texte[i + 1]
        if "A" <= a <= "Z" and "A" <= b <= "Z":
            score += _log_bigram(a, b)
            nombre += 1
    return score / max(nombre, 1)


def _ordre(permutation, taille: int) -> list[int]:
    """Indices d'un bloc tries par valeur de permutation (dernier bloc incomplet inclus)."""
    return sorted(range(taille), key=lambda i: (permutation[i], i))


def _unmixer(texte_partiel, permutation, periode: int) -> str:
    """Annule le melange de positions bloc par bloc.

    ``texte_partiel`` est le texte dont le Vigenere a ete retire colonne par
    colonne mais dont les positions restent melangees.  Rendre ``permutation``
    replace chaque caractere a sa position d'origine dans son bloc.
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
        return [i for i, c in enumerate(texte) if c.upper() in ALPHABET]
    if flux == "positions":
        return list(range(len(texte)))
    raise ValueError("Flux inconnu : 'lettres' ou 'positions'.")


def colonnes(texte, periode, flux="lettres"):
    """Découpe le texte en `periode` colonnes d'indices de même décalage."""
    if periode < 1:
        raise ValueError("La periode doit etre un entier positif.")
    indices = _indices(texte, flux)
    return [indices[j::periode] for j in range(min(periode, len(indices)))]


def scores_decalages(texte):
    """Note chaque décalage (0 à 25) par corrélation avec les fréquences du français."""
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
    """Retrouve un décalage par colonne du cryptogramme."""
    if periode > len(cryptogramme):
        raise ValueError("La periode ne peut pas depasser la taille du cryptogramme.")

    clair = list(cryptogramme)
    resultats = []
    decalages = []
    ecarts = []
    permutation = None

    for index, indices in enumerate(colonnes(cryptogramme, periode, flux)):
        colonne = "".join(cryptogramme[i] for i in indices)
        notes = scores_decalages(colonne)
        classement = sorted(notes.items(), key=lambda kv: kv[1], reverse=True)
        decalage, score = classement[0]
        ecart = score - classement[1][1]
        decalages.append(decalage)
        ecarts.append(ecart)

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
        "fiabilite": round(min(ecarts), 4) if ecarts else 0.0,
        "positions_melangees": positions_melangees,
        "colonnes": resultats,
        "texte": texte,
        "permutation": permutation,
    }
