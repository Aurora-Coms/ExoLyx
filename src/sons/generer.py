#!/usr/bin/env python3
"""Synthèse du thème de sons freedesktop « ExoLyx ».

Sonorités douces et « spatiales » : cloches FM légères, accords majeurs,
enveloppes courtes, réverbération stéréo synthétique. Chaque son est
normalisé à environ -14 LUFS (BS.1770, pondération K) avec un plafond de
crête à -1 dBFS, puis encodé en Ogg Vorbis (.oga) par ffmpeg (libvorbis)
ou oggenc s'ils sont présents ; sinon les fichiers restent en WAV.

Usage : python3 generer.py [dossier_theme]      (défaut : ./ExoLyx)
Dépendance : numpy.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

FE = 48000                 # fréquence d'échantillonnage
CIBLE_LUFS = -14.0
CRETE_MAX_DB = -1.0
RNG = np.random.default_rng(20261108)   # graine fixe : générations reproductibles


def note(nom):
    """'A4' -> 440 Hz ; accepte les dièses ('F#5')."""
    noms = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    base, octave = nom[:-1], int(nom[-1])
    demi = noms[base[0]] + (1 if "#" in base else 0) - (1 if base.endswith("b") and len(base) > 1 else 0)
    return 440.0 * 2 ** ((demi + 12 * (octave - 4)) / 12)


def silence(duree):
    return np.zeros((int(duree * FE), 2))


def temps(duree):
    return np.arange(int(duree * FE)) / FE


def enveloppe(duree, attaque=0.004, decroissance=0.5, maintien=0.0):
    t = temps(duree)
    env = np.where(t < attaque, t / max(attaque, 1e-6), 1.0)
    apres = np.clip(t - attaque - maintien, 0, None)
    env = env * np.exp(-apres / decroissance)
    # fondu de sortie pour éviter tout clic
    n = min(len(t), int(0.012 * FE))
    if n:
        env[-n:] *= np.linspace(1, 0, n)
    return env


def cloche(freq, duree, decroissance=0.35, ratio=3.5, indice=1.6, brillance=0.6, pan=0.0):
    """Cloche FM légère : porteuse sinus, modulante inharmonique dont
    l'indice décroît plus vite que l'amplitude (attaque cristalline)."""
    t = temps(duree)
    env = enveloppe(duree, 0.003, decroissance)
    ind = indice * np.exp(-t / (decroissance * 0.35))
    mod = np.sin(2 * np.pi * freq * ratio * t)
    s = np.sin(2 * np.pi * freq * t + ind * mod)
    # partiel d'octave doux + léger désaccord pour le scintillement
    s += 0.28 * brillance * np.sin(2 * np.pi * freq * 2.001 * t) * np.exp(-t / (decroissance * 0.5))
    s += 0.18 * np.sin(2 * np.pi * freq * 0.5 * t) * np.exp(-t / (decroissance * 1.4))
    mono = s * env
    return panoramique(mono, pan)


def nappe(freqs, duree, attaque=0.35, decroissance=0.9, pan_large=0.6):
    """Nappe douce : sinus légèrement désaccordés gauche/droite (largeur)."""
    t = temps(duree)
    env = enveloppe(duree, attaque, decroissance, maintien=0.05)
    g = np.zeros_like(t)
    d = np.zeros_like(t)
    for i, f in enumerate(freqs):
        for det, cote in ((0.9985, 0), (1.0015, 1)):
            onde = np.sin(2 * np.pi * f * det * t + i) + 0.12 * np.sin(2 * np.pi * 2 * f * det * t)
            if cote == 0:
                g += onde
            else:
                d += onde
    m = (g + d) / 2
    g = m + pan_large * (g - m)
    d = m + pan_large * (d - m)
    return np.stack([g * env, d * env], axis=1) / max(len(freqs), 1)


def bruit_filtre(duree, f_bas, f_haut, decroissance=0.08, attaque=0.002):
    n = int(duree * FE)
    b = RNG.standard_normal(n)
    spec = np.fft.rfft(b)
    f = np.fft.rfftfreq(n, 1 / FE)
    masque = np.exp(-0.5 * ((np.log(f + 1) - np.log((f_bas * f_haut) ** 0.5)) / (0.5 * np.log(f_haut / f_bas))) ** 2)
    b = np.fft.irfft(spec * masque, n)
    b /= np.max(np.abs(b)) + 1e-9
    return b * enveloppe(duree, attaque, decroissance)


def glissando(f0, f1, duree, decroissance=0.25, pan=0.0):
    t = temps(duree)
    f = f0 * (f1 / f0) ** np.clip(t / (duree * 0.6), 0, 1)
    phase = 2 * np.pi * np.cumsum(f) / FE
    s = np.sin(phase) + 0.15 * np.sin(2 * phase)
    return panoramique(s * enveloppe(duree, 0.006, decroissance), pan)


def panoramique(mono, pan):
    a = (pan + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1) * np.sqrt(2)


def placer(total, son, debut, gain=1.0):
    i = int(debut * FE)
    j = min(len(total), i + len(son))
    total[i:j] += gain * son[: j - i]
    return total


def adoucir(x, fc=7000.0):
    """Passe-bas à un pôle (enlève l'aigreur)."""
    a = np.exp(-2 * np.pi * fc / FE)
    y = np.empty_like(x)
    acc = np.zeros(x.shape[1])
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def adoucir_rapide(x, fc=7000.0):
    """Passe-bas doux dans le domaine fréquentiel (même effet, plus rapide)."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / FE)
    h = 1 / np.sqrt(1 + (f / fc) ** 4)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * h[:, None], n, axis=0)


def reverb(x, duree=0.9, melange=0.22, predelai=0.012):
    """Réverbération « spatiale » : réponse impulsionnelle de bruit décroissant,
    décorrélée gauche/droite, assombrie avec le temps."""
    n = int(duree * FE)
    t = np.arange(n) / FE
    ri = []
    for _ in range(2):
        b = RNG.standard_normal(n) * np.exp(-t / (duree / 6.9))
        b = adoucir_rapide(b[:, None], 5000.0)[:, 0]
        b[: int(predelai * FE)] = 0
        ri.append(b / np.sqrt(np.sum(b ** 2)))
    sortie = np.zeros((len(x) + n, 2))
    for c in range(2):
        m = len(x) + n
        taille = 1 << (m - 1).bit_length()
        conv = np.fft.irfft(np.fft.rfft(x[:, c], taille) * np.fft.rfft(ri[c], taille), taille)[:m]
        sortie[:, c] = conv
    sec = np.zeros_like(sortie)
    sec[: len(x)] = x
    return (1 - melange) * sec + melange * sortie * 1.4


def couper(x, duree_max):
    n = int(duree_max * FE)
    x = x[:n].copy()
    # supprime la traîne inaudible puis fondu final
    niveau = np.max(np.abs(x), axis=1)
    seuil = np.max(niveau) * 10 ** (-60 / 20)
    actifs = np.nonzero(niveau > seuil)[0]
    fin = min(len(x), (actifs[-1] + 1) if len(actifs) else len(x))
    x = x[:fin]
    f = min(len(x), int(0.03 * FE))
    x[-f:] *= np.linspace(1, 0, f)[:, None]
    return x


# --------------------------------------------------------------------------
# Mesure de sonie BS.1770-4 (pondération K, portes absolue et relative)
# --------------------------------------------------------------------------
def biquad(x, b, a):
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        v = b[0] * x[i] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1 = x1, x[i]
        y2, y1 = y1, v
        y[i] = v
    return y


def ponderation_k(canal):
    # coefficients BS.1770 pour 48 kHz
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    try:
        from scipy.signal import lfilter  # optionnel, plus rapide
        return lfilter(b2, a2, lfilter(b1, a1, canal))
    except ImportError:
        return biquad(biquad(canal, b1, a1), b2, a2)


def lufs(x):
    k = np.stack([ponderation_k(x[:, c]) for c in range(x.shape[1])], axis=1)
    bloc, pas = int(0.4 * FE), int(0.1 * FE)
    if len(k) < bloc:
        # son plus court qu'un bloc : sonie de sa partie active
        z = np.mean(np.sum(k ** 2, axis=1))
        return -0.691 + 10 * np.log10(z + 1e-12)
    zs = np.array([np.sum(np.mean(k[i:i + bloc] ** 2, axis=0)) for i in range(0, len(k) - bloc + 1, pas)])
    l = -0.691 + 10 * np.log10(zs + 1e-12)
    zs = zs[l > -70]
    if not len(zs):
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(zs)) - 10
    l = -0.691 + 10 * np.log10(zs)
    return -0.691 + 10 * np.log10(np.mean(zs[l > rel]))


def crete_vraie(x):
    """Crête estimée avec suréchantillonnage ×4 (domaine fréquentiel)."""
    n = len(x)
    spec = np.fft.rfft(x, axis=0)
    sur = np.fft.irfft(spec, 4 * n, axis=0) * 4
    return float(np.max(np.abs(sur)))


def normaliser(x):
    x = x - np.mean(x, axis=0)
    gain = 10 ** ((CIBLE_LUFS - lufs(x)) / 20)
    x = x * gain
    crete = crete_vraie(x)
    plafond = 10 ** (CRETE_MAX_DB / 20)
    if crete > plafond:
        x *= plafond / crete
    return x


# --------------------------------------------------------------------------
# Les sons
# --------------------------------------------------------------------------
def s_service_login():
    """Démarrage (≤ 2,5 s) : nappe de do majeur qui s'ouvre + arpège de cloches montant."""
    tot = silence(2.6)
    placer(tot, nappe([note("C4"), note("G4"), note("E5")], 2.3, attaque=0.45, decroissance=0.7), 0.0, 0.55)
    for i, (n, pan) in enumerate((("C5", -0.5), ("E5", -0.2), ("G5", 0.2), ("C6", 0.45), ("D6", 0.6))):
        placer(tot, cloche(note(n), 1.6, 0.55, ratio=3.5, indice=1.2, pan=pan), 0.12 + i * 0.16, 0.42)
    placer(tot, cloche(note("G6"), 1.2, 0.5, ratio=2.76, indice=0.8, pan=0.0), 1.0, 0.18)
    return couper(reverb(adoucir_rapide(tot, 6500), 1.1, 0.3), 2.5)


def s_desktop_login():
    tot = silence(1.6)
    for i, (n, pan) in enumerate((("G4", -0.4), ("B4", -0.1), ("D5", 0.2), ("G5", 0.45))):
        placer(tot, cloche(note(n), 1.2, 0.42, indice=1.3, pan=pan), i * 0.11, 0.5)
    placer(tot, nappe([note("G3"), note("D4"), note("B4")], 1.3, 0.2, 0.45), 0.05, 0.35)
    return couper(reverb(adoucir_rapide(tot, 6500), 0.9, 0.26), 1.5)


def s_desktop_logout():
    tot = silence(1.6)
    for i, (n, pan) in enumerate((("G5", 0.45), ("D5", 0.2), ("B4", -0.1), ("G4", -0.4))):
        placer(tot, cloche(note(n), 1.2, 0.42, indice=1.0, pan=pan), i * 0.12, 0.5)
    placer(tot, nappe([note("G3"), note("D4")], 1.3, 0.15, 0.4), 0.15, 0.3)
    return couper(reverb(adoucir_rapide(tot, 6000), 0.9, 0.26), 1.5)


def s_message():
    tot = silence(0.7)
    placer(tot, cloche(note("E6"), 0.5, 0.16, indice=1.4, pan=-0.2), 0.0, 0.6)
    placer(tot, cloche(note("A6"), 0.5, 0.2, indice=1.2, pan=0.25), 0.085, 0.6)
    return couper(reverb(adoucir_rapide(tot, 7500), 0.5, 0.2), 0.6)


def s_information():
    tot = silence(0.7)
    placer(tot, cloche(note("A5"), 0.6, 0.2, indice=1.1), 0.0, 0.7)
    placer(tot, cloche(note("E6"), 0.6, 0.16, indice=0.7, pan=0.3), 0.0, 0.25)
    return couper(reverb(adoucir_rapide(tot, 7000), 0.5, 0.2), 0.6)


def s_attention():
    tot = silence(0.7)
    for i in range(2):
        placer(tot, cloche(note("E5"), 0.4, 0.11, ratio=2.0, indice=1.4, pan=-0.15 + 0.3 * i), i * 0.17, 0.7)
        placer(tot, cloche(note("B5"), 0.4, 0.09, ratio=2.0, indice=0.6, pan=-0.15 + 0.3 * i), i * 0.17, 0.25)
    return couper(reverb(adoucir_rapide(tot, 6000), 0.45, 0.18), 0.6)


def s_erreur():
    tot = silence(0.7)
    placer(tot, cloche(note("D5"), 0.45, 0.13, ratio=1.41, indice=1.6, pan=-0.15), 0.0, 0.7)
    placer(tot, cloche(note("A4"), 0.45, 0.18, ratio=1.41, indice=1.4, pan=0.15), 0.13, 0.7)
    return couper(reverb(adoucir_rapide(tot, 5000), 0.45, 0.16), 0.6)


def s_bell():
    tot = silence(0.6)
    placer(tot, cloche(note("C6"), 0.55, 0.18, ratio=3.5, indice=1.8), 0.0, 0.8)
    return couper(reverb(adoucir_rapide(tot, 7500), 0.4, 0.15), 0.5)


def s_complete():
    tot = silence(0.7)
    for i, n in enumerate(("C6", "E6", "G6")):
        placer(tot, cloche(note(n), 0.45, 0.14 + 0.04 * i, indice=1.0, pan=-0.3 + 0.3 * i), i * 0.07, 0.55)
    return couper(reverb(adoucir_rapide(tot, 7500), 0.5, 0.2), 0.6)


def s_device_added():
    tot = silence(0.7)
    placer(tot, glissando(note("G4"), note("G5"), 0.25, 0.08), 0.0, 0.35)
    placer(tot, cloche(note("G5"), 0.45, 0.14, indice=1.0, pan=-0.2), 0.04, 0.6)
    placer(tot, cloche(note("D6"), 0.45, 0.17, indice=0.9, pan=0.25), 0.13, 0.6)
    return couper(reverb(adoucir_rapide(tot, 7000), 0.45, 0.2), 0.6)


def s_device_removed():
    tot = silence(0.7)
    placer(tot, glissando(note("G5"), note("G4"), 0.25, 0.08), 0.0, 0.35)
    placer(tot, cloche(note("D6"), 0.45, 0.12, indice=0.9, pan=0.25), 0.02, 0.6)
    placer(tot, cloche(note("G5"), 0.45, 0.17, indice=0.9, pan=-0.2), 0.12, 0.6)
    return couper(reverb(adoucir_rapide(tot, 6500), 0.45, 0.2), 0.6)


def s_trash_empty():
    tot = silence(0.7)
    b = bruit_filtre(0.35, 900, 5000, 0.07, 0.04)
    placer(tot, panoramique(b, -0.2) * 0.5, 0.0)
    placer(tot, panoramique(bruit_filtre(0.3, 500, 2500, 0.06, 0.03), 0.25) * 0.4, 0.08)
    placer(tot, cloche(note("E5"), 0.4, 0.12, ratio=1.5, indice=0.6), 0.14, 0.35)
    return couper(reverb(adoucir_rapide(tot, 6000), 0.4, 0.18), 0.6)


def s_volume():
    tot = silence(0.25)
    placer(tot, cloche(note("A5"), 0.18, 0.045, ratio=3.0, indice=0.9), 0.0, 0.8)
    return couper(reverb(adoucir_rapide(tot, 7000), 0.2, 0.1), 0.2)


def s_power_plug():
    tot = silence(0.7)
    placer(tot, glissando(note("C5"), note("C6"), 0.3, 0.12), 0.0, 0.35)
    placer(tot, cloche(note("C6"), 0.45, 0.14, indice=0.8, pan=-0.2), 0.08, 0.5)
    placer(tot, cloche(note("G6"), 0.45, 0.16, indice=0.7, pan=0.25), 0.16, 0.45)
    return couper(reverb(adoucir_rapide(tot, 7000), 0.45, 0.2), 0.6)


def s_power_unplug():
    tot = silence(0.7)
    placer(tot, glissando(note("C6"), note("C5"), 0.3, 0.12), 0.0, 0.35)
    placer(tot, cloche(note("G5"), 0.45, 0.12, indice=0.8, pan=0.25), 0.06, 0.5)
    placer(tot, cloche(note("C5"), 0.45, 0.17, indice=0.8, pan=-0.2), 0.15, 0.5)
    return couper(reverb(adoucir_rapide(tot, 6500), 0.45, 0.2), 0.6)


def declic(debut, tot, pan, aigu=4500):
    placer(tot, panoramique(bruit_filtre(0.05, 1500, aigu, 0.008, 0.0008), pan) * 0.9, debut)
    placer(tot, panoramique(bruit_filtre(0.06, 200, 900, 0.012, 0.001), pan) * 0.6, debut)


def s_camera():
    tot = silence(0.4)
    declic(0.0, tot, -0.15)
    declic(0.09, tot, 0.15, 3800)
    return couper(reverb(adoucir_rapide(tot, 8000), 0.25, 0.12), 0.35)


def s_capture():
    tot = silence(0.6)
    declic(0.0, tot, -0.15)
    declic(0.08, tot, 0.15, 3800)
    placer(tot, cloche(note("E6"), 0.4, 0.12, indice=0.8, pan=0.2), 0.12, 0.3)
    placer(tot, cloche(note("B6"), 0.35, 0.1, indice=0.6, pan=0.35), 0.17, 0.2)
    return couper(reverb(adoucir_rapide(tot, 7500), 0.4, 0.18), 0.55)


SONS = {
    "service-login": s_service_login,
    "desktop-login": s_desktop_login,
    "desktop-logout": s_desktop_logout,
    "message-new-instant": s_message,
    "dialog-information": s_information,
    "dialog-warning": s_attention,
    "dialog-error": s_erreur,
    "bell": s_bell,
    "complete": s_complete,
    "device-added": s_device_added,
    "device-removed": s_device_removed,
    "trash-empty": s_trash_empty,
    "audio-volume-change": s_volume,
    "power-plug": s_power_plug,
    "power-unplug": s_power_unplug,
    "camera-shutter": s_camera,
    "screen-capture": s_capture,
}
# Alias courants (KDE / GNOME) servis par des copies du même fichier
ALIAS = {
    "message-new-instant": ["message", "message-new-email"],
    "dialog-warning": ["dialog-warning-auth"],
    "bell": ["bell-window-system", "bell-terminal"],
    "device-added": ["device-added-media"],
    "device-removed": ["device-removed-media"],
    "screen-capture": [],
    "audio-volume-change": [],
}
# Durées maximales imposées
DUREES_MAX = {"service-login": 2.5, "desktop-login": 1.5, "desktop-logout": 1.5}
DUREE_NOTIF = 0.6


def ecrire_wav(chemin, x):
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(FE)
        w.writeframes(pcm.tobytes())


def encodeur():
    if shutil.which("ffmpeg"):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
        if "libvorbis" in r.stdout:
            return "ffmpeg"
    if shutil.which("oggenc"):
        return "oggenc"
    return None


def encoder(wav, oga, outil):
    if outil == "ffmpeg":
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-map_metadata", "-1", "-c:a", "libvorbis",
                        "-q:a", "6", "-fflags", "+bitexact", "-flags:a", "+bitexact", oga], check=True)
    else:
        subprocess.run(["oggenc", "-Q", "-q", "6", "-o", oga, wav], check=True)


def index_theme(extension):
    return ("[Sound Theme]\n"
            "Name=ExoLyx\n"
            "Comment=Sons ExoLyx : cloches cristallines et accords majeurs, doux et spatiaux\n"
            "Inherits=freedesktop\n"
            "Directories=stereo\n"
            "\n"
            "[stereo]\n"
            "OutputProfile=stereo\n")


def generer(racine):
    stereo = os.path.join(racine, "stereo")
    if os.path.isdir(stereo):
        shutil.rmtree(stereo)
    os.makedirs(stereo)
    outil = encodeur()
    ext = ".oga" if outil else ".wav"
    rapport = []
    with tempfile.TemporaryDirectory() as tmp:
        for nom, f in SONS.items():
            x = normaliser(f())
            limite = DUREES_MAX.get(nom, DUREE_NOTIF)
            assert len(x) / FE <= limite + 1e-6, (nom, len(x) / FE)
            wav = os.path.join(tmp if outil else stereo, nom + ".wav")
            ecrire_wav(wav, x)
            if outil:
                encoder(wav, os.path.join(stereo, nom + ext), outil)
            rapport.append((nom, len(x) / FE, lufs(x), 20 * np.log10(crete_vraie(x))))
            for a in ALIAS.get(nom, []):
                shutil.copyfile(os.path.join(stereo, nom + ext), os.path.join(stereo, a + ext))
    with open(os.path.join(racine, "index.theme"), "w", encoding="utf-8") as fh:
        fh.write(index_theme(ext))
    return outil, rapport


if __name__ == "__main__":
    ici = os.path.dirname(os.path.abspath(__file__))
    racine = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ici, "ExoLyx")
    outil, rapport = generer(racine)
    print("Encodage : %s" % (outil or "aucun (WAV)"))
    for nom, d, l, c in rapport:
        print("%-22s %5.2f s  %6.1f LUFS  crête %5.1f dBFS" % (nom, d, l, c))
