import math
import random


def accepter(score_k, score_k_prime):
    """Acceptation de Metropolis avec les scores bruts.

    Conservé pour compatibilité ; le MCMC utilise ``accepter_log`` pour éviter
    les rapports de très grands entiers.
    """
    if score_k_prime >= score_k:
        return True
    u = random.random()
    if u == 0.0:
        return True
    return u < (score_k_prime / score_k)


def accepter_log(log_score_k, log_score_k_prime):
    """Acceptation de Metropolis en logarithme.

    On accepte si ``log U < log S(k') - log S(k)``, ce qui est équivalent à
    ``U < S(k') / S(k)`` avec U uniforme dans ]0 ; 1[.
    """
    delta = log_score_k_prime - log_score_k
    if delta >= 0:
        return True

    u = random.random()
    if u == 0.0:  # événement de probabilité 2^-53 : autant accepter
        return True
    return math.log(u) < delta
