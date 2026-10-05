"""Analyse de digrammes et chaine de Markov d'un texte Wikipedia, avec interface web locale.

Meme logique de calcul que stats.py. L'interface est servie par http.server (stdlib)
et s'ouvre dans le navigateur : aucune dependance externe (stdlib uniquement).

Lancement :  python utils/app.py
"""

from __future__ import annotations

import http.server
import json
import random
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.attaque_frequentielle import attaque_frequentielle_colonnes
from chiffrements.chiffrement_cesar import ALPHABET, chiffre_cesar, dechiffre_cesar
from chiffrements.chiffrement_vigenere import chiffre_vigenere, dechiffre_vigenere
from permutation.cryptogramme import (
    chiffre_cryptogramme as chiffre_permutation,
    dechiffre_cryptogramme as dechiffre_permutation,
    definir_cle as cle_permutation,
)
from substitution.cryptogramme import scores_attaque_frequentielle

WIKI_UA = "MonScript/1.0 (simon@example.com)"
SATES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
         "V", "W", "X", "Y", "Z", " "]

PORT = 8765

def wiki_text(titre, lang="fr", intro_seule=False):
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "redirects": 1,
        "format": "json",
        "titles": titre,
    }
    if intro_seule:
        params["exintro"] = 1

    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    requete = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    with urllib.request.urlopen(requete, timeout=10) as reponse:
        payload = json.loads(reponse.read().decode("utf-8"))

    page = next(iter(payload["query"]["pages"].values()))

    # convert page content to a 27 character string, replacing newlines with spaces and letters in uppercase only
    content = page.get("extract", "").replace("\n", " ").upper()
    content = ''.join(c for c in content if c in SATES)

    if len(content) % 2 == 1:
        content += " "

    return content


def statistics(content):
    stats = {
        "global_count": len(content),
        "character_count": {char: content.count(char) for char in SATES},
    }
    return stats


def digram_stats(content, largeur=2):
    content_length = len(content)
    diagram_stats = {}

    for index in range(0, content_length, largeur):
        segment = content[index:index + largeur]
        diagram_stats[segment] = diagram_stats[segment] + 1 if segment in diagram_stats else 1

    return diagram_stats


def markov_matrix(digram_stats):
    matrix = []

    for x in range(len(SATES)):
        matrix.append([])
        for y in range(len(SATES)):
            matrix[x].append(0)

    for segment in digram_stats:
        x = SATES.index(segment[0])
        y = SATES.index(segment[1])
        matrix[x][y] += digram_stats[segment]

    for x in range(len(SATES)):
        ligne_total = sum(matrix[x])
        for y in range(len(SATES)):
            matrix[x][y] = matrix[x][y] / ligne_total if ligne_total > 0 else matrix[x][y] / 1

    return matrix


def text_generator(matrix, longueur=1000):
    text = " "
    current_char = " "
    for _ in range(longueur):
        x = SATES.index(current_char)
        next_char = random.choices(SATES, weights=matrix[x])[0]
        text += next_char
        current_char = next_char

    return text

# Les textes générées n'ont pas de sens particulier puisque toutes les lettres sont mélangées. Les mots ne sont plus de la même taille mais
# le texte reste cohérent en terme de structure à un texte normal.

# =============== SERVEUR ==============

ETAT: dict = {"matrix": None, "content": None, "crypto": {}}


def analyser(titre: str, lang: str, intro_seule: bool) -> dict:
    """Telecharge l'article et renvoie ce dont la page a besoin."""
    content = wiki_text(titre, lang, intro_seule)
    if not content:
        return {"erreur": "Aucun texte exploitable dans cet article."}

    digrammes = digram_stats(content)
    matrix = markov_matrix(digrammes)
    ETAT["matrix"] = matrix
    ETAT["content"] = content
    ETAT["crypto"] = {}

    return {
        "titre": titre,
        "content": content,
        "stats": statistics(content),
        "digrammes": digrammes,
        "matrix": matrix,
        "etats": SATES,
        "genere": generer(2000).get("texte", ""),
    }


def generer(longueur: int) -> dict:
    """Tire un texte selon la derniere matrice calculee."""
    matrix = ETAT["matrix"]
    if matrix is None:
        return {"erreur": "Analysez d'abord un article."}
    try:
        return {"texte": text_generator(matrix, longueur)}
    except ValueError:
        return {"erreur": "La chaine a atteint un etat sans transition sortante."}


def _cle(mot_cle: str) -> str:
    """Cle de chiffrement : un mot de lettres, espaces retires."""
    mot = "".join(mot_cle.upper().split())
    if not mot or not all(c in ALPHABET for c in mot):
        raise ValueError("La cle doit etre un mot non vide de lettres.")
    return mot


def _source() -> str:
    """Texte de l'article analyse, source de tous les cryptogrammes."""
    if not ETAT["content"]:
        raise ValueError("Analysez d'abord un article.")
    return ETAT["content"]


def _cryptogramme(cible: str) -> str:
    """Dernier cryptogramme produit pour une cible (cesar, vigenere...)."""
    crypto = ETAT["crypto"].get(cible)
    if not crypto:
        raise ValueError("Generez d'abord un cryptogramme.")
    return crypto


def cryptogrammer(decalage: int, mode: str = "chiffre") -> dict:
    """Chiffre ou dechiffre le dernier texte avec le chiffrement de Cesar."""
    cle = decalage % 26

    if mode == "dechiffre":
        return {"texte": dechiffre_cesar(_cryptogramme("cesar"), cle), "decalage": cle}

    crypto = chiffre_cesar(_source(), cle)
    ETAT["crypto"]["cesar"] = crypto
    return {"cryptogramme": crypto, "decalage": cle}


def crypter_vigenere(mot_cle: str, mode: str = "chiffre") -> dict:
    """Chiffre ou dechiffre le dernier texte avec une cle de Vigenere connue."""
    cle = _cle(mot_cle)

    if mode == "dechiffre":
        return {"texte": dechiffre_vigenere(_cryptogramme("vigenere"), cle), "cle": cle}

    crypto = chiffre_vigenere(_source(), cle)
    ETAT["crypto"]["vigenere"] = crypto
    return {"cryptogramme": crypto, "cle": cle}


def crypter_permutation(mot_cle: str, mode: str = "chiffre") -> dict:
    """Chiffre ou dechiffre avec la permutation de position pilotee par la cle."""
    cle = cle_permutation(_cle(mot_cle))

    if mode == "dechiffre":
        return {"texte": dechiffre_permutation(_cryptogramme("permutation"), cle), "cle": cle["mot"]}

    crypto = chiffre_permutation(_source(), cle)
    ETAT["crypto"]["permutation"] = crypto
    return {"cryptogramme": crypto, "cle": cle["mot"], "permutation": cle["permutation"]}


def attaquer() -> dict:
    """Attaque frequentielle du dernier cryptogramme genere."""
    crypto = _cryptogramme("cesar")
    scores = scores_attaque_frequentielle(crypto)
    meilleur = max(scores, key=scores.get)
    classement = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "mode": "decalage",
        "cible": "cesar",
        "decalage": meilleur,
        "scores": [{"decalage": d, "score": round(s, 4)} for d, s in classement],
        "texte": dechiffre_cesar(crypto, meilleur),
    }


def _attaquer_colonnes(cible: str, flux: str, periode: int) -> dict:
    """Attaque frequentielle par colonnes d'un chiffre de periode donnee.

    `flux` dit sur quoi la cle se repete : sur les lettres pour le Vigenere
    habituel, sur les positions brutes pour la permutation, qui les reordonne.
    """
    resultat = attaque_frequentielle_colonnes(_cryptogramme(cible), periode, flux)
    resultat["mode"] = "colonnes"
    resultat["cible"] = cible
    return resultat


def attaquer_vigenere(periode: int) -> dict:
    """Attaque par colonnes du cryptogramme Vigenere."""
    return _attaquer_colonnes("vigenere", "lettres", periode)


def attaquer_permutation(periode: int) -> dict:
    """Attaque par colonnes du cryptogramme a permutation de position."""
    return _attaquer_colonnes("permutation", "positions", periode)


class Handler(http.server.BaseHTTPRequestHandler):
    """Sert la page et les points d'entree JSON (analyse, generation, cifras, attaques)."""

    def do_GET(self) -> None:  # noqa: N802 - nom impose par BaseHTTPRequestHandler
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            self._repondre(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
            return

        if parsed.path == "/api/analyse":
            titre = query.get("titre", [""])[0].strip()
            lang = query.get("lang", ["fr"])[0]
            intro = query.get("intro", ["0"])[0] == "1"
            self._json(self._sur(analyser, titre, lang, intro))
            return

        if parsed.path == "/api/generer":
            longueur = int(query.get("longueur", ["2000"])[0])
            self._json(self._sur(generer, max(100, min(longueur, 20000))))
            return

        if parsed.path == "/api/cesar":
            decalage = int(query.get("decalage", ["3"])[0])
            mode = query.get("mode", ["chiffre"])[0]
            self._json(self._sur(cryptogrammer, decalage, mode))
            return

        if parsed.path == "/api/vigenere":
            cle = query.get("cle", [""])[0]
            mode = query.get("mode", ["chiffre"])[0]
            self._json(self._sur(crypter_vigenere, cle, mode))
            return

        if parsed.path == "/api/permutation":
            cle = query.get("cle", [""])[0]
            mode = query.get("mode", ["chiffre"])[0]
            self._json(self._sur(crypter_permutation, cle, mode))
            return

        if parsed.path == "/api/attaque":
            self._json(self._sur(attaquer))
            return

        if parsed.path == "/api/attaque-vigenere":
            periode = int(query.get("periode", ["4"])[0])
            self._json(self._sur(attaquer_vigenere, periode))
            return

        if parsed.path == "/api/attaque-permutation":
            periode = int(query.get("periode", ["5"])[0])
            self._json(self._sur(attaquer_permutation, periode))
            return

        self._repondre(404, "text/plain; charset=utf-8", b"Page inconnue")

    @staticmethod
    def _sur(fonction, *args) -> dict:
        """Convertit toute exception en message affichable par la page."""
        try:
            return fonction(*args)
        except urllib.error.HTTPError:
            return {"erreur": "Wikipedia a refuse la requete. Verifiez le titre et la langue."}
        except urllib.error.URLError as erreur:
            return {"erreur": f"Connexion impossible a Wikipedia : {erreur}"}
        except TimeoutError:
            return {"erreur": "Wikipedia a mis trop de temps a repondre."}
        except ValueError as erreur:
            return {"erreur": str(erreur)}
        except Exception as erreur:  # noqa: BLE001 - le serveur ne doit jamais tomber
            return {"erreur": str(erreur)}

    def _json(self, charge: dict) -> None:
        self._repondre(200, "application/json; charset=utf-8", json.dumps(charge).encode("utf-8"))

    def _repondre(self, code: int, type_mime: str, corps: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *args) -> None:  # noqa: A003 - on tait les logs d'acces
        pass


PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Matrice de transition</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ground:#FBFAF7; --ink:#23211E; --mute:#7A756C; --rule:#E3DED3;
  --accent:#2F6F4F; --alert:#A8492C; --panel:#F3F0E9;
  --sans:"Instrument Sans",-apple-system,Segoe UI,sans-serif;
  --mono:"IBM Plex Mono",Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px 80px}

/* ---- barre de controle ---- */
.bar{position:sticky;top:0;z-index:5;background:var(--ground);
  border-bottom:1px solid var(--rule);padding:18px 0;margin-bottom:34px;
  display:flex;gap:14px;align-items:flex-end;flex-wrap:wrap}
.champ{display:flex;flex-direction:column;gap:5px}
.champ label{font-size:12.5px;color:var(--mute)}
input[type=text],select{font:inherit;font-size:14px;padding:7px 10px;color:var(--ink);
  background:#fff;border:1px solid var(--rule);border-radius:3px;min-width:150px}
input[type=text]:focus-visible,select:focus-visible,button:focus-visible,
.bascule:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.case{display:flex;align-items:center;gap:7px;padding-bottom:8px;font-size:14px}
button{font:inherit;font-weight:500;font-size:14px;padding:8px 18px;cursor:pointer;
  background:var(--accent);color:#fff;border:none;border-radius:3px}
button:hover{background:#255C41}
button:disabled{background:var(--mute);cursor:default}
button.discret{background:transparent;color:var(--accent);border:1px solid var(--rule);padding:6px 13px}
button.discret:hover{background:var(--panel)}
button.discret[hidden]{display:none}
button.plus{margin-top:14px}
.etat{margin-left:auto;font-size:13.5px;color:var(--mute);padding-bottom:9px}
.etat.rouge{color:var(--alert)}

/* ---- une carte par cifra ---- */
.cifras{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:38px}
.cifra{border:1px solid var(--rule);border-radius:5px;padding:15px 17px 17px;background:var(--panel)}
.cifra h3{font-size:13px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  margin:0;color:var(--ink);display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
.cifra h3 .algo{font-weight:400;letter-spacing:0;text-transform:none;
  font-size:12px;color:var(--mute);font-style:italic}
.cifra .aide{font-size:12px;color:var(--mute);margin:7px 0 13px}
.cifra .ligne{display:flex;gap:9px;align-items:flex-end;flex-wrap:wrap}
.cifra .ligne+.ligne{margin-top:11px}
.cifra .ligne button{flex:1 1 auto;min-width:0;padding:8px 6px;font-size:13px;white-space:nowrap}
.cifra input[type=text]{width:120px;min-width:0}

/* ---- vide ---- */
.vide{padding:120px 0;max-width:38ch;color:var(--mute);font-size:17px}

/* ---- matrice ---- */
h2{font-size:16px;font-weight:600;margin:0 0 3px}
.legende{font-size:13px;color:var(--mute);margin:0 0 16px}
.hero{display:grid;grid-template-columns:minmax(0,1fr) 218px;gap:32px;align-items:start}
.grille{overflow-x:auto;padding-bottom:6px}
.ligne{display:flex}
.cel{width:30px;height:24px;flex:none;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-size:10.5px;letter-spacing:-.02em}
.tete{color:var(--mute);font-size:11px;font-weight:500}
.cel.src{color:var(--mute);font-size:11px;font-weight:500;justify-content:flex-end;padding-right:7px;width:32px}
.cel.val{cursor:crosshair}
.cel.nul{color:#CFC9BC}
.cel.somme{font-size:10px;color:var(--mute);width:44px;justify-content:flex-end;padding-right:2px}
.cel.somme.zero{color:var(--alert)}
.ligne.actif .cel.src,.cel.colactif.tete{color:var(--ink)}
.cel.vise{box-shadow:inset 0 0 0 1.5px var(--ink)}

/* ---- lecture ---- */
.lecture{position:sticky;top:96px;background:var(--panel);border-radius:4px;padding:20px}
.proba{font-family:var(--mono);font-size:27px;line-height:1.15;margin:0 0 2px}
.proba .petit{font-size:15px;color:var(--mute)}
.lecture p{margin:0;font-size:13.5px;color:var(--mute)}
.lecture dl{margin:18px 0 0;font-size:13px;display:grid;grid-template-columns:1fr auto;gap:7px 12px}
.lecture dt{color:var(--mute)}
.lecture dd{margin:0;font-family:var(--mono);text-align:right}
.echelle{display:flex;height:7px;margin:20px 0 6px;border-radius:2px;overflow:hidden}
.echelle span{flex:1}
.bornes{display:flex;justify-content:space-between;font-size:11.5px;color:var(--mute);
  font-family:var(--mono)}

/* ---- graphiques ---- */
.duo{display:grid;grid-template-columns:1fr 1fr;gap:44px;margin-top:56px}
.rang{display:grid;grid-template-columns:44px 1fr 52px 56px;align-items:center;
  gap:10px;font-size:12.5px;padding:2px 0}
.rang .cle{font-family:var(--mono);color:var(--ink)}
.rang .n,.rang .pc{font-family:var(--mono);text-align:right;font-size:11.5px;color:var(--mute)}
.rang.att{grid-template-columns:44px 1fr 64px;cursor:pointer}
.rang.att:hover{background:var(--panel)}
.rang.att .cle.etoi{color:var(--accent);font-weight:600}
.rang.fige .cle.etoi{color:var(--accent);font-weight:600}
.piste{height:9px;background:#EAE6DC;border-radius:2px;overflow:hidden}
.piste i{display:block;height:100%;background:var(--accent);border-radius:2px}

/* ---- textes ---- */
.textes{margin-top:56px}
.onglets{display:flex;gap:8px;margin-bottom:16px;align-items:center}
.bascule{font:inherit;font-size:13.5px;padding:5px 13px;border-radius:3px;cursor:pointer;
  background:transparent;color:var(--mute);border:1px solid transparent}
.bascule[aria-selected=true]{background:var(--panel);color:var(--ink)}
.corpus{font-family:var(--mono);font-size:12.5px;line-height:1.85;max-width:74ch;
  word-break:break-word;max-height:420px;overflow-y:auto;color:#3A362F}
.longueur{margin-left:auto;display:flex;align-items:center;gap:9px;font-size:13px;color:var(--mute)}
.longueur input{width:88px;min-width:0}

@media (prefers-reduced-motion:no-preference){
  .cel.val{animation:apparait .34s ease both;animation-delay:var(--d)}
  @keyframes apparait{from{opacity:0}to{opacity:1}}
}
@media (max-width:900px){
  .hero,.duo{grid-template-columns:1fr;gap:28px}
  .cifras{grid-template-columns:1fr}
  .lecture{position:static}
  .etat{margin-left:0}
}
</style>
</head>
<body>
<div class="wrap">

<div class="bar">
  <div class="champ">
    <label for="titre">Article Wikipedia</label>
    <input type="text" id="titre" value="Soup" autocomplete="off">
  </div>
  <div class="champ">
    <label for="lang">Langue</label>
    <select id="lang">
      <option value="fr">fr</option><option value="en">en</option>
      <option value="es">es</option><option value="de">de</option><option value="it">it</option>
    </select>
  </div>
  <label class="case"><input type="checkbox" id="intro"> Introduction seule</label>
  <button id="lancer">Analyser</button>
</div>

<div class="cifras">
  <section class="cifra">
    <h3>Cesar <span class="algo">un decalage fixe pour tout le texte</span></h3>
    <p class="aide">1 chiffre le texte &middot; 2 dechiffre avec le meme decalage &middot; 3 retrouve le decalage</p>
    <div class="ligne">
      <div class="champ">
        <label for="cesar">Decalage (0-25)</label>
        <input type="text" id="cesar" value="3" inputmode="numeric">
      </div>
    </div>
    <div class="ligne">
      <button id="crypto">1 Cryptogramme</button>
      <button id="dechiffre">2 Decrypter</button>
      <button id="attaque-btn">3 Attaque</button>
    </div>
  </section>

  <section class="cifra">
    <h3>Vigenere <span class="algo">un decalage par colonne, repete</span></h3>
    <p class="aide">1 chiffre le texte &middot; 2 dechiffre avec la cle &middot; 3 retrouve la cle, colonne par colonne</p>
    <div class="ligne">
      <div class="champ">
        <label for="cle-vigenere">Cle (mot)</label>
        <input type="text" id="cle-vigenere" value="ORACLE" autocomplete="off">
      </div>
      <div class="champ">
        <label for="periode-vigenere">Periode L</label>
        <input type="text" id="periode-vigenere" value="6" inputmode="numeric">
      </div>
    </div>
    <div class="ligne">
      <button id="crypto-vigenere">1 Cryptogramme</button>
      <button id="dechiffre-vigenere">2 Decrypter</button>
      <button id="attaque-btn-vigenere">3 Attaque</button>
    </div>
  </section>

  <section class="cifra">
    <h3>Permutation <span class="algo">Vigenere + positions melangees</span></h3>
    <p class="aide">1 Melange lettres et positions &middot; 2 remet en ordre avec la cle &middot; 3 retrouve les decalages</p>
    <div class="ligne">
      <div class="champ">
        <label for="cle-permutation">Cle (mot)</label>
        <input type="text" id="cle-permutation" value="LEMON" autocomplete="off">
      </div>
      <div class="champ">
        <label for="periode-permutation">Periode L</label>
        <input type="text" id="periode-permutation" value="5" inputmode="numeric">
      </div>
    </div>
    <div class="ligne">
      <button id="crypto-permutation">1 Cryptogramme</button>
      <button id="dechiffre-permutation">2 Decrypter</button>
      <button id="attaque-btn-permutation">3 Attaque</button>
    </div>
  </section>

  <div class="etat" id="etat">Choisissez un article, puis Analyzez : les trois cifras se regleront d'un coup.</div>
</div>

<div class="vide" id="vide">Chaque case indique la probabilite qu'une lettre en suive une autre dans le texte choisi.</div>

<main id="contenu" hidden>
  <section>
    <h2>Matrice de transition</h2>
    <p class="legende">Ligne : lettre courante. Colonne : lettre suivante. Survolez une case pour la lire.</p>
    <div class="hero">
      <div class="grille" id="grille"></div>
      <aside class="lecture">
        <p class="proba" id="proba">&mdash;</p>
        <p id="detail">Survolez la matrice.</p>
        <dl id="bilan"></dl>
        <div class="echelle" id="echelle"></div>
        <div class="bornes"><span>0</span><span>1</span></div>
      </aside>
    </div>
  </section>

  <div class="duo">
    <section>
      <h2>Frequences des caracteres</h2>
      <p class="legende" id="leg-freq"></p>
      <div id="freq"></div>
      <button class="discret plus" id="freq-plus" hidden>Voir plus</button>
    </section>
    <section>
      <h2>Digrammes les plus frequents</h2>
      <p class="legende" id="leg-dig"></p>
      <div id="dig"></div>
      <button class="discret plus" id="dig-plus" hidden>Voir plus</button>
    </section>
  </div>

  <section class="textes">
    <div class="onglets" role="tablist">
      <button class="bascule" role="tab" aria-selected="true" data-vue="genere">Texte genere</button>
      <button class="bascule" role="tab" aria-selected="false" data-vue="crypto">Cryptogramme</button>
      <button class="bascule" role="tab" aria-selected="false" data-vue="dechiffre">Dechiffre</button>
      <button class="bascule" role="tab" aria-selected="false" data-vue="attaque">Attaque</button>
      <button class="bascule" role="tab" aria-selected="false" data-vue="source">Texte source</button>
      <div class="longueur" id="reglage">
        <label for="longueur">Longueur</label>
        <input type="text" id="longueur" value="2000" inputmode="numeric">
        <button class="discret" id="regenerer">Regenerer</button>
      </div>
    </div>
    <div class="corpus" id="corpus"></div>
  </section>

  <section id="sec-attaque" hidden>
    <h2>Attaque frequentielle</h2>
    <p class="legende" id="leg-att"></p>
    <div id="attaque-list"></div>
  </section>
</main>
</div>

<script>
const RAMPE = ["#F4F1E8","#E4E7DC","#CBD9CB","#ADC8B7","#8AB49F","#659E85","#43876C","#276F55","#14563F"];
const $ = (id) => document.getElementById(id);
let DONNEES = null, CASES = [], vueActive = "genere", vueCible = "cesar";

RAMPE.forEach(c => { const s = document.createElement("span"); s.style.background = c; $("echelle").appendChild(s); });

function nombre(n){ return n.toLocaleString("fr-FR"); }
function nom(c){ return c === " " ? "espace" : c; }
function symbole(c){ return c === " " ? "\\u2423" : c; }

function statut(message, rouge){
  const e = $("etat");
  e.textContent = message;
  e.classList.toggle("rouge", !!rouge);
}

function afficherVue(quelle){
  vueActive = quelle;
  document.querySelectorAll(".bascule").forEach(a => a.setAttribute("aria-selected", a.dataset.vue === quelle));
  afficherCorpus();
}

// Boutons en cours d'appel : rafraichirBoutons doit les laisser grilles.
const EN_COURS = new Set();

async function charger(url, bouton){
  if (bouton) EN_COURS.add(bouton.id);
  try {
    const reponse = await fetch(url);
    return await reponse.json();
  } catch (erreur) {
    return { erreur: "Le serveur ne repond pas." };
  } finally {
    if (bouton) EN_COURS.delete(bouton.id);
    rafraichirBoutons();
  }
}

// Chaque cifra a son champ de cle et son bouton "Attaque" : les trois cartes
// se reglent independamment, dans le meme ordre 1 / 2 / 3.
const CIFRAS = {
  vigenere:    { cle: "cle-vigenere",    periode: "periode-vigenere",    url: "/api/vigenere",    nom: "Vigenere" },
  permutation: { cle: "cle-permutation", periode: "periode-permutation", url: "/api/permutation", nom: "Permutation" },
};

function suffixe(cible){ return cible === "cesar" ? "" : "-" + cible; }

function rafraichirBoutons(){
  const pret = !!DONNEES;
  const actif = (id, pret2) => { $(id).disabled = !pret2 || EN_COURS.has(id); };

  ["cesar", "cle-vigenere", "periode-vigenere", "cle-permutation", "periode-permutation"]
    .forEach(id => actif(id, pret));

  // 1 : on peut toujours chiffrer le texte analyse.
  ["crypto", "crypto-vigenere", "crypto-permutation"].forEach(id => actif(id, pret));

  // 2 et 3 : seulement si la cifra a deja produit son cryptogramme.
  ["cesar", "vigenere", "permutation"].forEach(cible => {
    const existe = pret && !!DONNEES.crypto[cible];
    actif("dechiffre" + suffixe(cible), existe);
    actif("attaque-btn" + suffixe(cible), existe);
  });
}

function lireCle(id){
  const cle = $(id).value.trim().toUpperCase();
  if (!cle) { statut("Indiquez une cle : un mot de lettres.", true); return null; }
  if (!/^[A-Z]+$/.test(cle)) { statut("La cle ne doit contenir que des lettres.", true); return null; }
  return cle;
}

function lirePeriode(id){
  const periode = parseInt($(id).value, 10);
  if (isNaN(periode) || periode < 1) { statut("Periode invalide : entier positif.", true); return null; }
  return periode;
}

// La periode vaut la longueur de la cle tant qu'on ne la corrige pas a la main.
function lierCle(idCle, idPeriode){
  $(idCle).addEventListener("input", () => {
    const mot = $(idCle).value.trim().toUpperCase();
    if (/^[A-Z]+$/.test(mot)) $(idPeriode).value = mot.length;
  });
}
lierCle("cle-vigenere", "periode-vigenere");
lierCle("cle-permutation", "periode-permutation");

async function analyser(){
  const titre = $("titre").value.trim();
  if (!titre) { statut("Indiquez un titre d'article.", true); return; }
  $("lancer").disabled = true;
  statut("Telechargement de " + titre + "\\u2026");

  const url = "/api/analyse?titre=" + encodeURIComponent(titre)
    + "&lang=" + $("lang").value + "&intro=" + ($("intro").checked ? "1" : "0");
  const reponse = await charger(url, $("lancer"));

  if (reponse.erreur) { statut(reponse.erreur, true); return; }

  DONNEES = reponse;
  DONNEES.crypto = {};
  DONNEES.dechiffre = null;
  DONNEES.attaque = null;
  $("sec-attaque").hidden = true;
  vueCible = "cesar";
  $("vide").hidden = true;
  $("contenu").hidden = false;
  const distincts = Object.keys(reponse.digrammes).length;
  statut(nombre(reponse.stats.global_count) + " caracteres \\u00b7 " + distincts + " digrammes distincts \\u00b7 cryptogramme dans la carte voulue.");
  dessinerMatrice();
  dessinerFrequences();
  dessinerDigrammes();
  resume();
  afficherVue("genere");
  rafraichirBoutons();
}

function dessinerMatrice(){
  const { matrix, etats } = DONNEES;
  const grille = $("grille");
  grille.innerHTML = "";
  CASES = [];

  const entete = document.createElement("div");
  entete.className = "ligne";
  entete.appendChild(cellule("", "cel src"));
  etats.forEach((c, y) => {
    const t = cellule(symbole(c), "cel tete");
    t.dataset.col = y;
    entete.appendChild(t);
  });
  entete.appendChild(cellule("\\u03a3", "cel somme"));
  grille.appendChild(entete);

  matrix.forEach((row, x) => {
    const ligne = document.createElement("div");
    ligne.className = "ligne";
    ligne.appendChild(cellule(symbole(etats[x]), "cel src"));
    const rang = [];

    row.forEach((v, y) => {
      const nul = v === 0;
      const c = cellule(nul ? "\\u00b7" : format(v), "cel val" + (nul ? " nul" : ""));
      if (!nul) {
        const niveau = Math.min(Math.floor(v * RAMPE.length), RAMPE.length - 1);
        c.style.background = RAMPE[niveau];
        if (niveau >= 5) c.style.color = "#FBFAF7";
      }
      c.style.setProperty("--d", (x + y) * 5 + "ms");
      c.onmouseenter = () => lire(x, y);
      rang.push(c);
      ligne.appendChild(c);
    });

    const total = row.reduce((a, b) => a + b, 0);
    ligne.appendChild(cellule(total.toFixed(2), "cel somme" + (total === 0 ? " zero" : "")));
    grille.appendChild(ligne);
    CASES.push(rang);
  });

  grille.onmouseleave = () => { nettoyer(); resume(); };
}

function cellule(texte, classe){
  const d = document.createElement("div");
  d.className = classe;
  d.textContent = texte;
  return d;
}

function format(v){
  if (v >= 0.995) return "1";
  return v.toFixed(2).slice(1);
}

function nettoyer(){
  document.querySelectorAll(".vise").forEach(e => e.classList.remove("vise"));
  document.querySelectorAll(".ligne.actif").forEach(e => e.classList.remove("actif"));
  document.querySelectorAll(".colactif").forEach(e => e.classList.remove("colactif"));
}

function lire(x, y){
  nettoyer();
  const { matrix, etats, digrammes, stats } = DONNEES;
  const de = etats[x], vers = etats[y];
  const cible = CASES[x][y];
  cible.classList.add("vise");
  cible.parentElement.classList.add("actif");
  document.querySelector('.tete[data-col="' + y + '"]').classList.add("colactif");

  $("proba").innerHTML = matrix[x][y].toFixed(3)
    + ' <span class="petit">P(' + nom(vers) + ' | ' + nom(de) + ')</span>';
  const paire = de + vers;
  const vus = digrammes[paire] || 0;
  $("detail").textContent = vus
    ? "Le digramme " + nom(de) + nom(vers) + " apparait " + nombre(vus) + (vus > 1 ? " fois." : " fois.")
    : "Ce digramme n'apparait jamais dans le texte.";
  $("bilan").innerHTML =
      ligneBilan(nom(de) + " dans le texte", nombre(stats.character_count[de]))
    + ligneBilan("Transitions depuis " + nom(de), nombre(Object.keys(digrammes)
        .filter(d => d[0] === de).reduce((s, d) => s + digrammes[d], 0)))
    + ligneBilan("Suivant le plus probable", meilleur(matrix[x], etats));
}

function ligneBilan(cle, valeur){ return "<dt>" + cle + "</dt><dd>" + valeur + "</dd>"; }

function meilleur(row, etats){
  let i = 0;
  row.forEach((v, k) => { if (v > row[i]) i = k; });
  return row[i] ? nom(etats[i]) + " " + row[i].toFixed(2) : "aucun";
}

function resume(){
  const { matrix, etats } = DONNEES;
  const morts = etats.filter((c, x) => matrix[x].every(v => v === 0));
  const jamais = etats.filter((c, y) => matrix.every(row => row[y] === 0));
  $("proba").innerHTML = '<span class="petit">Vue d\\'ensemble</span>';
  $("detail").textContent = "Survolez une case pour lire une probabilite de transition.";
  $("bilan").innerHTML =
      ligneBilan("Sans transition sortante", morts.length ? morts.map(nom).join(", ") : "aucun")
    + ligneBilan("Jamais atteints", jamais.length ? jamais.map(nom).join(", ") : "aucun");
}

// Listes longues : on montre les 5 premiers et on laisse le reste derriere un
// "Voir plus" / "Voir moins", sinon les 26 lettres ou les centaines de
// digrammes ecrasent le reste de la page.
const PLIAGE = { freq: false, dig: false };

function barres(cible, entrees, total, formateur, cle, limite = 5){
  const visibles = PLIAGE[cle] ? entrees : entrees.slice(0, limite);
  const maxi = visibles[0] ? visibles[0][1] : 1;
  cible.innerHTML = visibles.map(([cle2, n]) =>
    '<div class="rang"><span class="cle">' + formateur(cle2) + '</span>'
    + '<span class="piste"><i style="width:' + (n / maxi * 100).toFixed(1) + '%"></i></span>'
    + '<span class="n">' + nombre(n) + '</span>'
    + '<span class="pc">' + (n / total * 100).toFixed(2) + '%</span></div>').join("");

  const reste = entrees.length - limite;
  const bouton = $(cle + "-plus");
  bouton.hidden = reste <= 0;
  bouton.textContent = PLIAGE[cle] ? "Voir moins" : "Voir plus (" + nombre(reste) + ")";
}

function dessinerFrequences(){
  const { stats } = DONNEES;
  const entrees = Object.entries(stats.character_count).sort((a, b) => b[1] - a[1]);
  $("leg-freq").textContent = nombre(stats.global_count) + " caracteres retenus, accents supprimes.";
  barres($("freq"), entrees, stats.global_count || 1, nom, "freq");
}

function dessinerDigrammes(){
  const entrees = Object.entries(DONNEES.digrammes).sort((a, b) => b[1] - a[1]);
  const total = entrees.reduce((s, e) => s + e[1], 0) || 1;
  $("leg-dig").textContent = "Les 5 plus frequents sur " + entrees.length + " observes.";
  barres($("dig"), entrees, total, d => d.split("").map(symbole).join(""), "dig");
}

$("freq-plus").onclick = () => { PLIAGE.freq = !PLIAGE.freq; dessinerFrequences(); };
$("dig-plus").onclick = () => { PLIAGE.dig = !PLIAGE.dig; dessinerDigrammes(); };

function afficherCorpus(){
  $("corpus").textContent = vueActive === "genere" ? DONNEES.genere
    : vueActive === "crypto" ? (DONNEES.crypto[vueCible] || "(Aucun cryptogramme genere.)")
    : vueActive === "dechiffre" ? (DONNEES.dechiffre || "(Aucun dechiffrement effectue.)")
    : vueActive === "attaque" ? (DONNEES.attaque ? DONNEES.attaque.texte : "(Aucune attaque effectuee.)")
    : DONNEES.content;
  $("reglage").style.visibility = vueActive === "genere" ? "visible" : "hidden";
}

function dessinerAttaque(){
  const attaque = DONNEES.attaque;
  const liste = $("attaque-list");
  liste.innerHTML = "";
  $("sec-attaque").hidden = false;

  if (attaque.mode === "colonnes") {
    const suite = attaque.positions_melangees
      ? " Lettres dechiffrees, mais remises a la place de leur colonne destination : la permutation reste a retrouver."
      : "";
    $("leg-att").textContent = "Periode " + attaque.periode + " \\u00b7 decalages "
      + attaque.cle_lue.split("").join(" / ") + " \\u00b7 ecart mini " + attaque.fiabilite
      + " (fiabilite)" + suite;
    const maxi = Math.max.apply(null, attaque.colonnes.map(c => c.score));
    attaque.colonnes.forEach(colonne => {
      const rang = document.createElement("div");
      rang.className = "rang fige";
      rang.innerHTML = '<span class="cle etoi"> ' + colonne.colonne + '</span>'
        + '<span class="piste"><i style="width:' + (colonne.score / maxi * 100).toFixed(1) + '%"></i></span>'
        + '<span class="n">+' + colonne.decalage + '</span>'
        + '<span class="pc">' + nombre(colonne.lettres) + '</span>';
      liste.appendChild(rang);
    });
    return;
  }

  const maxi = attaque.scores[0].score;
  $("leg-att").textContent = "Cle la plus probable : " + attaque.decalage + " \\u2605   |   Notes des 26 decalages.";

  attaque.scores.forEach(s => {
    const rang = document.createElement("div");
    rang.className = "rang att";
    rang.dataset.cle = s.decalage;
    const best = s.decalage === attaque.decalage;
    rang.innerHTML =
        '<span class="cle' + (best ? " etoi" : "") + '"> ' + s.decalage + (best ? " \\u2605" : "") + '</span>'
      + '<span class="piste"><i style="width:' + (s.score / maxi * 100).toFixed(1) + '%"></i></span>'
      + '<span class="n">' + s.score.toFixed(4) + '</span>';
    liste.appendChild(rang);
  });
}

$("attaque-list").onclick = async (ev) => {
  const rang = ev.target.closest(".rang.att");
  if (!rang || !rang.dataset.cle) return;
  const cle = parseInt(rang.dataset.cle, 10);
  statut("Dechiffrement avec la cle candidate " + cle + "\\u2026");
  const reponse = await charger("/api/cesar?decalage=" + cle + "&mode=dechiffre&t=" + Date.now());
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.dechiffre = reponse.texte;
  afficherVue("dechiffre");
  statut("Dechiffrement affiche avec la cle candidate " + cle + ".");
};

document.querySelectorAll(".bascule").forEach(b => {
  b.onclick = () => afficherVue(b.dataset.vue);
});

$("regenerer").onclick = async () => {
  const longueur = parseInt($("longueur").value, 10) || 2000;
  $("regenerer").disabled = true;
  const reponse = await charger("/api/generer?longueur=" + longueur);
  $("regenerer").disabled = false;
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.genere = reponse.texte;
  afficherVue("genere");
};

$("lancer").onclick = analyser;
$("titre").addEventListener("keydown", e => { if (e.key === "Enter") analyser(); });

function noteCesar(saisie, decalage){
  return saisie !== decalage ? " (cle " + saisie + " hors 0-25, utilisee " + decalage + " par modulo 26)" : "";
}

$("crypto").onclick = async () => {
  if (!DONNEES) { statut("Analysez d'abord un article.", true); return; }
  const saisie = parseInt($("cesar").value, 10);
  if (isNaN(saisie)) { statut("Entrez une cle Cesar : entier entre 0 et 25.", true); return; }
  const decalage = ((saisie % 26) + 26) % 26;
  statut("Chiffrement avec la cle " + decalage + "\\u2026");
  const reponse = await charger("/api/cesar?decalage=" + decalage + "&t=" + Date.now(), $("crypto"));
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.crypto.cesar = reponse.cryptogramme;
  vueCible = "cesar";
  rafraichirBoutons();
  afficherVue("crypto");
  statut("Cryptogramme genere (cle " + reponse.decalage + ", " + nombre(reponse.cryptogramme.length) + " caracteres)."
    + noteCesar(saisie, decalage));
};

$("dechiffre").onclick = async () => {
  if (!DONNEES) { statut("Analysez d'abord un article.", true); return; }
  if (!DONNEES.crypto.cesar) { statut("Generer d'abord un cryptogramme a dechiffrer.", true); return; }
  const saisie = parseInt($("cesar").value, 10);
  if (isNaN(saisie)) { statut("Entrez une cle Cesar : entier entre 0 et 25.", true); return; }
  const decalage = ((saisie % 26) + 26) % 26;
  statut("Dechiffrement avec la cle " + decalage + "\\u2026");
  const reponse = await charger("/api/cesar?decalage=" + decalage + "&mode=dechiffre&t=" + Date.now(), $("dechiffre"));
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.dechiffre = reponse.texte;
  afficherVue("dechiffre");
  statut("Dechiffrement effectue avec la cle " + reponse.decalage + "." + noteCesar(saisie, decalage));
};

$("attaque-btn").onclick = async () => {
  if (!DONNEES) { statut("Analysez d'abord un article.", true); return; }
  if (!DONNEES.crypto.cesar) { statut("Generer d'abord un cryptogramme a attaquer.", true); return; }
  statut("Attaque frequentielle en cours\\u2026");
  const reponse = await charger("/api/attaque?t=" + Date.now(), $("attaque-btn"));
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.attaque = reponse;
  dessinerAttaque();
  afficherVue("attaque");
  statut("Cle la plus probable : " + reponse.decalage + ".");
};

// Chiffrement, dechiffrement et attaque des cifras a cle connue.
async function chiffrer(cible){
  const f = CIFRAS[cible];
  const bouton = $("crypto" + suffixe(cible));
  if (!DONNEES) { statut("Analysez d'abord un article.", true); return; }
  const cle = lireCle(f.cle);
  if (!cle) return;
  statut(f.nom + " avec la cle " + cle + "\\u2026");
  const reponse = await charger(f.url + "?cle=" + encodeURIComponent(cle) + "&mode=chiffre&t=" + Date.now(), bouton);
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.crypto[cible] = reponse.cryptogramme;
  vueCible = cible;
  rafraichirBoutons();
  afficherVue("crypto");
  statut("Cryptogramme " + f.nom + " genere (" + nombre(reponse.cryptogramme.length) + " caracteres) : vous pouvez decrypter ou attaquer.");
}

async function dechiffrer(cible){
  const f = CIFRAS[cible];
  const bouton = $("dechiffre" + suffixe(cible));
  if (!DONNEES) { statut("Analysez d'abord un article.", true); return; }
  if (!DONNEES.crypto[cible]) { statut("Generer d'abord le cryptogramme " + f.nom + ".", true); return; }
  const cle = lireCle(f.cle);
  if (!cle) return;
  statut("Dechiffrement " + f.nom + " avec la cle " + cle + "\\u2026");
  const reponse = await charger(f.url + "?cle=" + encodeURIComponent(cle) + "&mode=dechiffre&t=" + Date.now(), bouton);
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.dechiffre = reponse.texte;
  vueCible = cible;
  afficherVue("dechiffre");
  statut("Dechiffrement " + f.nom + " effectue avec la cle " + reponse.cle + ".");
}

async function attaquerColonnes(cible){
  const f = CIFRAS[cible];
  const bouton = $("attaque-btn" + suffixe(cible));
  if (!DONNEES) { statut("Analysez d'abord un article.", true); return; }
  if (!DONNEES.crypto[cible]) { statut("Generer d'abord le cryptogramme " + f.nom + ".", true); return; }
  const periode = lirePeriode(f.periode);
  if (!periode) return;
  statut("Attaque " + f.nom + " par colonnes, periode " + periode + "\\u2026");
  const reponse = await charger("/api/attaque-" + cible + "?periode=" + periode + "&t=" + Date.now(), bouton);
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.attaque = reponse;
  dessinerAttaque();
  afficherVue("attaque");
  statut("Decalages lus : " + reponse.cle_lue + " \\u00b7 ecart mini " + reponse.fiabilite + ".");
}

$("crypto-vigenere").onclick = () => chiffrer("vigenere");
$("dechiffre-vigenere").onclick = () => dechiffrer("vigenere");
$("crypto-permutation").onclick = () => chiffrer("permutation");
$("dechiffre-permutation").onclick = () => dechiffrer("permutation");
$("attaque-btn-vigenere").onclick = () => attaquerColonnes("vigenere");
$("attaque-btn-permutation").onclick = () => attaquerColonnes("permutation");
</script>
</body>
</html>
"""


def main() -> None:
    serveur = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    adresse = f"http://127.0.0.1:{PORT}/"
    print(f"Interface disponible sur {adresse}  (Ctrl+C pour arreter)")
    threading.Timer(0.6, webbrowser.open, args=(adresse,)).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArret.")
        serveur.server_close()


if __name__ == "__main__":
    main()