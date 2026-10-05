import math

from utils.initialisation import cle_heuristique
from utils.mutation import muter
from utils.score import calculer_score, construire_r, lire_texte
from utils.selection import accepter
from utils.substitution import dechiffrer

CHEMIN_REFERENCE = "reference.txt"  # gros texte français
CHEMIN_CHIFFRE = "chiffre.txt"      # texte à décrypter
N_ITERATIONS = 20000
N_PROPOSITIONS = 5
# +--------------------------------------------+
# |   ____      _    ____  ____  _____ _       |
# |  |  _ \    / \  |  _ \|  _ \| ____| |      |
# |  | |_) |  / _ \ | |_) | |_) |  _| | |      |
# |  |  _ <  / ___ \|  __/|  __/| |___| |___   |
# |  |_| \_\/_/   \_\_|   |_|   |_____|_____|  |
# |                                            |
# |  Demander au prof sur quel critère garder  |
# |  les meilleures clés                       |
# +--------------------------------------------+

def mcmc(texte_chiffre, cle_initiale, r, n_iterations):
    """Renvoie {clé: S(k)} pour toutes les clés acceptées pendant la marche."""
    cle = cle_initiale
    s = calculer_score(texte_chiffre, cle, r, dechiffrer)
    visitees = {cle: s}

    for _ in range(n_iterations):
        cle_prime = muter(cle)                                          # Mutation
        s_prime = calculer_score(texte_chiffre, cle_prime, r, dechiffrer)
        if accepter(s, s_prime):                                        # Sélection
            cle, s = cle_prime, s_prime
            visitees[cle] = s

    return visitees


def meilleures_cles(visitees, n):
    """Les n clés de plus haut score """
    return sorted(visitees.items(), key=lambda item: item[1], reverse=True)[:n]


def afficher_propositions(propositions, chiffre):
    """Affiche chaque clé proposée et le début du texte qu'elle donne."""
    for numero, (cle, s) in enumerate(propositions, start=1):
        log_s = math.log(s)  # S(k) est trop grand pour être affiché tel quel
        print(f"Proposition {numero}  (log S = {log_s:.1f})")
        print(f"  clé   : {cle}")
        print(f"  texte : {dechiffrer(chiffre, cle)[:70]}")
        print()
 
# +--------------------------------------------+
# |   ____      _    ____  ____  _____ _       |
# |  |  _ \    / \  |  _ \|  _ \| ____| |      |
# |  | |_) |  / _ \ | |_) | |_) |  _| | |      |
# |  |  _ <  / ___ \|  __/|  __/| |___| |___   |
# |  |_| \_\/_/   \_\_|   |_|   |_____|_____|  |
# |                                            |
# |  Demander au prof sur quel critère garder  |
# |  les meilleures clés                       |
# +--------------------------------------------+

 
def main():
    # 1. Lecture des textes
    reference = lire_texte(CHEMIN_REFERENCE)
    chiffre = lire_texte(CHEMIN_CHIFFRE)
 
    # 2. Statistiques du français
    r = construire_r(reference)
 
    # 3. Clé de départ
    k0 = cle_heuristique(chiffre, reference)
 
    # 4. Marche MCMC
    visitees = mcmc(chiffre, k0, r, N_ITERATIONS)
 
    # 5. L'humain choisit parmi les meilleures clés
    propositions = meilleures_cles(visitees, N_PROPOSITIONS)
    afficher_propositions(propositions, chiffre)
 
 
if __name__ == "__main__":
    main()