"""Tests de l'extra de Mathis : surlignage des mots non français.

Lancement depuis la racine du dépôt :

    python3 mcmc/tests/test_dictionnaire.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "mcmc"))

from utils.dictionnaire import (
    COULEUR_DEBUT,
    COULEUR_FIN,
    analyser_mots,
    charger_dictionnaire,
    resume_mots,
    surligner,
)

DICO = {"LA", "SOUPE", "EST", "CHAUDE"}


class TestAnalyse(unittest.TestCase):
    def test_mots_reconnus_et_pourcentage(self):
        analyse = analyser_mots("LA SOUPE XQT CHAUDE", DICO)
        self.assertEqual((analyse["reconnus"], analyse["total"]), (3, 4))
        self.assertEqual(analyse["pourcentage"], 75)
        self.assertEqual(analyse["inconnus"], [(9, 12)])
        self.assertEqual(resume_mots(analyse), "mots reconnus : 75 % (3/4)")

    def test_espaces_multiples_et_texte_vide(self):
        self.assertEqual(analyser_mots("  LA  ZZ ", DICO)["inconnus"], [(6, 8)])
        self.assertEqual(analyser_mots("", DICO)["pourcentage"], 0)


class TestSurlignage(unittest.TestCase):
    def test_crochets_sans_couleur(self):
        texte = "LA SOUPE XQT CHAUDE"
        analyse = analyser_mots(texte, DICO)
        self.assertEqual(surligner(texte, analyse["inconnus"], couleur=False), "LA SOUPE [XQT] CHAUDE")

    def test_couleur_ansi(self):
        texte = "XQT EST"
        resultat = surligner(texte, analyser_mots(texte, DICO)["inconnus"])
        self.assertEqual(resultat, f"{COULEUR_DEBUT}XQT{COULEUR_FIN} EST")

    def test_extrait_coupe_un_mot(self):
        """Un mot coupé par la longueur est jugé sur le mot entier."""
        texte = "LA XQTW"
        inconnus = analyser_mots(texte, DICO)["inconnus"]
        self.assertEqual(surligner(texte, inconnus, 5, couleur=False), "LA [XQ]")
        self.assertEqual(surligner("LA SOUPEXX", [], 5, couleur=False), "LA SO")


class TestChargement(unittest.TestCase):
    def test_normalisation_et_fichier_absent(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write("été\naujourd'hui\n")
            chemin = Path(f.name)
        try:
            self.assertEqual(charger_dictionnaire(chemin), {"ETE", "AUJOURD", "HUI"})
        finally:
            chemin.unlink()
        self.assertIsNone(charger_dictionnaire(RACINE / "inexistant.txt"))


if __name__ == "__main__":
    unittest.main()
