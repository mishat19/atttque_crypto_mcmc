"""Génère un cryptogramme de test pour l'attaque MCMC.

Exemples :

    python3 mcmc/chiffrer.py --mode lettres --graine 1
    python3 mcmc/chiffrer.py --mode positions --longueur-cle 4 --longueur 3000 --graine 1

Le script affiche la clé de chiffrement et la clé de déchiffrement attendues,
puis écrit le cryptogramme dans ``chiffre.txt`` ou ``chiffre_positions.txt``.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(DOSSIER))

from permutation.bloc import (  # noqa: E402
    chiffrer as chiffrer_positions,
    cle_inverse as cle_inverse_positions,
    definir_cle as definir_cle_positions,
    formater_cle as formater_positions,
)
from utils.initialisation import (  # noqa: E402
    cle_aleatoire,
    cle_aleatoire_positions,
)
from utils.score import lire_texte  # noqa: E402
from utils.substitution import (  # noqa: E402
    chiffrer as chiffrer_lettres,
    cle_inverse as cle_inverse_lettres,
    verifier_cle as verifier_cle_lettres,
)

CHEMIN_CLAIR = DOSSIER / "clair.txt"
CHEMIN_SORTIE_LETTRES = DOSSIER / "chiffre.txt"
CHEMIN_SORTIE_POSITIONS = DOSSIER / "chiffre_positions.txt"


def construire_parseur():
    parser = argparse.ArgumentParser(
        description="Chiffre un texte clair pour préparer un test MCMC."
    )
    parser.add_argument(
        "--mode",
        choices=("lettres", "positions"),
        default="lettres",
    )
    parser.add_argument("--clair", type=Path, default=CHEMIN_CLAIR)
    parser.add_argument("--sortie", type=Path, default=None)
    parser.add_argument(
        "--longueur",
        type=int,
        default=None,
        help="nombre de caractères à chiffrer (défaut : 1500 lettres, 3000 positions)",
    )
    parser.add_argument(
        "--longueur-cle",
        type=int,
        default=4,
        help="longueur de la clé de permutation (mode positions)",
    )
    parser.add_argument(
        "--cle",
        default=None,
        help="clé imposée : 26 lettres, ou valeurs de permutation (ex. 3021)",
    )
    parser.add_argument("--graine", type=int, default=None)
    return parser


def main(argv=None):
    parser = construire_parseur()
    args = parser.parse_args(argv)

    if args.graine is not None:
        random.seed(args.graine)

    try:
        clair = lire_texte(args.clair)
    except FileNotFoundError:
        parser.error(f"Fichier introuvable : {args.clair}")

    if not clair:
        parser.error("Le texte clair est vide.")

    if args.mode == "positions":
        longueur = args.longueur if args.longueur is not None else 3000
        if args.longueur_cle < 2:
            parser.error("--longueur-cle doit être au moins 2.")
        if longueur < args.longueur_cle:
            parser.error("--longueur doit être >= --longueur-cle.")
    else:
        longueur = args.longueur if args.longueur is not None else 1500
        if longueur < 1:
            parser.error("--longueur doit être au moins 1.")

    clair = clair[:longueur]
    sortie = args.sortie
    if sortie is None:
        sortie = (
            CHEMIN_SORTIE_POSITIONS
            if args.mode == "positions"
            else CHEMIN_SORTIE_LETTRES
        )

    if args.mode == "positions":
        if args.cle is None:
            cle_chiffrement = cle_aleatoire_positions(args.longueur_cle)
        else:
            try:
                cle_chiffrement = definir_cle_positions(args.cle)
            except ValueError as exc:
                parser.error(str(exc))
        if len(cle_chiffrement) != args.longueur_cle:
            parser.error(
                f"La clé fournie a une longueur {len(cle_chiffrement)}, "
                f"attendue {args.longueur_cle}."
            )

        cle_dechiffrement = cle_inverse_positions(cle_chiffrement)
        chiffre = chiffrer_positions(clair, cle_chiffrement)

        print("=== Chiffrement par permutation de positions ===")
        print(f"Clé de chiffrement : {formater_positions(cle_chiffrement)}")
        print(f"Clé de déchiffrement : {formater_positions(cle_dechiffrement)}")
    else:
        if args.cle is None:
            cle_chiffrement = cle_aleatoire()
        else:
            cle_chiffrement = "".join(args.cle.upper().split())
            if not verifier_cle_lettres(cle_chiffrement):
                parser.error(
                    "La clé de lettres doit être une permutation des 26 lettres."
                )

        cle_dechiffrement = cle_inverse_lettres(cle_chiffrement)
        chiffre = chiffrer_lettres(clair, cle_chiffrement)

        print("=== Chiffrement par substitution de lettres ===")
        print(f"Clé de chiffrement   : {cle_chiffrement}")
        print(f"Clé de déchiffrement : {cle_dechiffrement}")

    with open(sortie, "w", encoding="utf-8") as fichier:
        fichier.write(chiffre)

    print(f"Longueur      : {len(clair)} caractères")
    print(f"Clair         : {clair[:70]}")
    print(f"Chiffré       : {chiffre[:70]}")
    print(f"Cryptogramme écrit dans : {sortie}")


if __name__ == "__main__":
    main()
