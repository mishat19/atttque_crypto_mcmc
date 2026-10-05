"""Attaque fréquentielle d'un chiffre polyalphabétique de période L.

Un chiffre polyalphabétique de période L revient à L chiffres de César
indépendants : à l'intérieur d'un bloc de L caractères, la position j reçoit
toujours le même décalage, quels que soient les blocs. Une colonne du
cryptogramme (les positions j, j+L, j+2L...) est donc un César à part entière,
que l'on attaque séparément par sa distribution de lettres.

C'est aussi le cas du chiffrement par permutation de position de
permutation.cryptogramme : la permutation envoie toute une colonne source vers
une même colonne destination, et le décalage Vigenère suit la colonne. Chaque
colonne du cryptogramme porte donc encore un décalage unique, et la même
attaque s'applique sans changement.

Une nuance pour la permutation : les décalages sont retrouvés colonne par
colonne, mais ils correspondent aux colonnes destination, pas à l'ordre des
lettres de la clé. Le texte clair est obtenu, le mot clé ne l'est pas sans un
travail de couplage supplémentaire.
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
    """Indices sur lesquels la clé se répète.

    "lettres" : la clé de Vigenère n'avance que sur les lettres.
    "positions" : la permutation de position réordonne toutes les positions,
    espaces compris, donc la clé se répète sur les positions brutes.
    """
    if flux == "lettres":
        return [i for i, c in enumerate(texte) if c.upper() in ALPHABET]
    if flux == "positions":
        return list(range(len(texte)))
    raise ValueError("Flux inconnu : 'lettres' ou 'positions'.")


def colonnes(texte, periode, flux="lettres"):
    """Découpe le texte en `periode` colonnes d'indices.

    Chaque colonne reçoit toujours le même décalage. La coupe se fait sur les
    indices et non sur des tranches de texte, donc la reconstruction est exacte
    quels que soient les espaces et la ponctuation.
    """
    if periode < 1:
        raise ValueError("La periode doit etre un entier positif.")
    indices = _indices(texte, flux)
    return [indices[j::periode] for j in range(min(periode, len(indices)))]


def scores_decalages(texte):
    """Note chaque decalage candidat (0 a 25).

    Chaque decalage est note par la correlation entre les frequences observees
    dans le texte et les frequences connues du francais : plus la note est
    haute, plus le decalage est probable.
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
    """Attaque par colonnes : retrouve un decalage par colonne du cryptogramme.

    Colonnes trop courtes (< 100 lettres) ne sont pas fiables et le signalent
    par un ecart faible entre le meilleur decalage et le deuxieme.

    `flux` indique sur quoi la clé se répète. Sur "positions" (permutation de
    position), les lettres obtenues sont bien les bonnes, mais chacune est
    rendue a la place de sa colonne destination et non de sa colonne source :
    le texte revient deciphre mais encore permute, et seule la permutation
    manque encore.
    """
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


# if __name__ == "__main__":
#     from chiffrements.chiffrement_vigenere import chiffre_vigenere
#     from permutation.cryptogramme import chiffre_cryptogramme, definir_cle
#     phrase = ("LE CHIFFREMENT DE VIGENERE UTILISE UNE CLE REPETEE SUR LE TEXTE ET "
#               "CHAQUE LETTRE DE LA CLE DECALE UNE POSITION DIFFERENTE LES LETTRES "
#               "SUIVANTES SONT DONC CHIFFREES AUTREMENT COMME DANS CESAR ") * 10
#     mot = "ORACLE"
#     print("Longueur :", len(phrase))
#
#     resultat = attaque_frequentielle_colonnes(chiffre_vigenere(phrase, mot), len(mot))
#     print("Vigenere     -> cle lue", resultat["cle_lue"], "| exact :", resultat["texte"] == phrase)
#
#     cle = definir_cle(mot)
#     resultat = attaque_frequentielle_colonnes(
#         chiffre_cryptogramme(phrase, cle), len(mot), flux="positions")
#     print("Permutation  -> decalages", resultat["decalages"],
#           "(shifts de la cle :", [ord(c) - 65 for c in mot], ")")
#     print("Permutation  -> ecart mini", resultat["fiabilite"],
#           "| positions encore melangees :", resultat["positions_melangees"])