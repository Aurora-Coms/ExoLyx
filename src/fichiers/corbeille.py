"""Corbeille conforme à la spécification freedesktop.org (Trash 1.0).

Corbeille principale : $XDG_DATA_HOME/Trash (~/.local/share/Trash), avec files/ et
info/*.trashinfo. Sur un autre système de fichiers : $topdir/.Trash/$uid (si le
dossier existe, est collant et n'est pas un lien) sinon $topdir/.Trash-$uid.
Les étiquettes (user.xdg.tags) voyagent avec le fichier ; une copie est aussi notée
dans le .trashinfo (clé X-Exolyx-Etiquettes) pour les systèmes sans xattr.
"""

import os
import shutil
import stat
import time
import urllib.parse
from datetime import datetime

import etiquettes
import lecteurs

CLE_ETIQUETTES = "X-Exolyx-Etiquettes"


def dossier_principal():
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "Trash")


def point_de_montage(chemin):
    chemin = os.path.realpath(chemin)
    dev = os.lstat(chemin).st_dev
    while True:
        parent = os.path.dirname(chemin)
        if parent == chemin:
            return chemin
        try:
            if os.lstat(parent).st_dev != dev:
                return chemin
        except OSError:
            return chemin
        chemin = parent


def encoder_chemin(chemin):
    return urllib.parse.quote(chemin, safe="/")


def decoder_chemin(texte):
    return urllib.parse.unquote(texte)


class Corbeille:
    def __init__(self, principal=None, montages=True):
        self.principal = principal or dossier_principal()
        self.montages = montages   # False : ignorer les corbeilles des autres points de montage

    # --- emplacements ---
    def _preparer(self, racine):
        for sous in ("files", "info"):
            os.makedirs(os.path.join(racine, sous), mode=0o700, exist_ok=True)
        return racine

    def corbeilles_connues(self):
        """Toutes les corbeilles existantes : principale + celles des points de montage."""
        resultat = [self.principal]
        uid = os.getuid()
        for m in (lecteurs.points_de_montage() if self.montages else []):
            for c in (os.path.join(m, ".Trash", str(uid)), os.path.join(m, f".Trash-{uid}")):
                if os.path.isdir(os.path.join(c, "info")) and c not in resultat:
                    resultat.append(c)
        return resultat

    def corbeille_pour(self, chemin):
        """(racine de corbeille, topdir ou None pour la principale)."""
        try:
            dev_fichier = os.lstat(chemin).st_dev
            os.makedirs(self.principal, exist_ok=True)
            if os.stat(self.principal).st_dev == dev_fichier:
                return self._preparer(self.principal), None
        except OSError:
            return self._preparer(self.principal), None
        topdir = point_de_montage(os.path.dirname(os.path.abspath(chemin)) or "/")
        uid = os.getuid()
        partagee = os.path.join(topdir, ".Trash")
        try:
            st = os.lstat(partagee)
            if stat.S_ISDIR(st.st_mode) and st.st_mode & stat.S_ISVTX and not stat.S_ISLNK(st.st_mode):
                racine = os.path.join(partagee, str(uid))
                return self._preparer(racine), topdir
        except OSError:
            pass
        racine = os.path.join(topdir, f".Trash-{uid}")
        try:
            return self._preparer(racine), topdir
        except OSError:
            return self._preparer(self.principal), None

    # --- jeter ---
    def jeter(self, chemin):
        """Met « chemin » à la corbeille ; renvoie le chemin dans files/."""
        chemin = os.path.abspath(chemin)
        if not os.path.lexists(chemin):
            raise FileNotFoundError(2, "Fichier introuvable", chemin)
        racine, topdir = self.corbeille_pour(chemin)
        etq = etiquettes.lire(chemin)
        nom = os.path.basename(chemin.rstrip(os.sep))
        # Réservation atomique du nom via le .trashinfo (O_EXCL)
        base, ext = os.path.splitext(nom) if not nom.startswith(".") or nom.count(".") > 1 else (nom, "")
        n = 1
        while True:
            candidat = nom if n == 1 else f"{base}.{n}{ext}"
            info = os.path.join(racine, "info", candidat + ".trashinfo")
            try:
                fd = os.open(info, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                n += 1
                continue
            if os.path.lexists(os.path.join(racine, "files", candidat)):
                os.close(fd)
                os.unlink(info)
                n += 1
                continue
            break
        if topdir:
            enregistre = os.path.relpath(chemin, topdir)
        else:
            enregistre = chemin
        lignes = [
            "[Trash Info]",
            f"Path={encoder_chemin(enregistre)}",
            f"DeletionDate={datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        ]
        if etq:
            lignes.append(f"{CLE_ETIQUETTES}={urllib.parse.quote(','.join(etq))}")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lignes) + "\n")
        cible = os.path.join(racine, "files", candidat)
        try:
            try:
                os.rename(chemin, cible)
            except OSError:
                # dernier recours (ex. périphérique sans corbeille) : copie puis suppression
                if os.path.isdir(chemin) and not os.path.islink(chemin):
                    shutil.copytree(chemin, cible, symlinks=True)
                    shutil.rmtree(chemin)
                else:
                    shutil.copy2(chemin, cible, follow_symlinks=False)
                    os.unlink(chemin)
        except BaseException:
            os.unlink(info)
            raise
        self._invalider_taille(racine)
        return cible

    def _invalider_taille(self, racine):
        try:
            os.unlink(os.path.join(racine, "directorysizes"))
        except OSError:
            pass

    # --- lister ---
    @staticmethod
    def lire_info(chemin_info):
        donnees = {}
        try:
            with open(chemin_info, encoding="utf-8", errors="replace") as f:
                section = False
                for ligne in f:
                    ligne = ligne.strip()
                    if ligne.startswith("["):
                        section = ligne == "[Trash Info]"
                        continue
                    if section and "=" in ligne:
                        cle, _, val = ligne.partition("=")
                        donnees[cle.strip()] = val.strip()
        except OSError:
            return None
        return donnees

    def lister(self):
        """Éléments de toutes les corbeilles : dicts nom, chemin, origine, date, info, etiquettes."""
        elements = []
        for racine in self.corbeilles_connues():
            dossier_info = os.path.join(racine, "info")
            try:
                noms = os.listdir(dossier_info)
            except OSError:
                continue
            topdir = None if racine == self.principal else self._topdir_de(racine)
            for n in noms:
                if not n.endswith(".trashinfo"):
                    continue
                nom = n[: -len(".trashinfo")]
                fichier = os.path.join(racine, "files", nom)
                if not os.path.lexists(fichier):
                    continue
                d = self.lire_info(os.path.join(dossier_info, n)) or {}
                origine = decoder_chemin(d.get("Path", nom))
                if topdir and not os.path.isabs(origine):
                    origine = os.path.join(topdir, origine)
                try:
                    date = time.mktime(time.strptime(d.get("DeletionDate", ""), "%Y-%m-%dT%H:%M:%S"))
                except ValueError:
                    date = 0.0
                etq = urllib.parse.unquote(d.get(CLE_ETIQUETTES, ""))
                elements.append({
                    "nom": os.path.basename(origine) or nom,
                    "chemin": fichier,
                    "origine": origine,
                    "date": date,
                    "info": os.path.join(dossier_info, n),
                    "etiquettes": [e for e in etq.split(",") if e],
                })
        elements.sort(key=lambda e: e["date"], reverse=True)
        return elements

    @staticmethod
    def _topdir_de(racine):
        parent = os.path.dirname(racine)
        if os.path.basename(parent) == ".Trash":
            return os.path.dirname(parent)
        return parent

    def element(self, chemin_fichier):
        for e in self.lister():
            if e["chemin"] == chemin_fichier:
                return e
        return None

    def est_vide(self):
        for racine in self.corbeilles_connues():
            try:
                if any(n.endswith(".trashinfo") for n in os.listdir(os.path.join(racine, "info"))):
                    return False
            except OSError:
                pass
        return True

    # --- restaurer / supprimer ---
    def restaurer(self, chemin_fichier, destination=None):
        """Remet l'élément à son emplacement d'origine (ou « destination »).
        Si le nom est pris, un nom unique « nom (2).ext » est choisi. Renvoie le chemin restauré."""
        from operations import nom_unique
        e = self.element(chemin_fichier)
        if e is None:
            raise FileNotFoundError(2, "Élément introuvable dans la corbeille", chemin_fichier)
        cible = destination or e["origine"]
        dossier = os.path.dirname(cible)
        os.makedirs(dossier, exist_ok=True)
        cible = os.path.join(dossier, nom_unique(dossier, os.path.basename(cible)))
        try:
            os.rename(e["chemin"], cible)
        except OSError:
            if os.path.isdir(e["chemin"]) and not os.path.islink(e["chemin"]):
                shutil.copytree(e["chemin"], cible, symlinks=True)
                shutil.rmtree(e["chemin"])
            else:
                shutil.copy2(e["chemin"], cible, follow_symlinks=False)
                os.unlink(e["chemin"])
        os.unlink(e["info"])
        # Les étiquettes suivent normalement le fichier ; on les reprend du .trashinfo sinon
        if e["etiquettes"] and not etiquettes.lire(cible):
            etiquettes.ecrire(cible, e["etiquettes"])
        self._invalider_taille(os.path.dirname(os.path.dirname(e["info"])))
        return cible

    def supprimer(self, chemin_fichier):
        e = self.element(chemin_fichier)
        if e is None:
            return
        if os.path.isdir(e["chemin"]) and not os.path.islink(e["chemin"]):
            shutil.rmtree(e["chemin"], ignore_errors=True)
        else:
            os.unlink(e["chemin"])
        os.unlink(e["info"])

    def vider(self):
        for racine in self.corbeilles_connues():
            for sous in ("files", "info"):
                d = os.path.join(racine, sous)
                try:
                    noms = os.listdir(d)
                except OSError:
                    continue
                for n in noms:
                    p = os.path.join(d, n)
                    if os.path.isdir(p) and not os.path.islink(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        try:
                            os.unlink(p)
                        except OSError:
                            pass
            self._invalider_taille(racine)
