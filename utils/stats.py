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

    if len(content) % 2 == 1:
        content += " "

    return content

# =============== STATS ==============

def statistics(content):
    stats = {
        "global_count": len(content),
        "character_count": {char: content.count(char) for char in SATES},
        }
    return stats

def display_stats(stats, largeur=50):
    total = stats["global_count"] or 1
    counts = sorted(stats["character_count"].items(), key=lambda kv: kv[1], reverse=True)
    maxi = counts[0][1] or 1

    print(f"{total} caractères\n")
    for char, n in counts:
        label = "espace" if char == " " else char
        barre = "#" * round(n / maxi * largeur)
        print(f"{label:>6} {n:6d} {n / total:6.2%}  {barre}")

# =============== DIAGRAMS =============

def digram_stats(content, largeur=2):
    content_length = len(content)
    diagram_stats = {}
    
    for index in range(0, content_length, largeur):
        segment = content[index:index + largeur]
        diagram_stats[segment] = diagram_stats[segment] + 1 if segment in diagram_stats else 1

    return diagram_stats


def display_digrams(diagrams, top=20000, largeur=50):
    total = sum(diagrams.values()) or 1
    counts = sorted(diagrams.items(), key=lambda kv: kv[1], reverse=True)[:top]
    maxi = counts[0][1] or 1

    print(f"{len(diagrams)} digrammes distincts, {total} au total — top {len(counts)}\n")
    for segment, n in counts:
        label = segment.replace(" ", "_")
        barre = "#" * round(n / maxi * largeur)
        print(f"{label:>6} {n:6d} {n / total:6.2%}  {barre}")


# ============= MATRICE =============
SHADES = " .:-=+*#%@"

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

def display_matrix(matrix, decimales=2):
    labels = ["_" if char == " " else char for char in SATES]
    cell = 2 + decimales  # "0.15" tient sur 4 colonnes quand decimales=2

    print(" " * 4 + " ".join(f"{label:>{cell}}" for label in labels))
    for x, row in enumerate(matrix):
        cells = " ".join(
            f"{value:{cell}.{decimales}f}" if value else f"{'.':>{cell}}"
            for value in row
        )
        print(f"{labels[x]:>3} " + cells)
    print("\nligne = caractère courant, colonne = suivant")


def text_generator(matrix, longueur=1000):
    import random

    text = ""
    current_char = " "
    for _ in range(longueur):
        x = SATES.index(current_char)
        next_char = random.choices(SATES, weights=matrix[x])[0]
        text += next_char
        current_char = next_char

    return text

content = wiki_text("Soup", "en", False)
print(content)
print("\n==================\n")
display_stats(statistics(content))
print("\n==================\n")
display_digrams(digram_stats(content))
print("\n==================\n")
display_matrix(markov_matrix(digram_stats(content)))
print("\n==================\n")
print(text_generator(markov_matrix(digram_stats(content)), 2000))