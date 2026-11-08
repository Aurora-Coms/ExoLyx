"""Lecteurs : lecture de /proc/mounts et de « lsblk -J », montage via udisksctl."""

import json
import os
import re
import subprocess

COLONNES_LSBLK = "NAME,PATH,LABEL,SIZE,FSTYPE,MOUNTPOINTS,RM,HOTPLUG,TYPE,UUID,MODEL"

# Systèmes de fichiers sans intérêt pour l'utilisateur
FS_IGNORES = {"swap", "squashfs", "crypto_LUKS", "LVM2_member", "linux_raid_member", "iso9660_hidden", None, ""}
MONTAGES_IGNORES = ("/boot", "/efi", "/snap", "/var/lib/snapd", "/opt")


def decoder_montage(texte):
    """/proc/mounts encode espaces & co en octal (\\040)."""
    return re.sub(rb"\\([0-7]{3})", lambda m: bytes([int(m.group(1), 8)]),
                  texte.encode("utf-8", "surrogateescape")).decode("utf-8", "replace")


def analyser_mounts(texte):
    """Liste de dicts {peripherique, montage, fstype, options} depuis /proc/mounts."""
    resultat = []
    for ligne in texte.splitlines():
        champs = ligne.split()
        if len(champs) < 4:
            continue
        resultat.append({
            "peripherique": decoder_montage(champs[0]),
            "montage": decoder_montage(champs[1]),
            "fstype": champs[2],
            "options": champs[3].split(","),
        })
    return resultat


def lire_mounts():
    try:
        with open("/proc/mounts", encoding="utf-8", errors="surrogateescape") as f:
            return analyser_mounts(f.read())
    except OSError:
        return []


def points_de_montage():
    return [m["montage"] for m in lire_mounts()]


def format_taille_disque(octets):
    from modele import format_taille
    return format_taille(octets)


def _a_plat(peripheriques, parent=None):
    for p in peripheriques or []:
        p = dict(p)
        p["_parent"] = parent
        yield p
        yield from _a_plat(p.get("children"), p)


def analyser_lsblk(texte_json, montages=None):
    """Transforme la sortie de « lsblk -J -b -o … » en liste de lecteurs affichables.

    Chaque lecteur : nom, peripherique, montage ('' si non monté), fstype, taille,
    amovible, uuid. Accepte « mountpoints » (util-linux ≥ 2.37) ou « mountpoint »."""
    try:
        donnees = json.loads(texte_json)
    except (ValueError, TypeError):
        return []
    par_peripherique = {}
    fs_montes = {}
    for m in montages or []:
        par_peripherique.setdefault(m["peripherique"], []).append(m["montage"])
        fs_montes.setdefault(m["peripherique"], m["fstype"])
    lecteurs = []
    for p in _a_plat(donnees.get("blockdevices")):
        if p.get("type") == "loop":
            continue
        chemin = p.get("path") or ("/dev/" + p.get("name", ""))
        # lsblk sans udev ne connaît pas toujours le type : /proc/mounts complète
        fstype = p.get("fstype") or fs_montes.get(chemin)
        if fstype in FS_IGNORES:
            continue
        points = p.get("mountpoints")
        if points is None:
            points = [p.get("mountpoint")]
        points = [x for x in points if x]
        points += [x for x in par_peripherique.get(chemin, []) if x not in points]
        montage = ""
        if points:
            # « / » en priorité, sinon le plus court (sous-volumes btrfs)
            montage = "/" if "/" in points else sorted(points, key=len)[0]
        if montage == "[SWAP]" or any(montage == x or montage.startswith(x + "/") for x in MONTAGES_IGNORES):
            continue
        parent = p.get("_parent") or {}
        taille = p.get("size") or 0
        try:
            taille = int(taille)
        except (TypeError, ValueError):
            taille = 0
        amovible = bool(p.get("rm") or p.get("hotplug") or parent.get("rm") or parent.get("hotplug"))
        if montage == "/":
            nom = "Système"
        elif p.get("label"):
            nom = p["label"]
        else:
            modele = (parent.get("model") or p.get("model") or "").strip()
            nom = f"{modele or 'Volume'} {format_taille_disque(taille)}".strip()
        lecteurs.append({
            "nom": nom,
            "peripherique": chemin,
            "montage": montage,
            "fstype": fstype,
            "taille": taille,
            "amovible": amovible,
            "uuid": p.get("uuid") or "",
        })
    # Système d'abord, puis internes, puis amovibles
    lecteurs.sort(key=lambda l: (l["montage"] != "/", l["amovible"], l["nom"].lower()))
    return lecteurs


def espace(montage):
    """(total, libre) en octets, ou (0, 0)."""
    try:
        st = os.statvfs(montage)
    except OSError:
        return 0, 0
    return st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize


def lister():
    """Lecteurs du système, enrichis de l'espace disque pour ceux qui sont montés."""
    montages = lire_mounts()
    try:
        sortie = subprocess.run(["lsblk", "-J", "-b", "-o", COLONNES_LSBLK],
                                capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        sortie = ""
    lecteurs = analyser_lsblk(sortie, montages)
    if not lecteurs:
        # Pas de lsblk exploitable : on se rabat sur la racine
        lecteurs = [{"nom": "Système", "peripherique": "", "montage": "/", "fstype": "",
                     "taille": 0, "amovible": False, "uuid": ""}]
    for l in lecteurs:
        total, libre = espace(l["montage"]) if l["montage"] else (0, 0)
        l["total"] = total or l["taille"]
        l["libre"] = libre
        l["utilise"] = (total - libre) if total else 0
    return lecteurs


def analyser_sortie_montage(texte):
    """« Mounted /dev/sdb1 at /run/media/moi/CLE » -> « /run/media/moi/CLE »."""
    m = re.search(r"\bat (.+?)\.?\s*$", texte.strip())
    return m.group(1) if m else ""
