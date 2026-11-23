"""Extra de Mathis : repérer les mots du texte déchiffré qui ne sont pas français.

N'intervient pas dans l'attaque (score, mutation, acceptation, sélection) :
sert uniquement à l'affichage des propositions, pour voir d'un coup d'œil si
une clé est bonne, et à quel endroit elle se trompe.

Le dictionnaire est ``mcmc/dictionnaire_fr.txt`` (un mot par ligne).  Chaque
mot passe par ``normaliser()`` pour être comparable au texte déchiffré.
"""

import os
import re
import sys
from pathlib import Path

from utils.score import normaliser

CHEMIN_DICTIONNAIRE = Path(__file__).resolve().parent.parent / "dictionnaire_fr.txt"

COULEUR_DEBUT = "\033[30;43m"  # texte noir sur fond jaune
COULEUR_FIN = "\033[0m"

_CACHE: dict = {}


def charger_dictionnaire(chemin=CHEMIN_DICTIONNAIRE):
    """Ensemble des mots normalisés du dictionnaire, ou None si le fichier manque.

    Le fichier n'est lu qu'une fois.
    """
    chemin = Path(chemin)
    if chemin not in _CACHE:
        try:
            mots = set()
            with open(chemin, encoding="utf-8") as fichier:
                for ligne in fichier:
                    mots.update(normaliser(ligne).split())
        except FileNotFoundError:
            mots = None
        _CACHE[chemin] = mots
    return _CACHE[chemin]


def analyser_mots(texte, dictionnaire):
    """Découpe le texte en mots et repère ceux absents du dictionnaire.

    Renvoie {reconnus, total, pourcentage, inconnus} où ``inconnus`` est la
    liste des positions (début, fin) des mots non reconnus dans ``texte``.
    """
    inconnus = []
    total = 0
    for mot in re.finditer(r"[^ ]+", texte):
        total += 1
        if mot.group() not in dictionnaire:
            inconnus.append((mot.start(), mot.end()))
    reconnus = total - len(inconnus)
    return {
        "reconnus": reconnus,
        "total": total,
        "pourcentage": round(100 * reconnus / total) if total else 0,
        "inconnus": inconnus,
    }


def resume_mots(analyse):
    """« mots reconnus : 64 % (7/11) »."""
    return (
        f"mots reconnus : {analyse['pourcentage']} % "
        f"({analyse['reconnus']}/{analyse['total']})"
    )


def couleur_disponible(flux=sys.stdout):
    """Vrai si le terminal accepte les codes ANSI (et que NO_COLOR n'est pas posé)."""
    return "NO_COLOR" not in os.environ and hasattr(flux, "isatty") and flux.isatty()


def surligner(texte, inconnus, longueur=None, couleur=True):
    """Surligne les mots inconnus dans ``texte[:longueur]``.

    En couleur (fond jaune) si ``couleur``, sinon entre crochets : ``[MOT]``.
    Un mot coupé par ``longueur`` est jugé sur le mot entier.
    """
    if longueur is None:
        longueur = len(texte)
    morceaux = []
    position = 0
    for debut, fin in inconnus:
        if debut >= longueur:
            break
        fin = min(fin, longueur)
        mot = texte[debut:fin]
        morceaux.append(texte[position:debut])
        morceaux.append(f"{COULEUR_DEBUT}{mot}{COULEUR_FIN}" if couleur else f"[{mot}]")
        position = fin
    morceaux.append(texte[position:longueur])
    return "".join(morceaux)
