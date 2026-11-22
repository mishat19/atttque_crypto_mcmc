"""Règle d'acceptation de Metropolis (sélection des états).

C'est le cœur probabiliste de l'attaque : on accepte toujours une clé
meilleure, et parfois une moins bonne pour ne pas rester coincé dans un
maximum local.
"""

import math
import random


def accepter_log(log_score_k, log_score_k_prime):
    """Accepte si log U < log S(k') - log S(k), équivalent à U < S(k') / S(k).

    On raisonne en logarithmes parce que S(k) est un produit énorme :
    - si Δ = log S(k') - log S(k) >= 0, la nouvelle clé est au moins aussi
      bonne, on l'accepte systématiquement ;
    - sinon, on l'accepte avec probabilité exp(Δ) = S(k')/S(k) < 1.
      Plus la clé proposée est mauvaise, plus Δ est négatif, plus l'acceptation
      est improbable.

    Et comme log est croissant, comparer log(U) < Δ revient à comparer
    U < exp(Δ), sans jamais calculer exp(Δ) (qui pourrait déborder).

    Le cas ``u == 0`` est traité à part : math.log(0) n'existe pas, mais
    l'inégalité 0 < exp(Δ) est toujours vraie.
    """
    delta = log_score_k_prime - log_score_k
    if delta >= 0:
        return True

    u = random.random()
    if u == 0.0:
        return True
    return math.log(u) < delta
