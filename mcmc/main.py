"""Attaque par MCMC des chiffrements par substitution et par permutation.

Deux modes, un seul moteur :

    python3 mcmc/main.py --mode lettres
    python3 mcmc/main.py --mode positions --longueur-max 8

Mode ``lettres``
    L'état est une clé de déchiffrement des 26 lettres.  La mutation échange
    deux lettres au hasard.

Mode ``positions``
    L'état est une permutation de ``0..ℓ-1`` pour une longueur ``ℓ`` fixée.
    La mutation déplace un sous-bloc.  On teste successivement ℓ = 2, 3, ...
    et l'humain compare les propositions de chaque longueur.

Le score, la sélection et les statistiques de référence sont communs aux deux
modes ; seule la façon de déchiffrer et de muter change.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(DOSSIER))

from permutation.bloc import (  # noqa: E402
    cle_inverse as cle_inverse_positions,
    dechiffrer as dechiffrer_positions,
    formater_cle as formater_positions,
)
from utils.initialisation import (  # noqa: E402
    cle_aleatoire,
    cle_aleatoire_positions,
    cle_heuristique,
)
from utils.mutation import muter_lettres, muter_positions  # noqa: E402
from utils.score import (  # noqa: E402
    calculer_score_log,
    construire_log_r,
    lire_chiffre,
    lire_texte,
)
from utils.selection import accepter_log  # noqa: E402
from utils.substitution import (  # noqa: E402
    cle_inverse as cle_inverse_lettres,
    dechiffrer as dechiffrer_lettres,
)

CHEMIN_REFERENCE = DOSSIER / "reference.txt"
CHEMIN_CHIFFRE_LETTRES = DOSSIER / "chiffre.txt"
CHEMIN_CHIFFRE_POSITIONS = DOSSIER / "chiffre_positions.txt"

N_DEFAUT_ITERATIONS = 20_000
N_DEFAUT_PROPOSITIONS = 5
CHAUFFE_DEFAUT = 0.10
LONGUEUR_MIN_DEFAUT = 2
LONGUEUR_MAX_DEFAUT = 8


# =============== MOTEUR MCMC ===============

def marche_mcmc(texte_chiffre, cle_initiale, log_r, dechiffrer, muter,
                n_iterations, chauffe=0):
    """Fait tourner la chaîne et renvoie les états visités après la chauffe.

    Retour : ``(etats, candidats)``.

    ``etats`` : ``{clé: {"score": log S(clé), "visites": nombre de visites}}``
    pour les états réellement occupés après la chauffe.

    ``candidats`` : ``{clé: {"score": ..., "propositions": ...}}`` pour toutes
    les clés évaluées, acceptées ou non.  Cela permet d'afficher plusieurs
    alternatives même quand la chaîne s'est concentrée sur un seul état.
    """
    if n_iterations <= chauffe:
        raise ValueError("Il faut au moins une itération après la période de chauffe.")

    cle = cle_initiale
    score = calculer_score_log(texte_chiffre, cle, log_r, dechiffrer)
    cache = {cle: score}
    etats: dict = {}
    candidats: dict = {}

    for iteration in range(n_iterations):
        candidate = muter(cle)
        if candidate in cache:
            score_candidat = cache[candidate]
        else:
            score_candidat = calculer_score_log(
                texte_chiffre, candidate, log_r, dechiffrer
            )
            cache[candidate] = score_candidat

        info_candidat = candidats.get(candidate)
        if info_candidat is None:
            candidats[candidate] = {"score": score_candidat, "propositions": 1}
        else:
            info_candidat["propositions"] += 1
            info_candidat["score"] = max(info_candidat["score"], score_candidat)

        if accepter_log(score, score_candidat):
            cle, score = candidate, score_candidat

        if iteration >= chauffe:
            info = etats.get(cle)
            if info is None:
                etats[cle] = {"score": score, "visites": 1}
            else:
                info["visites"] += 1
                info["score"] = score

    # La clé initiale peut avoir été visitée sans avoir été proposée.
    for cle_etat, info_etat in etats.items():
        if cle_etat not in candidats:
            candidats[cle_etat] = {"score": info_etat["score"], "propositions": 0}

    return etats, candidats


def fusionner_etats(destination, source):
    """Fusionne les résultats de plusieurs redémarrages pour une même longueur."""
    for cle, info in source.items():
        if cle in destination:
            destination[cle]["visites"] += info["visites"]
            destination[cle]["score"] = max(destination[cle]["score"], info["score"])
        else:
            destination[cle] = dict(info)


def fusionner_candidats(destination, source):
    """Fusionne les candidats évalués par plusieurs redémarrages."""
    for cle, info in source.items():
        if cle in destination:
            destination[cle]["propositions"] += info["propositions"]
            destination[cle]["score"] = max(destination[cle]["score"], info["score"])
        else:
            destination[cle] = dict(info)


def fusionner_vue(etats, candidats):
    """Réunit visites et propositions dans une même table pour le classement."""
    vue = {
        cle: {
            "score": info["score"],
            "visites": 0,
            "propositions": info["propositions"],
        }
        for cle, info in candidats.items()
    }
    for cle, info in etats.items():
        if cle in vue:
            vue[cle]["visites"] = info["visites"]
            vue[cle]["score"] = max(vue[cle]["score"], info["score"])
        else:
            vue[cle] = {
                "score": info["score"],
                "visites": info["visites"],
                "propositions": 0,
            }
    return vue


def classer(etats, n, critere="score"):
    """Renvoie les ``n`` meilleurs états.

    ``critere="score"`` classe par log S décroissant, puis par visites.
    ``critere="visites"`` classe par nombre de visites, puis par score.
    """
    if critere == "visites":
        return sorted(
            etats.items(),
            key=lambda item: (-item[1]["visites"], -item[1]["score"]),
        )[:n]
    return sorted(
        etats.items(),
        key=lambda item: (-item[1]["score"], -item[1]["visites"]),
    )[:n]


# =============== AFFICHAGE ===============

def afficher_propositions(propositions, chiffre, dechiffrer, inverse, formater,
                          titre=None):
    """Affiche une petite famille de clés candidates et le texte associé."""
    if titre:
        print(titre)
    for numero, (cle, info) in enumerate(propositions, start=1):
        propositions_recues = info.get("propositions", 0)
        print(
            f"Proposition {numero}  "
            f"(log S = {info['score']:.1f}, visites = {info['visites']}, "
            f"proposée = {propositions_recues})"
        )
        print(f"  clé         : {formater(cle)}")
        print(f"  clé inverse : {formater(inverse(cle))}")
        print(f"  texte       : {dechiffrer(chiffre, cle)[:100]}")
        print()


def verifier_entrees(reference, chiffre):
    if not reference:
        raise ValueError("Le texte de référence est vide.")
    if not chiffre:
        raise ValueError("Le texte chiffré est vide.")


# =============== MODE LETTRES ===============

def attaque_lettres(args):
    reference = lire_texte(args.reference)
    chiffre = lire_chiffre(args.chiffre)
    verifier_entrees(reference, chiffre)

    log_r = construire_log_r(reference)
    if args.initialisation == "aleatoire":
        cle_initiale = cle_aleatoire()
    else:
        cle_initiale = cle_heuristique(chiffre, reference)

    chauffe = int(args.iterations * args.chauffe)
    score_initial = calculer_score_log(
        chiffre, cle_initiale, log_r, dechiffrer_lettres
    )

    print("=== Attaque MCMC : substitution de lettres ===")
    print(f"Référence      : {args.reference}")
    print(f"Chiffré        : {args.chiffre}")
    print(f"Itérations     : {args.iterations} (chauffe : {chauffe})")
    print(f"Clé initiale   : {cle_initiale} (log S = {score_initial:.1f})")
    print()

    etats, candidats = marche_mcmc(
        chiffre,
        cle_initiale,
        log_r,
        dechiffrer_lettres,
        muter_lettres,
        args.iterations,
        chauffe,
    )
    vue = fusionner_vue(etats, candidats)
    propositions = classer(vue, args.propositions, args.classement)
    afficher_propositions(
        propositions,
        chiffre,
        dechiffrer_lettres,
        cle_inverse_lettres,
        str,
        titre="=== Propositions ===",
    )
    if len(propositions) < args.propositions:
        print(
            f"({len(propositions)} clé(s) distincte(s) retenue(s) ; "
            "la chaîne s'est concentrée sur une famille réduite.)"
        )


# =============== MODE POSITIONS ===============

def attaque_positions(args):
    reference = lire_texte(args.reference)
    chiffre = lire_chiffre(args.chiffre)
    verifier_entrees(reference, chiffre)

    log_r = construire_log_r(reference)
    chauffe = int(args.iterations * args.chauffe)

    print("=== Attaque MCMC : permutation de positions ===")
    print(f"Référence      : {args.reference}")
    print(f"Chiffré        : {args.chiffre}")
    print(f"Itérations / ℓ : {args.iterations} (chauffe : {chauffe})")
    print(f"Redémarrages   : {args.redemarrages}")
    print()

    resultats = []

    for longueur in range(args.longueur_min, args.longueur_max + 1):
        etats: dict = {}
        candidats: dict = {}
        for _ in range(args.redemarrages):
            cle_initiale = cle_aleatoire_positions(longueur)
            etats_marche, candidats_marche = marche_mcmc(
                chiffre,
                cle_initiale,
                log_r,
                dechiffrer_positions,
                muter_positions,
                args.iterations,
                chauffe,
            )
            fusionner_etats(etats, etats_marche)
            fusionner_candidats(candidats, candidats_marche)

        vue = fusionner_vue(etats, candidats)
        propositions = classer(vue, args.propositions, args.classement)
        resultats.append((longueur, propositions))

        meilleur_score = propositions[0][1]["score"]
        penalise = meilleur_score - math.lgamma(longueur + 1)
        afficher_propositions(
            propositions,
            chiffre,
            dechiffrer_positions,
            cle_inverse_positions,
            formater_positions,
            titre=(
                f"=== ℓ = {longueur}  |  meilleur log S = {meilleur_score:.1f}  "
                f"|  log S - log(ℓ!) = {penalise:.1f} ==="
            ),
        )
        if len(propositions) < args.propositions:
            print(
                f"({len(propositions)} clé(s) distincte(s) retenue(s) ; "
                "la chaîne s'est concentrée sur une famille réduite.)"
            )
            print()

    print("=== Résumé ===")
    print(f"{'ℓ':>3}  {'meilleur log S':>15}  {'log S - log(ℓ!)':>18}  clé")
    for longueur, propositions in resultats:
        cle, info = propositions[0]
        penalise = info["score"] - math.lgamma(longueur + 1)
        print(
            f"{longueur:>3}  {info['score']:>15.1f}  {penalise:>18.1f}  "
            f"{formater_positions(cle)}"
        )

    print()
    print("Les scores de plusieurs ℓ ne sont pas directement comparables :")
    print("l'espace des clés grandit en ℓ! et un ℓ trop grand peut sur-ajuster.")
    print("La colonne log S - log(ℓ!) est une correction grossière ;")
    print("le choix final se fait en lisant les extraits déchiffrés.")
    print("Une clé périodique peut aussi reproduire le texte avec un ℓ multiple")
    print("de la vraie longueur : préférer la plus petite longueur lisible.")


# =============== CLI ===============

def construire_parseur():
    parser = argparse.ArgumentParser(
        description="Attaque MCMC d'un chiffrement par substitution ou permutation."
    )
    parser.add_argument(
        "--mode",
        choices=("lettres", "positions"),
        default="lettres",
        help="substitution de lettres (1.3) ou permutation de positions (1.4)",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=CHEMIN_REFERENCE,
        help="texte de référence pour les bigrammes",
    )
    parser.add_argument(
        "--chiffre",
        type=Path,
        default=None,
        help="cryptogramme à attaquer (défaut selon le mode)",
    )
    parser.add_argument("--iterations", type=int, default=N_DEFAUT_ITERATIONS)
    parser.add_argument("--propositions", type=int, default=N_DEFAUT_PROPOSITIONS)
    parser.add_argument(
        "--chauffe",
        type=float,
        default=CHAUFFE_DEFAUT,
        help="fraction des itérations ignorée au début (0 <= chauffe < 1)",
    )
    parser.add_argument("--graine", type=int, default=None)
    parser.add_argument(
        "--initialisation",
        choices=("heuristique", "aleatoire"),
        default="heuristique",
        help="mode lettres uniquement",
    )
    parser.add_argument("--longueur-min", type=int, default=LONGUEUR_MIN_DEFAUT)
    parser.add_argument("--longueur-max", type=int, default=LONGUEUR_MAX_DEFAUT)
    parser.add_argument("--redemarrages", type=int, default=1)
    parser.add_argument(
        "--classement",
        choices=("score", "visites"),
        default="score",
        help="critère de conservation des meilleures clés",
    )
    return parser


def main(argv=None):
    parser = construire_parseur()
    args = parser.parse_args(argv)

    if args.iterations < 1:
        parser.error("--iterations doit être au moins 1.")
    if not 0 <= args.chauffe < 1:
        parser.error("--chauffe doit être dans [0 ; 1[.")
    if args.propositions < 1:
        parser.error("--propositions doit être au moins 1.")

    if args.chiffre is None:
        args.chiffre = (
            CHEMIN_CHIFFRE_POSITIONS
            if args.mode == "positions"
            else CHEMIN_CHIFFRE_LETTRES
        )

    if args.mode == "positions":
        if args.longueur_min < 2:
            parser.error("--longueur-min doit être au moins 2.")
        if args.longueur_max < args.longueur_min:
            parser.error("--longueur-max doit être >= --longueur-min.")
        if args.redemarrages < 1:
            parser.error("--redemarrages doit être au moins 1.")

    if args.graine is not None:
        random.seed(args.graine)

    try:
        if args.mode == "positions":
            attaque_positions(args)
        else:
            attaque_lettres(args)
    except FileNotFoundError as exc:
        parser.error(
            f"Fichier introuvable : {exc.filename}. "
            "Générez un cryptogramme avec mcmc/chiffrer.py (--mode lettres ou positions)."
        )
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()


# =============== JUSTIFICATIONS THÉORIQUES ===============
#
# 1. Pourquoi S(k) est une crédibilité.
#    Un modèle de Markov d'ordre 1 du français donne à un texte T la
#    vraisemblance ∏ p(x,y)^{nombre de xy dans T}.  En estimant p(x,y) par
#    (1 + compte dans la référence) / constante, le score S(k) est une
#    vraisemblance lissée du texte déchiffré.  Avec un a priori uniforme sur
#    les clés, la loi a posteriori est proportionnelle à S(k) : les clés qui
#    produisent un texte proche du français sont les plus crédibles.
#
# 2. Irréductibilité, mode lettres.
#    Les échanges de deux positions engendrent toutes les permutations de 26
#    lettres (les transpositions forment un système générateur de S_26).  On
#    peut donc aller de n'importe quelle clé à n'importe quelle autre.
#
# 3. Irréductibilité, mode positions.
#    Le déplacement d'un seul élément (L = 1) est un cas particulier de la
#    mutation.  Ces déplacements engendrent toutes les permutations de ℓ
#    éléments : on peut donc atteindre toute clé parmi les ℓ! clés possibles.
#
# 4. Apériodicité.
#    Dans le mode positions, le déplacement identitaire (i = d) a une
#    probabilité strictement positive : la chaîne peut rester sur place.
#    Dans le mode lettres, un refus de Metropolis a lui aussi une probabilité
#    strictement positive (il existe des voisins de score inférieur).  Une
#    chaîne irréductible avec une auto-transition est apériodique.
#
# 5. Loi stationnaire.
#    La proposition est symétrique : pour les lettres, échanger i et j est
#    réversible ; pour les positions, l'inverse de (i, L, d) est (d, L, i).
#    L'acceptation min(1, S(k')/S(k)) vérifie donc l'équilibre détaillé pour
#    π(k) ∝ S(k).  C'est exactement la loi stable cherchée : les clés les plus
#    crédibles sont visitées le plus souvent.
#
# 6. Choix de ℓ.
#    Pour un ℓ fixé, la chaîne explore ℓ! clés.  Comparer les scores de
#    longueurs différentes revient à comparer des modèles de tailles
#    différentes : un ℓ plus grand peut mieux coller aux bigrammes par hasard.
#    D'où l'affichage de log S - log(ℓ!) et, surtout, la lecture humaine des
#    textes déchiffrés.
