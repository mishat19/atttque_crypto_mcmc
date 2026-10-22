import random


def muter_lettres(cle):
    """Échange deux lettres chiffrées prises au hasard dans la clé.

    La clé est une chaîne de 26 lettres (clé de déchiffrement).  La proposition
    est symétrique : échanger i et j a la même probabilité que échanger j et i.
    """
    i, j = random.sample(range(len(cle)), 2)
    lettres = list(cle)
    lettres[i], lettres[j] = lettres[j], lettres[i]
    return "".join(lettres)


def deplacer_bloc(cle, longueur_bloc, i, d):
    """Retire ``cle[i:i+longueur_bloc]`` et le réinsère à l'indice ``d``.

    Fonction déterministe utilisée par ``muter_positions`` et par les tests :
    elle permet de vérifier que le déplacement ``(i, L, d)`` a bien pour
    réciproque ``(d, L, i)``.
    """
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
    """Déplace un sous-bloc de la permutation à une autre position.

    On choisit une longueur de bloc L, un début i et une destination d, puis on
    retire ``cle[i:i+L]`` et on le réinsère à l'indice ``d`` du reste.

    La proposition est symétrique : l'inverse du déplacement ``(i, L, d)`` est
    ``(d, L, i)``.  C'est ce qui permet d'utiliser le rapport d'acceptation
    ``S(k') / S(k)`` sans correction de Hastings.

    Le cas ``i == d`` est un déplacement identitaire : il laisse la clé
    inchangée et garantit une auto-transition de probabilité strictement
    positive (donc l'apériodicité).
    """
    n = len(cle)
    if n < 2:
        raise ValueError("Une permutation de positions doit avoir au moins 2 éléments.")

    longueur_bloc = random.randint(1, n - 1)
    i = random.randint(0, n - longueur_bloc)
    d = random.randint(0, n - longueur_bloc)
    return deplacer_bloc(cle, longueur_bloc, i, d)


# Ancien nom conservé pour les scripts existants.
muter = muter_lettres
