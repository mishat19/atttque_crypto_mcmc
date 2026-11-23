"""Tests de la page web de démo (suivi de la chaîne, paramètres, calcul).

Lancement depuis la racine du dépôt :

    python3 mcmc/tests/test_web.py
"""

import sys
import threading
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "mcmc"))

from main import marche_mcmc
from web import (
    Annulation,
    ErreurParametre,
    Observateur,
    chiffrer_texte,
    lancer_travail,
    lire_parametres,
    preparer_positions,
)


def dechiffrer_factice(texte, cle):
    return texte


class TestObservateur(unittest.TestCase):
    def test_rappel_appele_le_bon_nombre_de_fois(self):
        appels = []
        observateur = Observateur(lambda cle: 1 - cle, 1000, lambda it, cle: appels.append(it))
        marche_mcmc("ABAB", 0, {("A", "B"): 1.0}, dechiffrer_factice, observateur, 6000)
        self.assertEqual(appels, [0, 1000, 2000, 3000, 4000, 5000])

    def test_rappel_recoit_la_cle_courante(self):
        """Toutes les propositions sont acceptées (même score) : la clé alterne."""
        cles = []
        observateur = Observateur(lambda cle: 1 - cle, 1, lambda it, cle: cles.append(cle))
        marche_mcmc("ABAB", 0, {("A", "B"): 1.0}, dechiffrer_factice, observateur, 4)
        self.assertEqual(cles, [0, 1, 0, 1])

    def test_annulation(self):
        annule = threading.Event()
        annule.set()
        observateur = Observateur(lambda cle: 1 - cle, 10, annule=annule)
        with self.assertRaises(Annulation):
            marche_mcmc("ABAB", 0, {("A", "B"): 1.0}, dechiffrer_factice, observateur, 100)


class TestParametres(unittest.TestCase):
    def test_texte_vide(self):
        with self.assertRaises(ErreurParametre):
            lire_parametres({"texte": "   ", "mode": "lettres"})

    def test_valeurs_par_defaut_et_normalisation(self):
        p = lire_parametres({"texte": "Été à Noël", "mode": "lettres"})
        self.assertEqual(p["chiffre"], "ETE A NOEL")
        self.assertEqual(p["iterations"], 20_000)
        self.assertEqual(p["propositions"], 5)

    def test_parametre_invalide(self):
        with self.assertRaises(ErreurParametre):
            lire_parametres({"texte": "ABC", "iterations": "beaucoup"})
        with self.assertRaises(ErreurParametre):
            lire_parametres({"texte": "ABC", "mode": "positions",
                             "longueur_min": 5, "longueur_max": 3})

    def test_positions_garde_les_espaces(self):
        self.assertEqual(preparer_positions("ab  é\n"), "AB  E")


class TestCalcul(unittest.TestCase):
    def test_attaque_lettres_complete(self):
        crypto = chiffrer_texte({"texte": "BONJOUR LE MONDE " * 20, "mode": "lettres"})
        p = lire_parametres({"texte": crypto["chiffre"], "mode": "lettres", "iterations": 300,
                             "intervalle_suivi": 100, "propositions": 3, "graine": 1})
        etat = lancer_travail(p, synchrone=True).etat()
        self.assertTrue(etat["termine"])
        self.assertIsNone(etat["erreur"])
        self.assertEqual(etat["nb_instantanes"], 3)
        self.assertEqual(len(etat["resultats"]["propositions"]), 3)

    def test_attaque_positions_par_longueur(self):
        crypto = chiffrer_texte({"texte": "BONJOUR LE MONDE " * 20, "mode": "positions",
                                 "longueur_cle": 3})
        p = lire_parametres({"texte": crypto["chiffre"], "mode": "positions", "iterations": 200,
                             "longueur_max": 4, "intervalle_suivi": 100, "graine": 2})
        etat = lancer_travail(p, synchrone=True).etat()
        longueurs = [e["longueur"] for e in etat["resultats"]["longueurs"]]
        self.assertEqual(longueurs, [2, 3, 4])
        self.assertEqual(etat["total"], 600)
        self.assertEqual(len(etat["resultats"]["resume"]), 3)


if __name__ == "__main__":
    unittest.main()
