"""Attaque fréquentielle d'un chiffre polyalphabétique de période L.

Les positions j, j+L, j+2L... forment un César, attaqué par sa distribution de lettres.
"""

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
            "notes": [{"decalage": d, "score": round(s, 4)} for d, s in classement[:3]],
        })

    return {
        "flux": flux,
        "periode": len(decalages),
        "decalages": decalages,
        "cle_lue": "".join(chr(ord("A") + d) for d in decalages),
        "fiabilite": round(min(ecarts), 4) if ecarts else 0.0,
        "positions_melangees": flux == "positions",
        "colonnes": resultats,
        "texte": "".join(clair),
    }
