"""Permutation de position combinée au chiffrement de Vigenère.

La clé est un mot ("LEMON"). Elle joue deux rôles à la fois :

1. substitution : chaque lettre de la clé est le décalage appliqué par
   Vigenère à la position correspondante du bloc ;
2. permutation : les positions des caractères sont réordonnées par blocs de la
   longueur de la clé, selon le classement des lettres de la clé. Pour "LEMON",
   les positions sont classées L < E < M < O < N : le caractère de la colonne 2
   part donc en tête de bloc.

La substitution utilise le Vigenère positionnel
(chiffrements.chiffrement_vigenere.chiffre_vigenere_positions) : la clé se
répète tous les L caractères, espaces compris. C'est nécessaire ici, sinon le
décalage dépendrait du nombre de lettres déjà vues et une permutation de
position n'aurait plus de position fixe à permuter.

Quatre opérations sont fournies.

1. Clé : définir une clé (mot normalisé et permutation induite) et vérifier
   qu'elle est exploitable.

2. Chiffrement : appliquer cette clé à un texte clair pour obtenir un
   cryptogramme.

3. Clé inverse : construire l'inverse de cette clé (décalages opposés et
   permutation réciproque) quand elle est connue.

4. Déchiffrement : déchiffrer un texte chiffré avec une clé connue.

Le chiffrement se fait dans cet ordre : Vigenère puis permutation. Le
déchiffrement fait l'inverse.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chiffrements.chiffrement_cesar import ALPHABET
from chiffrements.chiffrement_vigenere import (
    chiffre_vigenere_positions,
    cle_inverse_vigenere,
    dechiffre_vigenere_positions,
)


# =============== 1. CLÉ ===============

def _normaliser(mot_cle):
    """Minuscules mises, espaces retirés : la clé ne garde que ses lettres."""
    if not isinstance(mot_cle, str):
        raise ValueError("La clé doit être un mot.")
    return "".join(mot_cle.upper().split())


def _permutation_depuis(mot):
    """Position d'arrivée, dans un bloc, du caractère placé à la position i.

    Les positions sont classées par ordre croissant de leur lettre de clé (les
    égalités sont tranchées par l'indice), puis chaque position reçoit son rang.
    Le résultat est donc toujours une bijection de range(longueur).
    """
    longueur = len(mot)
    permutation = [0] * longueur
    for rang, position in enumerate(sorted(range(longueur), key=lambda i: (mot[i], i))):
        permutation[position] = rang
    return permutation


def verifier_cle(cle) -> bool:
    """Vrai si la clé est exploitable.

    Accepte soit un mot, soit une clé déjà construite par definir_cle. Pour un
    mot : non vide et uniquement formé de lettres. Pour une clé : longueur
    cohérente et permutation bien une bijection, donc réversible.
    """
    if isinstance(cle, dict):
        longueur = cle.get("longueur")
        permutation = cle.get("permutation")
        if not isinstance(longueur, int) or not isinstance(permutation, list):
            return False
        if len(permutation) != longueur or longueur <= 0:
            return False
        return sorted(permutation) == list(range(longueur))

    mot = _normaliser(cle)
    return bool(mot) and all(c in ALPHABET for c in mot)


def definir_cle(mot_cle) -> dict:
    """Définit la clé de chiffrement à partir d'un mot.

    Attention aux clés faibles : un mot dont les lettres sont déjà en ordre
    alphabétique (ZZZZ, AAAA...) donne une permutation identité, donc aucune
    permutation de position.
    """
    mot = _normaliser(mot_cle)
    if not verifier_cle(mot):
        raise ValueError("La clé doit être un mot non vide uniquement formé de lettres.")
    return {"mot": mot, "longueur": len(mot), "permutation": _permutation_depuis(mot)}


def cle_inverse(cle) -> dict:
    """Construit l'inverse de la clé connue.

    L'inverse de la permutation s'obtient en échangeant départ et arrivée ;
    l'inverse de la substitution Vigenère remplace chaque lettre par son
    décalage opposé.

    Chaque couche est donc inversée séparément, mais le déchiffrement les
    applique dans l'ordre inverse (permutation d'abord, Vigenère ensuite) : les
    deux couches ne commutent pas, la clé inverse n'est donc pas simplement
    "la même opération avec la clé inverse".
    """
    cle = _exiger(cle)
    reciproque = [0] * cle["longueur"]
    for depart, arrivee in enumerate(cle["permutation"]):
        reciproque[arrivee] = depart

    return {
        "mot": cle_inverse_vigenere(cle["mot"]),
        "longueur": cle["longueur"],
        "permutation": reciproque,
    }


def _exiger(cle) -> dict:
    """Valide une clé et la renvoie toujours sous forme de dictionnaire."""
    if not verifier_cle(cle):
        raise ValueError("Clé invalide : mot non vide de lettres, permutation bijective.")
    return cle if isinstance(cle, dict) else definir_cle(cle)


# =============== PERMUTATION DE POSITION ===============

def _ordre(permutation, taille):
    """Ordre de lecture des sources dans un bloc de `taille` positions.

    Pour `taille` égale à la longueur de la clé, la source de rang k est celle
    qui arrive en position k.
    """
    return sorted(range(taille), key=lambda i: (permutation[i], i))


def _rang(permutation, taille):
    """Réciproque de _ordre sur un bloc de `taille` positions."""
    rang = [0] * taille
    for position, source in enumerate(_ordre(permutation, taille)):
        rang[source] = position
    return rang


def _permuter(texte, permutation, dechiffrer=False):
    """Réordonne les positions de `texte` bloc par bloc.

    Chaque bloc fait la longueur de la clé. Un dernier bloc plus court est
    réordonné sur lui-même, la permutation reste donc réversible.
    """
    longueur = len(permutation)
    resultat = []

    for debut in range(0, len(texte), longueur):
        bloc = texte[debut:debut + longueur]
        ordre = _rang(permutation, len(bloc)) if dechiffrer else _ordre(permutation, len(bloc))
        resultat.append("".join(bloc[i] for i in ordre))

    return "".join(resultat)


# =============== 2. ET 4. CHIFFREMENT / DÉCHIFFREMENT ===============

def chiffre_cryptogramme(texte_clair, cle) -> str:
    """Applique la clé (Vigenère positionnel puis permutation) pour produire un cryptogramme."""
    cle = _exiger(cle)
    return _permuter(chiffre_vigenere_positions(texte_clair, cle["mot"]), cle["permutation"])


def dechiffre_cryptogramme(cryptogramme, cle) -> str:
    """Retrouve le texte clair d'un cryptogramme avec une clé connue."""
    cle = _exiger(cle)
    return dechiffre_vigenere_positions(
        _permuter(cryptogramme, cle["permutation"], dechiffrer=True),
        cle["mot"],
    )


# =============== POURQUOI EST-CE DIFFICILE À ATTAQUER ? ===============
#
# Réponse courte : beaucoup moins qu'on ne le croit. La permutation dérange la
# positions, mais elle ne résiste pas à l'attaque fréquentielle.
#
# 1. Ce que la permutation fait vraiment. Elle déplace les caractères sans les
#    changer, donc elle conserve l'histogramme. Et comme elle envoie toute une
#    colonne du Vigenère vers une seule colonne destination, chaque colonne du
#    cryptogramme porte encore un décalage unique : chaque colonne reste un
#    César à part entière, atacable par sa distribution de lettres.
#    (chiffrements.attaque_frequentielle.attaque_frequentielle_colonnes fait
#    exactement cela et retrouve les L décalages de la clé.)
#
# 2. Ce que la permutation coûte vraiment à l'adversaire.
#    - Kasiski : les trigrammes répétés ne réapparaissent plus à un multiple de
#      L, la période ne se lit donc plus par les distances.
#    - L'ordre des colonnes : les colonnes du cryptogramme ne sont plus les
#      colonnes du clair dans l'ordre. Les décalages sont retrouvés, mais rangés
#      par colonne destination : on obtient les bonnes lettres, pas à leur
#      place. Il reste L! façon de les remettre, et le mot clé n'est pas lisible
#      tant que ce couplage n'est pas résolu.
#    - Les statistiques de Markov du texte : la permutation mélange les positions
#      voisines, donc deux caractères voisins du cryptogramme n'ont plus aucun
#      lien dans le clair, et la vraisemblance ne peut classer les L! candidats
#      de permutation qu'après coup.
#
# 3. Ce que la permutation ne coûte pas. Retrouver le contenu des colonnes coûte
#    26 hypothèses par colonne, soit 26L au total : aucune explosion
#    factorielle. Le L! n'est un obstacle que pour qui exige le mot clé ou le
#    texte remis en ordre, pas pour qui veut juste les lettres.
#
# 4. Mesure de L. L'indice de coïncidence est invariant par permutation, donc il
#    continue de révéler L, exactement comme pour un Vigenère ordinaire.
#
# Conclusion : l'association n'apporte presque aucune sécurité au-delà du
# Vigenère seul. Ce qu'elle cache est l'ordre (la clé et les positions), pas la
# substitution. Une clé longue et secrète reste la seule vraie protection, et le
# chiffrement cède dès que le texte est assez long pour que chaque colonne ait
# quelques centaines de lettres.


# if __name__ == "__main__":
#     message = "UN TEXTE ASSEZ LONG POUR OBSERVER LA PERMUTATION DES POSITIONS"
#     cle = definir_cle("LEMON")
#     crypto = chiffre_cryptogramme(message, cle)
#     print("Mot cle     :", "LEMON")
#     print("Cle        :", cle)
#     print("Cle inverse:", cle_inverse(cle))
#     print("Clair      :", message)
#     print("Cryptogramme:", crypto)
#     print("Dechiffre  :", dechiffre_cryptogramme(crypto, cle))