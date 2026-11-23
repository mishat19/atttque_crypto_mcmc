"""Version terminal (historique) de l'analyse de digrammes et de la chaîne de Markov.

Ce script télécharge un article Wikipédia, réduit le texte à un alphabet de
42 symboles (26 lettres + 15 lettres accentuées + espace), puis affiche :
- l'histogramme des caractères ;
- l'histogramme des digrammes (paires de caractères) ;
- la matrice de transition 42×42 ;
- un texte aléatoire généré par la chaîne.

C'est le même calcul que ``utils/app.py``, mais sans interface web et avec la
bibliothèque externe ``requests`` au lieu de ``urllib`` (stdlib). Le code de
démonstration en bas de fichier s'exécute dès le lancement.

Lancement : python utils/stats.py   (nécessite ``pip install requests``)
"""

import requests

# User-Agent obligatoire pour l'API Wikipédia : sans lui, les requêtes
# anonymes peuvent être rejetées.
WIKI_UA = "MonScript/1.0 (simon@example.com)" 
# Alphabet réduit utilisé par la chaîne : chaque état est un symbole.
SATES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "À", "Â", "Ä", "É", "È", "Ê", "Ë", "Î", "Ï", "Ô", "Ö", "Ù", "Û", "Ü", "Ç", " "]

def wiki_text(titre, lang= "fr", intro_seule = False):
    """Télécharge le texte brut d'un article Wikipédia et le filtre sur SATES.

    ``intro_seule=1`` demande à l'API de ne renvoyer que l'introduction.
    """
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

    # L'API renvoie un dictionnaire de pages indexé par identifiant :
    # next(iter(...)) prend la première (et généralement unique) page.
    page = next(iter(resp.json()["query"]["pages"].values()))
    
    # On passe en majuscules, on remplace les sauts de ligne par des espaces,
    # puis on supprime tout symbole hors de SATES (ponctuation, chiffres...).
    content = page.get("extract", "").replace("\n", " ").upper()
    content = ''.join(c for c in content if c in SATES)

    # Les digrammes sont découpés par paires : on ajoute un espace pour
    # tomber sur une longueur paire et ne pas perdre le dernier caractère.
    if len(content) % 2 == 1:
        content += " "

    return content

# =============== STATS ==============

def statistics(content):
    """Histogramme des caractères : total + effectif par symbole de SATES."""
    stats = {
        "global_count": len(content),
        "character_count": {char: content.count(char) for char in SATES},
        }
    return stats

def display_stats(stats, largeur=50):
    """Affiche l'histogramme sous forme de barres ASCII (#)."""
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
    """Compte les paires de caractères consécutives (digrammes).

    ``largeur=2`` découpe le texte en segments de 2 : "ABCDE" -> AB, CD, E.
    """
    content_length = len(content)
    diagram_stats = {}
    
    for index in range(0, content_length, largeur):
        segment = content[index:index + largeur]
        # Expression équivalente à un "get(segment, 0) + 1".
        diagram_stats[segment] = diagram_stats[segment] + 1 if segment in diagram_stats else 1

    return diagram_stats


def display_digrams(diagrams, top=20000, largeur=50):
    """Affiche les digrammes les plus fréquents (top par défaut très large)."""
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
    """Matrice de probabilités de transition P(suivant | courant), 42×42.

    Chaque ligne correspond à un symbole courant, chaque colonne au symbole
    suivant. On compte les occurrences de chaque digramme, puis on divise
    chaque case par le total de sa ligne pour obtenir une distribution.
    """
    matrix = []

    # Initialisation d'une matrice 42×42 remplie de zéros.
    

    for x in range(len(SATES)):
        matrix.append([])
        for y in range(len(SATES)):
            matrix[x].append(0)

    # Remplissage : le digramme "AB" incrémente matrix[index(A)][index(B)].
    for segment in digram_stats:
        x = SATES.index(segment[0])
        y = SATES.index(segment[1])
        matrix[x][y] += digram_stats[segment]

    # Normalisation par ligne (somme = 1). Une ligne vide reste à 0.
    

    for x in range(len(SATES)):
        ligne_total = sum(matrix[x])
        for y in range(len(SATES)):
            matrix[x][y] = matrix[x][y] / ligne_total if ligne_total > 0 else matrix[x][y] / 1

    # Remarque théorique : certains états n'ont aucune transition sortante.
    # La chaîne n'est donc pas irréductible sur les 42 états, seulement sur
    # sa classe récurrente (~22 états) : voir la note en fin de fichier.
    
    return matrix

def display_matrix(matrix, decimales=2):
    """Affiche la matrice en tableau textuel (ligne = courant, colonne = suivant)."""
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
    """Génère du texte en tirant le symbole suivant selon la ligne courante.

    On démarre d'un espace. À chaque étape, ``random.choices`` tire un
    symbole de SATES avec les poids de la ligne correspondante.
    """
    import random

    text = ""
    current_char = " "
    for _ in range(longueur):
        x = SATES.index(current_char)
        next_char = random.choices(SATES, weights=matrix[x])[0]
        text += next_char
        current_char = next_char

    return text

# ============= DÉMONSTRATION =============
# Ce bloc s'exécute à chaque lancement du script.
content = wiki_text("Paris", "fr", False)
print(content)
print("\n==================\n")
display_stats(statistics(content))
print("\n==================\n")
display_digrams(digram_stats(content))
print("\n==================\n")
display_matrix(markov_matrix(digram_stats(content)))
print("\n==================\n")
print(text_generator(markov_matrix(digram_stats(content)), 2000))

"""
non irréductible, apériodique sur sa classe récurrente, et une seule loi stationnaire, portée par 22 états sur 27.
"""
