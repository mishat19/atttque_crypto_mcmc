"""Analyse de digrammes et chaine de Markov d'un texte Wikipedia, avec interface web locale.

Meme logique de calcul que stats.py. L'interface est servie par http.server (stdlib)
et s'ouvre dans le navigateur : aucune dependance en plus de requests.

Lancement :  python stats_web.py
"""

from __future__ import annotations

import http.server
import json
import random
import threading
import urllib.parse
import webbrowser

import requests

WIKI_UA = "MonScript/1.0 (simon@example.com)"
SATES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
         "V", "W", "X", "Y", "Z", " "]

PORT = 8765


# =============== DONNEES (identique a stats.py) ==============

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

    resp = requests.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params=params,
        headers={"User-Agent": WIKI_UA},
        timeout=10,
    )
    resp.raise_for_status()

    page = next(iter(resp.json()["query"]["pages"].values()))

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
    text = ""
    current_char = " "
    for _ in range(longueur):
        x = SATES.index(current_char)
        next_char = random.choices(SATES, weights=matrix[x])[0]
        text += next_char
        current_char = next_char

    return text


# =============== SERVEUR ==============

ETAT: dict = {"matrix": None}


def analyser(titre: str, lang: str, intro_seule: bool) -> dict:
    """Telecharge l'article et renvoie tout ce dont la page a besoin."""
    content = wiki_text(titre, lang, intro_seule)
    if not content:
        return {"erreur": "Aucun texte exploitable dans cet article."}

    digrammes = digram_stats(content)
    matrix = markov_matrix(digrammes)
    ETAT["matrix"] = matrix

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


class Handler(http.server.BaseHTTPRequestHandler):
    """Sert la page et deux points d'entree JSON."""

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

        self._repondre(404, "text/plain; charset=utf-8", b"Page inconnue")

    @staticmethod
    def _sur(fonction, *args) -> dict:
        """Convertit toute exception en message affichable par la page."""
        try:
            return fonction(*args)
        except requests.HTTPError:
            return {"erreur": "Wikipedia a refuse la requete. Verifiez le titre et la langue."}
        except requests.RequestException:
            return {"erreur": "Connexion impossible a Wikipedia."}
        except Exception as erreur:  # noqa: BLE001 - le serveur ne doit jamais tomber
            return {"erreur": str(erreur)}

    def _json(self, charge: dict) -> None:
        self._repondre(200, "application/json; charset=utf-8", json.dumps(charge).encode("utf-8"))

    def _repondre(self, code: int, type_mime: str, corps: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(corps)))
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
.etat{margin-left:auto;font-size:13.5px;color:var(--mute);padding-bottom:9px}
.etat.rouge{color:var(--alert)}

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
  .lecture{position:static}
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
  <div class="etat" id="etat">Choisissez un article pour construire sa matrice.</div>
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
    </section>
    <section>
      <h2>Digrammes les plus frequents</h2>
      <p class="legende" id="leg-dig"></p>
      <div id="dig"></div>
    </section>
  </div>

  <section class="textes">
    <div class="onglets" role="tablist">
      <button class="bascule" role="tab" aria-selected="true" data-vue="genere">Texte genere</button>
      <button class="bascule" role="tab" aria-selected="false" data-vue="source">Texte source</button>
      <div class="longueur" id="reglage">
        <label for="longueur">Longueur</label>
        <input type="text" id="longueur" value="2000" inputmode="numeric">
        <button class="discret" id="regenerer">Regenerer</button>
      </div>
    </div>
    <div class="corpus" id="corpus"></div>
  </section>
</main>
</div>

<script>
const RAMPE = ["#F4F1E8","#E4E7DC","#CBD9CB","#ADC8B7","#8AB49F","#659E85","#43876C","#276F55","#14563F"];
const $ = (id) => document.getElementById(id);
let DONNEES = null, CASES = [], vueActive = "genere";

RAMPE.forEach(c => { const s = document.createElement("span"); s.style.background = c; $("echelle").appendChild(s); });

function nombre(n){ return n.toLocaleString("fr-FR"); }
function nom(c){ return c === " " ? "espace" : c; }
function symbole(c){ return c === " " ? "\\u2423" : c; }

function statut(message, rouge){
  const e = $("etat");
  e.textContent = message;
  e.classList.toggle("rouge", !!rouge);
}

async function analyser(){
  const titre = $("titre").value.trim();
  if (!titre) { statut("Indiquez un titre d'article.", true); return; }
  $("lancer").disabled = true;
  statut("Telechargement de " + titre + "\\u2026");

  const url = "/api/analyse?titre=" + encodeURIComponent(titre)
    + "&lang=" + $("lang").value + "&intro=" + ($("intro").checked ? "1" : "0");
  const reponse = await fetch(url).then(r => r.json());
  $("lancer").disabled = false;

  if (reponse.erreur) { statut(reponse.erreur, true); return; }

  DONNEES = reponse;
  $("vide").hidden = true;
  $("contenu").hidden = false;
  const distincts = Object.keys(reponse.digrammes).length;
  statut(nombre(reponse.stats.global_count) + " caracteres \\u00b7 " + distincts + " digrammes distincts");
  dessinerMatrice();
  dessinerFrequences();
  dessinerDigrammes();
  afficherCorpus();
  resume();
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

function barres(cible, entrees, total, formateur){
  const maxi = entrees[0] ? entrees[0][1] : 1;
  cible.innerHTML = entrees.map(([cle, n]) =>
    '<div class="rang"><span class="cle">' + formateur(cle) + '</span>'
    + '<span class="piste"><i style="width:' + (n / maxi * 100).toFixed(1) + '%"></i></span>'
    + '<span class="n">' + nombre(n) + '</span>'
    + '<span class="pc">' + (n / total * 100).toFixed(2) + '%</span></div>').join("");
}

function dessinerFrequences(){
  const { stats } = DONNEES;
  const entrees = Object.entries(stats.character_count).sort((a, b) => b[1] - a[1]);
  $("leg-freq").textContent = nombre(stats.global_count) + " caracteres retenus, accents supprimes.";
  barres($("freq"), entrees, stats.global_count || 1, nom);
}

function dessinerDigrammes(){
  const entrees = Object.entries(DONNEES.digrammes).sort((a, b) => b[1] - a[1]);
  const total = entrees.reduce((s, e) => s + e[1], 0) || 1;
  $("leg-dig").textContent = "Les 30 plus frequents sur " + entrees.length + " observes.";
  barres($("dig"), entrees.slice(0, 30), total, d => d.split("").map(symbole).join(""));
}

function afficherCorpus(){
  $("corpus").textContent = vueActive === "genere" ? DONNEES.genere : DONNEES.content;
  $("reglage").style.visibility = vueActive === "genere" ? "visible" : "hidden";
}

document.querySelectorAll(".bascule").forEach(b => {
  b.onclick = () => {
    document.querySelectorAll(".bascule").forEach(a => a.setAttribute("aria-selected", a === b));
    vueActive = b.dataset.vue;
    afficherCorpus();
  };
});

$("regenerer").onclick = async () => {
  const longueur = parseInt($("longueur").value, 10) || 2000;
  $("regenerer").disabled = true;
  const reponse = await fetch("/api/generer?longueur=" + longueur).then(r => r.json());
  $("regenerer").disabled = false;
  if (reponse.erreur) { statut(reponse.erreur, true); return; }
  DONNEES.genere = reponse.texte;
  vueActive = "genere";
  document.querySelectorAll(".bascule").forEach(a => a.setAttribute("aria-selected", a.dataset.vue === "genere"));
  afficherCorpus();
};

$("lancer").onclick = analyser;
$("titre").addEventListener("keydown", e => { if (e.key === "Enter") analyser(); });
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