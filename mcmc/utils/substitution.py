"""Déchiffrement par substitution (à remplacer par ta fonction de la partie 1.3).

Clé de déchiffrement : cle[i] = lettre claire de la lettre chiffrée LETTRES[i].
"""
import string

LETTRES = string.ascii_uppercase


def dechiffrer(texte, cle):
    """Remplace chaque lettre chiffrée par sa lettre claire ; l'espace reste inchangé."""
    correspondance = dict(zip(LETTRES, cle)) 
    return "".join(correspondance.get(c, c) for c in texte)