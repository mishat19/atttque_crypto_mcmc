import math
import random


def accepter_log(log_score_k, log_score_k_prime):
    """Accepte si log U < log S(k') - log S(k), équivalent à U < S(k') / S(k)."""
    delta = log_score_k_prime - log_score_k
    if delta >= 0:
        return True

    u = random.random()
    if u == 0.0:
        return True
    return math.log(u) < delta
