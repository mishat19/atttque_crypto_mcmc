import random


def muter(cle):
    # k' = k avec 2 lettres prises au hasard échangées
    i, j = random.sample(range(len(cle)), 2)
    lettres = list(cle)
    lettres[i], lettres[j] = lettres[j], lettres[i]
    return "".join(lettres)