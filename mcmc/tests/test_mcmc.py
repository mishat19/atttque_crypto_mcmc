"""Tests unitaires des briques utilisées par l'attaque MCMC.

Lancement depuis la racine du dépôt :

    python3 mcmc/tests/test_mcmc.py
"""

from __future__ import annotations

import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "mcmc"))

from permutation.bloc import (  # noqa: E402
    chiffrer as chiffrer_positions,
    cle_inverse as cle_inverse_positions,
    definir_cle as definir_cle_positions,
    dechiffrer as dechiffrer_positions,
    formater_cle as formater_cle_positions,
    verifier_cle as verifier_cle_positions,
)
from permutation.cryptogramme import (  # noqa: E402
    chiffre_cryptogramme,
    definir_cle as definir_cle_combinee,
    dechiffre_cryptogramme,
)
from utils.initialisation import cle_aleatoire_positions  # noqa: E402
from utils.mutation import deplacer_bloc, muter_positions  # noqa: E402
from utils.score import (  # noqa: E402
    construire_log_r,
    construire_r,
    lire_chiffre,
    score_log,
    score_texte,
)
from utils.substitution import (  # noqa: E402
    LETTRES,
    chiffrer as chiffrer_lettres,
    cle_inverse as cle_inverse_lettres,
    dechiffrer as dechiffrer_lettres,
    verifier_cle as verifier_cle_lettres,
)
from main import marche_mcmc  # noqa: E402


class TestPermutationBloc(unittest.TestCase):
    def test_exemple_du_sujet(self):
        self.assertEqual(chiffrer_positions("BONJOUR", "3021"), "OJNBURO")
        self.assertEqual(dechiffrer_positions("OJNBURO", "3021"), "BONJOUR")

    def test_cle_et_inverse(self):
        cle = (3, 0, 2, 1)
        self.assertEqual(cle_inverse_positions(cle), (1, 3, 2, 0))
        self.assertEqual(cle_inverse_positions(cle_inverse_positions(cle)), cle)

    def test_verification(self):
        self.assertTrue(verifier_cle_positions("3021"))
        self.assertTrue(verifier_cle_positions([3, 0, 2, 1]))
        self.assertFalse(verifier_cle_positions("3011"))
        self.assertFalse(verifier_cle_positions("301"))
        self.assertFalse(verifier_cle_positions(""))
        with self.assertRaises(ValueError):
            definir_cle_positions("3011")

    def test_aller_retour_aleatoire(self):
        rng = random.Random(1234)
        for longueur in range(2, 9):
            for _ in range(20):
                cle = cle_aleatoire_positions(longueur)
                texte = "".join(
                    rng.choice("ABC ") for _ in range(rng.randint(0, 80))
                )
                chiffre = chiffrer_positions(texte, cle)
                self.assertEqual(dechiffrer_positions(chiffre, cle), texte)
                self.assertEqual(
                    chiffrer_positions(dechiffrer_positions(texte, cle), cle),
                    texte,
                )

    def test_formater_cle_longue(self):
        cle = (10, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
        self.assertEqual(formater_cle_positions(cle), "10 0 1 2 3 4 5 6 7 8 9")
        self.assertEqual(definir_cle_positions(formater_cle_positions(cle)), cle)


class TestMutationPositions(unittest.TestCase):
    def test_mutation_conserve_permutation(self):
        for longueur in range(2, 9):
            cle = tuple(range(longueur))
            for _ in range(100):
                nouvelle = muter_positions(cle)
                self.assertEqual(len(nouvelle), longueur)
                self.assertEqual(sorted(nouvelle), list(range(longueur)))

    def test_cle_aleatoire_est_une_permutation(self):
        for longueur in range(2, 12):
            cle = cle_aleatoire_positions(longueur)
            self.assertEqual(sorted(cle), list(range(longueur)))

    def test_deplacement_a_un_inverse(self):
        """Le déplacement (i, L, d) est annulé par (d, L, i)."""
        for n in range(2, 9):
            cle = tuple(range(n))
            for longueur_bloc in range(1, n):
                for i in range(n - longueur_bloc + 1):
                    for d in range(n - longueur_bloc + 1):
                        nouvelle = deplacer_bloc(cle, longueur_bloc, i, d)
                        retour = deplacer_bloc(nouvelle, longueur_bloc, d, i)
                        self.assertEqual(retour, cle)


class TestSubstitutionLettres(unittest.TestCase):
    def test_chiffrement_dechiffrement(self):
        cle_chiffrement = LETTRES[1:] + LETTRES[0]
        cle_dechiffrement = cle_inverse_lettres(cle_chiffrement)
        clair = "BONJOUR LE MONDE"
        chiffre = chiffrer_lettres(clair, cle_chiffrement)
        self.assertEqual(dechiffrer_lettres(chiffre, cle_dechiffrement), clair)

    def test_inverse_involutive(self):
        cle = LETTRES[5:] + LETTRES[:5]
        self.assertEqual(cle_inverse_lettres(cle_inverse_lettres(cle)), cle)

    def test_verification(self):
        self.assertTrue(verifier_cle_lettres(LETTRES[::-1]))
        self.assertFalse(verifier_cle_lettres("A" * 26))
        self.assertFalse(verifier_cle_lettres("ABC"))


class TestScore(unittest.TestCase):
    def test_log_egale_log_du_produit(self):
        reference = "BONJOUR LE MONDE"
        texte = "BONJOUR"
        r = construire_r(reference)
        log_r = construire_log_r(reference)
        self.assertAlmostEqual(
            score_log(texte, log_r),
            math.log(score_texte(texte, r)),
            places=9,
        )

    def test_lecture_chiffre_conserve_les_espaces(self):
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".txt", delete=False
        ) as fichier:
            fichier.write("A  B C\n")
            chemin = Path(fichier.name)
        try:
            self.assertEqual(lire_chiffre(chemin), "A  B C")
        finally:
            chemin.unlink()


class TestPermutationCombinee(unittest.TestCase):
    """Non-régression après le partage des helpers de permutation."""

    def test_aller_retour(self):
        message = "UN TEXTE ASSEZ LONG POUR TESTER LA PERMUTATION DES POSITIONS"
        cle = definir_cle_combinee("LEMON")
        crypto = chiffre_cryptogramme(message, cle)
        self.assertEqual(dechiffre_cryptogramme(crypto, cle), message)


class TestMoteurMCMC(unittest.TestCase):
    def test_enregistre_visites_et_candidats(self):
        """Avec deux états de même score, la chaîne alterne et tout est compté."""

        def dechiffrer_factice(texte, cle):
            return texte

        log_r = {("A", "B"): 1.0}
        etats, candidats = marche_mcmc(
            "ABAB",
            0,
            log_r,
            dechiffrer_factice,
            lambda cle: 1 - cle,
            n_iterations=100,
            chauffe=10,
        )

        self.assertEqual(set(etats), {0, 1})
        self.assertEqual(sum(info["visites"] for info in etats.values()), 90)
        self.assertIn(0, candidats)
        self.assertIn(1, candidats)


if __name__ == "__main__":
    unittest.main()
