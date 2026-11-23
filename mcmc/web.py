"""Page web de démo de l'attaque MCMC (substitution et permutation).

Lancement depuis la racine du dépôt :

    python3 mcmc/web.py                    # ouvre http://127.0.0.1:8766/
    python3 mcmc/web.py --sans-navigateur  # serveur seul

Bibliothèque standard uniquement : la page marche hors ligne.

Aucun fichier existant n'est modifié : le moteur ``marche_mcmc`` est réutilisé
tel quel.  Pour observer la chaîne pendant qu'elle tourne (« le texte qui se
répare »), on enveloppe la fonction de mutation : ``marche_mcmc`` l'appelle une
fois par itération avec la clé courante, ce qui suffit pour prendre des
instantanés et pour annuler le calcul.
"""

import argparse
import http.server
import json
import math
import random
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(DOSSIER))

from main import (
    CHEMIN_CHIFFRE_LETTRES,
    CHEMIN_CHIFFRE_POSITIONS,
    CHEMIN_REFERENCE,
    classer,
    fusionner_candidats,
    fusionner_etats,
    fusionner_vue,
    marche_mcmc,
)
from permutation.bloc import (
    chiffrer as chiffrer_positions,
    cle_inverse as cle_inverse_positions,
    dechiffrer as dechiffrer_positions,
    formater_cle as formater_positions,
)
from utils.dictionnaire import analyser_mots, charger_dictionnaire
from utils.initialisation import (
    cle_aleatoire,
    cle_aleatoire_positions,
    cle_heuristique,
)
from utils.mutation import muter_lettres, muter_positions
from utils.score import (
    ALPHABET,
    calculer_score_log,
    construire_log_r,
    lire_chiffre,
    lire_texte,
    normaliser,
)
from utils.substitution import (
    chiffrer as chiffrer_lettres,
    cle_inverse as cle_inverse_lettres,
    dechiffrer as dechiffrer_lettres,
)

HOTE = "127.0.0.1"
PORT = 8766
CHEMIN_PAGE = DOSSIER / "web" / "index.html"

LIMITE_CARACTERES = 50_000
LIMITE_CORPS = 2_000_000
LIMITE_INSTANTANES_PAR_MARCHE = 2_000
LONGUEUR_INSTANTANE = 80

DEFAUTS = {
    "mode": "lettres",
    "iterations": 20_000,
    "propositions": 5,
    "chauffe": 0.10,
    "graine": None,
    "initialisation": "heuristique",
    "classement": "score",
    "longueur_min": 2,
    "longueur_max": 8,
    "redemarrages": 1,
    "intervalle_suivi": 1_000,
}


class ErreurParametre(ValueError):
    """Paramètre invalide : le message est affiché tel quel dans la page."""


class Annulation(Exception):
    """Levée dans la mutation pour sortir de ``marche_mcmc``."""


# =============== STATISTIQUES DE RÉFÉRENCE ===============

_REFERENCE: dict = {}
_VERROU_REFERENCE = threading.Lock()


def reference():
    """Texte de référence et log r(x, y), calculés une seule fois."""
    with _VERROU_REFERENCE:
        if not _REFERENCE:
            texte = lire_texte(CHEMIN_REFERENCE)
            _REFERENCE["texte"] = texte
            _REFERENCE["log_r"] = construire_log_r(texte)
    return _REFERENCE


def frequences_reference():
    """Fréquence (en %) de chaque lettre et de l'espace dans le texte de référence."""
    texte = reference()["texte"]
    lettres = sum(1 for c in texte if c != " ")
    return {
        "lettres": {c: round(100 * texte.count(c) / lettres, 3) for c in ALPHABET if c != " "},
        "espace": round(100 * texte.count(" ") / len(texte), 2),
    }


# =============== LECTURE DES PARAMÈTRES ===============

def _entier(donnees, nom, mini, maxi):
    valeur = donnees.get(nom)
    if valeur is None or valeur == "":
        valeur = DEFAUTS[nom]
    if isinstance(valeur, bool):
        raise ErreurParametre(f"« {nom} » doit être un entier.")
    try:
        valeur = int(valeur)
    except (TypeError, ValueError):
        raise ErreurParametre(f"« {nom} » doit être un entier.") from None
    if not mini <= valeur <= maxi:
        raise ErreurParametre(f"« {nom} » doit être compris entre {mini} et {maxi}.")
    return valeur


def _choix(donnees, nom, valeurs):
    valeur = donnees.get(nom) or DEFAUTS[nom]
    if valeur not in valeurs:
        raise ErreurParametre(f"« {nom} » doit valoir {' ou '.join(valeurs)}.")
    return valeur


def preparer_positions(texte):
    """Prépare un cryptogramme de permutation sans décaler les positions.

    Comme ``lire_chiffre`` : on retire les retours à la ligne mais on garde
    chaque espace.  Chaque caractère reste un caractère (majuscule sans accent,
    ou espace s'il n'est pas dans l'alphabet).
    """
    sortie = []
    for caractere in texte.replace("\r", "").replace("\n", ""):
        normalise = normaliser(caractere)
        sortie.append(normalise if len(normalise) == 1 else " ")
    return "".join(sortie)


def preparer_chiffre(texte, mode):
    if not isinstance(texte, str) or not texte.strip():
        raise ErreurParametre("Le texte chiffré est vide.")
    if len(texte) > LIMITE_CARACTERES:
        raise ErreurParametre(
            f"Texte trop long ({len(texte)} caractères, maximum {LIMITE_CARACTERES})."
        )
    chiffre = normaliser(texte) if mode == "lettres" else preparer_positions(texte)
    if not chiffre.strip():
        raise ErreurParametre("Le texte ne contient aucune lettre exploitable.")
    return chiffre


def lire_parametres(donnees):
    """Valide la requête de ``/api/attaque`` et renvoie les paramètres complets."""
    if not isinstance(donnees, dict):
        raise ErreurParametre("Requête invalide.")

    mode = _choix(donnees, "mode", ("lettres", "positions"))
    p = {
        "mode": mode,
        "chiffre": preparer_chiffre(donnees.get("texte"), mode),
        "iterations": _entier(donnees, "iterations", 1, 500_000),
        "propositions": _entier(donnees, "propositions", 1, 50),
        "initialisation": _choix(donnees, "initialisation", ("heuristique", "aleatoire")),
        "classement": _choix(donnees, "classement", ("score", "visites")),
        "longueur_min": _entier(donnees, "longueur_min", 2, 12),
        "longueur_max": _entier(donnees, "longueur_max", 2, 12),
        "redemarrages": _entier(donnees, "redemarrages", 1, 20),
        "intervalle_suivi": _entier(donnees, "intervalle_suivi", 1, 500_000),
    }

    chauffe = donnees.get("chauffe")
    if chauffe is None or chauffe == "":
        chauffe = DEFAUTS["chauffe"]
    try:
        chauffe = float(chauffe)
    except (TypeError, ValueError):
        raise ErreurParametre("« chauffe » doit être un nombre.") from None
    if not 0 <= chauffe < 1:
        raise ErreurParametre("« chauffe » doit être dans [0 ; 1[.")
    p["chauffe"] = chauffe

    graine = donnees.get("graine")
    if graine is None or graine == "":
        p["graine"] = None
    else:
        p["graine"] = _entier({"graine": graine}, "graine", -(2**63), 2**63 - 1)

    if mode == "positions" and p["longueur_max"] < p["longueur_min"]:
        raise ErreurParametre("ℓ max doit être supérieur ou égal à ℓ min.")

    # Pas plus de LIMITE_INSTANTANES_PAR_MARCHE instantanés par marche.
    minimum = math.ceil(p["iterations"] / LIMITE_INSTANTANES_PAR_MARCHE)
    p["intervalle_suivi"] = max(p["intervalle_suivi"], minimum)
    return p


# =============== SUIVI DE LA CHAÎNE ===============

class Observateur:
    """Enveloppe une fonction de mutation pour suivre ``marche_mcmc``.

    À l'itération ``n``, ``marche_mcmc`` appelle ``muter(cle_courante)`` : on
    appelle donc ``rappel(n, cle_courante)`` toutes les ``intervalle``
    itérations, puis on délègue à la vraie mutation.  Si ``annule`` est levé,
    on interrompt la marche avec ``Annulation``.
    """

    def __init__(self, muter, intervalle, rappel=None, annule=None):
        if intervalle < 1:
            raise ValueError("L'intervalle de suivi doit être au moins 1.")
        self.muter = muter
        self.intervalle = intervalle
        self.rappel = rappel
        self.annule = annule
        self.iteration = 0

    def __call__(self, cle):
        if self.annule is not None and self.annule.is_set():
            raise Annulation()
        if self.rappel is not None and self.iteration % self.intervalle == 0:
            self.rappel(self.iteration, cle)
        self.iteration += 1
        return self.muter(cle)


# =============== CALCUL EN TÂCHE DE FOND ===============

class Travail:
    """Une attaque lancée depuis la page, et tout ce qu'elle a produit."""

    def __init__(self, parametres):
        self.id = uuid.uuid4().hex
        self.parametres = parametres
        self.verrou = threading.Lock()
        self.annule = threading.Event()
        self.thread = None
        self.termine = False
        self.annulee = False
        self.erreur = None
        self.resultats = None
        self.iteration = 0
        self.longueur_en_cours = None
        self.instantanes = []
        self.debut = time.monotonic()
        self.duree = None

        p = parametres
        if p["mode"] == "positions":
            nb_longueurs = p["longueur_max"] - p["longueur_min"] + 1
            self.total = p["iterations"] * p["redemarrages"] * nb_longueurs
        else:
            self.total = p["iterations"]

    def observateur(self, muter, dechiffrer, log_r, base, longueur, marche):
        """Observateur d'une marche qui commence à l'itération globale ``base``."""
        chiffre = self.parametres["chiffre"]
        formater = formater_positions if longueur else str

        def rappel(iteration, cle):
            score = calculer_score_log(chiffre, cle, log_r, dechiffrer)
            instantane = {
                "iteration": base + iteration,
                "iteration_marche": iteration,
                "longueur": longueur,
                "marche": marche,
                "score": round(score, 1),
                "cle": formater(cle),
                "texte": dechiffrer(chiffre, cle)[:LONGUEUR_INSTANTANE],
            }
            with self.verrou:
                self.iteration = base + iteration
                self.instantanes.append(instantane)

        return Observateur(muter, self.parametres["intervalle_suivi"], rappel, self.annule)

    def etat(self, depuis=0):
        with self.verrou:
            depuis = max(0, min(depuis, len(self.instantanes)))
            reponse = {
                "id": self.id,
                "mode": self.parametres["mode"],
                "termine": self.termine,
                "annule": self.annulee,
                "erreur": self.erreur,
                "iteration": self.total if self.termine and not self.annulee else self.iteration,
                "total": self.total,
                "longueur_en_cours": self.longueur_en_cours,
                "longueur_min": self.parametres["longueur_min"],
                "longueur_max": self.parametres["longueur_max"],
                "intervalle_suivi": self.parametres["intervalle_suivi"],
                "nb_caracteres": len(self.parametres["chiffre"]),
                "nb_instantanes": len(self.instantanes),
                "instantanes": self.instantanes[depuis:],
                "duree": round(
                    self.duree if self.duree is not None else time.monotonic() - self.debut,
                    1,
                ),
            }
            if self.termine:
                reponse["resultats"] = self.resultats
            return reponse


def decrire_propositions(propositions, chiffre, dechiffrer, inverse, formater):
    """Même contenu que ``afficher_propositions`` de la CLI, en JSON.

    ``mots`` : extra de Mathis (mots reconnus, positions des mots inconnus),
    ou None si le dictionnaire est absent.
    """
    dictionnaire = charger_dictionnaire()
    resultat = []
    for rang, (cle, info) in enumerate(propositions, start=1):
        texte = dechiffrer(chiffre, cle)
        resultat.append({
            "rang": rang,
            "score": round(info["score"], 1),
            "visites": info["visites"],
            "propositions": info.get("propositions", 0),
            "cle": formater(cle),
            "cle_inverse": formater(inverse(cle)),
            "texte": texte,
            "mots": analyser_mots(texte, dictionnaire) if dictionnaire is not None else None,
        })
    return resultat


def attaque_lettres(travail, log_r):
    p = travail.parametres
    chiffre = p["chiffre"]
    if p["initialisation"] == "aleatoire":
        cle_initiale = cle_aleatoire()
    else:
        cle_initiale = cle_heuristique(chiffre, reference()["texte"])

    chauffe = int(p["iterations"] * p["chauffe"])
    score_initial = calculer_score_log(chiffre, cle_initiale, log_r, dechiffrer_lettres)
    observateur = travail.observateur(muter_lettres, dechiffrer_lettres, log_r, 0, None, 0)

    etats, candidats = marche_mcmc(
        chiffre, cle_initiale, log_r, dechiffrer_lettres, observateur,
        p["iterations"], chauffe,
    )
    vue = fusionner_vue(etats, candidats)
    propositions = classer(vue, p["propositions"], p["classement"])
    return {
        "mode": "lettres",
        "chauffe": chauffe,
        "cle_initiale": cle_initiale,
        "score_initial": round(score_initial, 1),
        "propositions": decrire_propositions(
            propositions, chiffre, dechiffrer_lettres, cle_inverse_lettres, str
        ),
    }


def attaque_positions(travail, log_r):
    """Une marche (ou plusieurs redémarrages) par longueur ℓ, comme la CLI.

    En cas d'annulation, on garde les longueurs déjà terminées.
    """
    p = travail.parametres
    chiffre = p["chiffre"]
    chauffe = int(p["iterations"] * p["chauffe"])
    longueurs = []
    base = 0
    marche = 0

    try:
        for longueur in range(p["longueur_min"], p["longueur_max"] + 1):
            with travail.verrou:
                travail.longueur_en_cours = longueur
            etats: dict = {}
            candidats: dict = {}
            for _ in range(p["redemarrages"]):
                observateur = travail.observateur(
                    muter_positions, dechiffrer_positions, log_r, base, longueur, marche
                )
                etats_marche, candidats_marche = marche_mcmc(
                    chiffre, cle_aleatoire_positions(longueur), log_r,
                    dechiffrer_positions, observateur, p["iterations"], chauffe,
                )
                fusionner_etats(etats, etats_marche)
                fusionner_candidats(candidats, candidats_marche)
                base += p["iterations"]
                marche += 1

            vue = fusionner_vue(etats, candidats)
            propositions = classer(vue, p["propositions"], p["classement"])
            meilleur = propositions[0][1]["score"]
            longueurs.append({
                "longueur": longueur,
                "meilleur": round(meilleur, 1),
                "penalise": round(meilleur - math.lgamma(longueur + 1), 1),
                "propositions": decrire_propositions(
                    propositions, chiffre, dechiffrer_positions,
                    cle_inverse_positions, formater_positions,
                ),
            })
    except Annulation:
        travail.annulee = True

    return {
        "mode": "positions",
        "chauffe": chauffe,
        "longueurs": longueurs,
        "resume": [
            {
                "longueur": entree["longueur"],
                "score": entree["meilleur"],
                "penalise": entree["penalise"],
                "cle": entree["propositions"][0]["cle"],
                "mots": entree["propositions"][0]["mots"],
            }
            for entree in longueurs
        ],
    }


def executer(travail):
    """Corps du thread de calcul."""
    p = travail.parametres
    resultats = None
    erreur = None
    try:
        if p["graine"] is not None:
            random.seed(p["graine"])
        log_r = reference()["log_r"]
        if p["mode"] == "positions":
            resultats = attaque_positions(travail, log_r)
        else:
            resultats = attaque_lettres(travail, log_r)
    except Annulation:
        travail.annulee = True
    except Exception as exc:  # noqa: BLE001 - l'erreur est affichée dans la page
        erreur = f"Erreur pendant l'attaque : {exc}"

    with travail.verrou:
        travail.resultats = resultats
        travail.erreur = erreur
        travail.duree = time.monotonic() - travail.debut
        travail.termine = True


TRAVAUX: dict = {}
_VERROU_TRAVAUX = threading.Lock()


def lancer_travail(parametres, synchrone=False):
    """Lance une attaque ; la précédente est annulée (le hasard est partagé)."""
    with _VERROU_TRAVAUX:
        for ancien in TRAVAUX.values():
            if not ancien.termine:
                ancien.annule.set()
                if ancien.thread is not None:
                    ancien.thread.join(timeout=5)
        travail = Travail(parametres)
        TRAVAUX.clear()  # on ne garde que le dernier calcul
        TRAVAUX[travail.id] = travail

    if synchrone:
        executer(travail)
    else:
        travail.thread = threading.Thread(target=executer, args=(travail,), daemon=True)
        travail.thread.start()
    return travail


def trouver_travail(identifiant):
    with _VERROU_TRAVAUX:
        travail = TRAVAUX.get(identifiant)
    if travail is None:
        raise ErreurParametre("Calcul inconnu (le serveur a peut-être redémarré).")
    return travail


# =============== CHIFFREMENT D'UN TEXTE CLAIR ===============

def chiffrer_texte(donnees):
    """Même logique que ``mcmc/chiffrer.py``, sans écrire de fichier."""
    if not isinstance(donnees, dict):
        raise ErreurParametre("Requête invalide.")
    mode = _choix(donnees, "mode", ("lettres", "positions"))
    texte = donnees.get("texte")
    if not isinstance(texte, str) or not texte.strip():
        raise ErreurParametre("Le texte clair est vide.")
    if len(texte) > LIMITE_CARACTERES:
        raise ErreurParametre(f"Texte trop long (maximum {LIMITE_CARACTERES} caractères).")
    clair = normaliser(texte)
    if not clair:
        raise ErreurParametre("Le texte clair ne contient aucune lettre.")

    if mode == "positions":
        longueur_cle = _entier(
            {"longueur_cle": donnees.get("longueur_cle") or 4}, "longueur_cle", 2, 12
        )
        if len(clair) < longueur_cle:
            raise ErreurParametre("Le texte est plus court que la clé.")
        cle = cle_aleatoire_positions(longueur_cle)
        return {
            "mode": mode,
            "chiffre": chiffrer_positions(clair, cle),
            "cle_chiffrement": formater_positions(cle),
            "cle_dechiffrement": formater_positions(cle_inverse_positions(cle)),
            "longueur": len(clair),
        }

    cle = cle_aleatoire()
    return {
        "mode": mode,
        "chiffre": chiffrer_lettres(clair, cle),
        "cle_chiffrement": cle,
        "cle_dechiffrement": cle_inverse_lettres(cle),
        "longueur": len(clair),
    }


# =============== SERVEUR HTTP ===============

class Gestionnaire(http.server.BaseHTTPRequestHandler):
    """Sert la page et les points d'entrée JSON."""

    def do_GET(self):
        url = urlparse(self.path)
        requete = parse_qs(url.query)

        if url.path in ("/", "/index.html"):
            try:
                corps = CHEMIN_PAGE.read_bytes()
            except FileNotFoundError:
                self._repondre(500, "text/plain; charset=utf-8", b"Page introuvable.")
                return
            self._repondre(200, "text/html; charset=utf-8", corps)
            return

        if url.path == "/api/etat":
            identifiant = requete.get("id", [""])[0]
            try:
                depuis = int(requete.get("depuis", ["0"])[0])
            except ValueError:
                depuis = 0
            self._traiter(lambda: trouver_travail(identifiant).etat(depuis))
            return

        if url.path == "/api/frequences":
            self._traiter(frequences_reference)
            return

        if url.path == "/api/exemple":
            mode = requete.get("mode", ["lettres"])[0]

            def exemple():
                chemin = CHEMIN_CHIFFRE_POSITIONS if mode == "positions" else CHEMIN_CHIFFRE_LETTRES
                try:
                    return {"mode": mode, "fichier": chemin.name, "texte": lire_chiffre(chemin)}
                except FileNotFoundError:
                    raise ErreurParametre(
                        f"{chemin.name} introuvable : générez-le avec mcmc/chiffrer.py."
                    ) from None

            self._traiter(exemple)
            return

        self._json(404, {"erreur": "Page inconnue."})

    def do_POST(self):
        url = urlparse(self.path)
        routes = {
            "/api/attaque": lambda d: {"id": lancer_travail(lire_parametres(d)).id},
            "/api/annuler": self._annuler,
            "/api/chiffrer": chiffrer_texte,
        }
        route = routes.get(url.path)
        if route is None:
            self._json(404, {"erreur": "Page inconnue."})
            return

        try:
            taille = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            taille = -1
        if not 0 <= taille <= LIMITE_CORPS:
            self._json(400, {"erreur": "Requête trop grosse ou mal formée."})
            return
        try:
            donnees = json.loads(self.rfile.read(taille).decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"erreur": "Le corps de la requête n'est pas du JSON valide."})
            return

        self._traiter(lambda: route(donnees))

    @staticmethod
    def _annuler(donnees):
        travail = trouver_travail((donnees or {}).get("id", ""))
        travail.annule.set()
        return {"id": travail.id, "annule": True}

    def _traiter(self, fonction):
        try:
            self._json(200, fonction())
        except ErreurParametre as exc:
            self._json(400, {"erreur": str(exc)})
        except Exception as exc:  # noqa: BLE001 - le serveur ne doit jamais tomber
            self._json(500, {"erreur": f"Erreur interne : {exc}"})

    def _json(self, code, charge):
        corps = json.dumps(charge, ensure_ascii=False).encode("utf-8")
        self._repondre(code, "application/json; charset=utf-8", corps)

    def _repondre(self, code, type_mime, corps):
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *args):  # noqa: A003 - pas de journal d'accès
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(description="Page web de démo de l'attaque MCMC.")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--sans-navigateur", action="store_true")
    args = parser.parse_args(argv)

    print("Chargement du texte de référence et du dictionnaire…")
    reference()
    if charger_dictionnaire() is None:
        print("(mcmc/dictionnaire_fr.txt absent : pas de surlignage des mots)")
    serveur = http.server.ThreadingHTTPServer((HOTE, args.port), Gestionnaire)
    adresse = f"http://{HOTE}:{args.port}/"
    print(f"Démo MCMC disponible sur {adresse}  (Ctrl+C pour arrêter)")
    if not args.sans_navigateur:
        threading.Timer(0.6, webbrowser.open, args=(adresse,)).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
    finally:
        serveur.server_close()


if __name__ == "__main__":
    main()
