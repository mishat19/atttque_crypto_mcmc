import random


def muter_lettres(cle):
    """Échange deux lettres prises au hasard dans la clé (proposition symétrique)."""
    i, j = random.sample(range(len(cle)), 2)
    lettres = list(cle)
    lettres[i], lettres[j] = lettres[j], lettres[i]
    return "".join(lettres)


def deplacer_bloc(cle, longueur_bloc, i, d):
    """Retire cle[i:i+longueur_bloc] et le réinsère à l'indice d."""
    n = len(cle)
    if not 1 <= longueur_bloc <= n - 1:
        raise ValueError("La longueur du bloc doit être dans 1..n-1.")
    if not 0 <= i <= n - longueur_bloc:
        raise ValueError("Indice de départ invalide.")
    if not 0 <= d <= n - longueur_bloc:
        raise ValueError("Indice d'arrivée invalide.")

    bloc = cle[i:i + longueur_bloc]
    reste = cle[:i] + cle[i + longueur_bloc:]
    return tuple(reste[:d] + bloc + reste[d:])


def muter_positions(cle):
    """Déplace un sous-bloc de longueur L de la position i vers la position d.

    Symétrique : (i, L, d) est annulé par (d, L, i).
    Le cas i == d laisse la clé inchangée (apériodicité).
    """
    n = len(cle)
    if n < 2:
        raise ValueError("Une permutation de positions doit avoir au moins 2 éléments.")

    longueur_bloc = random.randint(1, n - 1)
    i = random.randint(0, n - longueur_bloc)
    d = random.randint(0, n - longueur_bloc)
    return deplacer_bloc(cle, longueur_bloc, i, d)
