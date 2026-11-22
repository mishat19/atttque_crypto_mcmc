"""Opérateurs de mutation (propositions de nouvelles clés) pour le MCMC.

Une mutation doit vérifier deux propriétés :
1. elle conserve le domaine des clés (une permutation reste une permutation) ;
2. elle est *symétrique* : si k' peut être proposé depuis k, alors k peut
   être proposé depuis k' avec la même probabilité. C'est ce qui garantit
   que la chaîne converge vers la loi π(k) ∝ S(k) avec l'acceptation de
   Metropolis simple (sans facteur de correction de Hastings).
"""

import random


def muter_lettres(cle):
    """Échange deux lettres prises au hasard dans la clé (proposition symétrique).

    ``random.sample`` tire deux indices distincts. Échanger i et j est une
    opération involutive : la même mutation peut revenir à la clé initiale,
    donc la probabilité de proposition est la même dans les deux sens.

    Les transpositions engendrent toutes les permutations des 26 lettres :
    la chaîne est donc irréductible (aucune clé n'est inaccessible).
    """
    i, j = random.sample(range(len(cle)), 2)
    lettres = list(cle)
    lettres[i], lettres[j] = lettres[j], lettres[i]
    return "".join(lettres)


def deplacer_bloc(cle, longueur_bloc, i, d):
    """Retire cle[i:i+longueur_bloc] et le réinsère à l'indice d.

    Exemple : cle = (0,1,2,3,4), bloc de 2 à i=1 -> (0,3,4),
    réinsertion à d=3 -> (0,3,4,1,2). L'opération est une permutation des
    éléments : aucune valeur n'est perdue ni dupliquée.

    Les trois contrôles garantissent que le bloc existe et que la destination
    reste dans le tableau après le retrait du bloc.
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
    """Déplace un sous-bloc de longueur L de la position i vers la position d.

    Symétrique : (i, L, d) est annulé par (d, L, i).
    Le cas i == d laisse la clé inchangée (apériodicité).

    Pourquoi l'apériodicité ? Une chaîne qui peut rester dans son état
    courant avec une probabilité > 0 ne peut pas être piégée dans un cycle.
    Ici, i et d sont tirés uniformément, donc P(i == d) = 1/(n-L+1) > 0.

    En prenant L = 1, on obtient le déplacement d'un seul élément ; ces
    déplacements engendrent toutes les permutations de ℓ éléments, donc la
    chaîne est irréductible sur les ℓ! clés possibles.
    """
    n = len(cle)
    if n < 2:
        raise ValueError("Une permutation de positions doit avoir au moins 2 éléments.")

    longueur_bloc = random.randint(1, n - 1)
    i = random.randint(0, n - longueur_bloc)
    d = random.randint(0, n - longueur_bloc)
    return deplacer_bloc(cle, longueur_bloc, i, d)
