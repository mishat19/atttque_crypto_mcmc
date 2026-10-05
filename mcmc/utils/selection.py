import random


def accepter(score_k, score_k_prime):
    # Renvoie True si k' remplace k.
    if score_k_prime >= score_k:
        return True
    u = random.random()
    return u < (score_k_prime / score_k)