"""Recherche récursive par nom, en tâche de fond et annulable."""

import fnmatch
import os
import threading
import time
import unicodedata


def normaliser(texte):
    """Minuscules sans accents : « Été » trouve « ete »."""
    decompose = unicodedata.normalize("NFD", texte.casefold())
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def correspondance(motif):
    """Fonction nom -> bool. Jokers * ? [ ] acceptés, sinon recherche de sous-chaîne.
    Plusieurs mots : tous doivent apparaître."""
    m = normaliser(motif.strip())
    if any(c in m for c in "*?["):
        return lambda nom: fnmatch.fnmatchcase(normaliser(nom), m)
    mots = m.split()
    return lambda nom: all(x in normaliser(nom) for x in mots)


def rechercher(racine, motif, annule=None, caches=False, limite=5000):
    """Générateur des chemins correspondant à « motif » sous « racine » (parcours en largeur,
    les liens symboliques vers des dossiers ne sont pas suivis)."""
    test = correspondance(motif)
    if not motif.strip():
        return
    file_ = [racine]
    trouves = 0
    while file_:
        if annule is not None and annule.is_set():
            return
        dossier = file_.pop(0)
        try:
            it = os.scandir(dossier)
        except OSError:
            continue
        with it:
            entrees = sorted(it, key=lambda e: e.name.casefold())
        sous = []
        for e in entrees:
            if annule is not None and annule.is_set():
                return
            if not caches and e.name.startswith("."):
                continue
            if test(e.name):
                yield e.path
                trouves += 1
                if trouves >= limite:
                    return
            try:
                if e.is_dir(follow_symlinks=False):
                    sous.append(e.path)
            except OSError:
                pass
        file_.extend(sous)


class Recherche:
    """Exécute « rechercher » dans un thread ; « lot(chemins) » reçoit les résultats par
    paquets, « fin(annulee) » à la fin. Les rappels sont appelés depuis le thread."""

    def __init__(self, racine, motif, lot, fin, caches=False):
        self.annule = threading.Event()
        self._args = (racine, motif, lot, fin, caches)
        self.thread = threading.Thread(target=self._travail, daemon=True, name="recherche")

    def demarrer(self):
        self.thread.start()
        return self

    def annuler(self):
        self.annule.set()

    def _travail(self):
        racine, motif, lot, fin, caches = self._args
        paquet = []
        dernier = time.monotonic()
        for chemin in rechercher(racine, motif, self.annule, caches):
            paquet.append(chemin)
            if time.monotonic() - dernier > 0.15 or len(paquet) >= 200:
                lot(paquet)
                paquet = []
                dernier = time.monotonic()
        if paquet and not self.annule.is_set():
            lot(paquet)
        fin(self.annule.is_set())
