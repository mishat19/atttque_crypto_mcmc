import requests

WIKI_UA = "MonScript/1.0 (simon@example.com)" 
SATES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", " "]

def wiki_text(titre, lang= "fr", intro_seule = False):
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

    return content

def statistics(titre, lang="fr", intro_seule=False):
    content = wiki_text(titre, lang, intro_seule)
    stats = {
        "global_count": len(content),
        "character_count": {char: content.count(char) for char in SATES},
        }
    return stats


def display(stats, largeur=50):
    total = stats["global_count"] or 1
    counts = sorted(stats["character_count"].items(), key=lambda kv: kv[1], reverse=True)
    maxi = counts[0][1] or 1

    print(f"{total} caractères\n")
    for char, n in counts:
        label = "espace" if char == " " else char
        barre = "#" * round(n / maxi * largeur)
        print(f"{label:>6} {n:6d} {n / total:6.2%}  {barre}")


print(wiki_text("Paris", "fr", True))
print("\n==================\n")
display(statistics("Paris", "fr", True))