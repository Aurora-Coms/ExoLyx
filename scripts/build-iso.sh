#!/usr/bin/env bash
# Assemble le profil archiso ExoLyx (releng + surcharges) et construit l'ISO.
# Prérequis : Arch Linux, root, paquet archiso, dépôt local construit par build-packages.sh.
# Usage : scripts/build-iso.sh [dossier-depot] [dossier-sortie]
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
DEPOT="$(realpath -m "${1:-$RACINE/depot}")"
SORTIE="$(realpath -m "${2:-$RACINE/sortie}")"
PROFIL="$(mktemp -d)/profil"
[[ $EUID -eq 0 ]] || { echo "À lancer en root."; exit 1; }
[[ -f "$DEPOT/exolyx.db.tar.gz" ]] || { echo "Dépôt introuvable : $DEPOT (lancez build-packages.sh)"; exit 1; }

# 1. Base : profil officiel releng
cp -a /usr/share/archiso/configs/releng "$PROFIL"

# 2. Retirer ce qui ne convient pas à un bureau (réseau systemd-networkd/iwd remplacé par NetworkManager)
rm -f  "$PROFIL"/airootfs/etc/systemd/system/multi-user.target.wants/{iwd,systemd-networkd,systemd-resolved,sshd}.service \
       "$PROFIL"/airootfs/etc/systemd/system/network-online.target.wants/systemd-networkd-wait-online.service \
       "$PROFIL"/airootfs/etc/systemd/system/sockets.target.wants/systemd-networkd*.socket \
       "$PROFIL"/airootfs/etc/systemd/system/dbus-org.freedesktop.network1.service \
       "$PROFIL"/airootfs/etc/systemd/system/systemd-networkd-wait-online.service.wants/* 2>/dev/null || true
rm -rf "$PROFIL"/airootfs/etc/systemd/network "$PROFIL"/airootfs/etc/systemd/network.conf.d \
       "$PROFIL"/airootfs/etc/systemd/system/getty@tty1.service.d \
       "$PROFIL"/airootfs/etc/systemd/system/cloud-init.target.wants \
       "$PROFIL"/airootfs/etc/systemd/system/sshd.service.d 2>/dev/null || true
rm -f "$PROFIL"/airootfs/etc/motd "$PROFIL"/airootfs/etc/xdg/reflector/reflector.conf 2>/dev/null || true

# 3. Surcharges ExoLyx
cp -a "$RACINE"/archiso/airootfs/. "$PROFIL"/airootfs/
cp "$RACINE"/archiso/packages.x86_64 "$PROFIL"/packages.x86_64
cat "$RACINE"/archiso/profiledef.overlay.sh >> "$PROFIL"/profiledef.sh

# 4. Dépôt local ExoLyx (prioritaire, en tête)
python3 - "$PROFIL/pacman.conf" "$DEPOT" <<'PY'
import sys, re
f, depot = sys.argv[1], sys.argv[2]
t = open(f).read()
bloc = f"\n[exolyx]\nSigLevel = Optional TrustAll\nServer = file://{depot}\n"
t = re.sub(r"\n\[core\]", bloc + "\n[core]", t, count=1)
t = t.replace("#ParallelDownloads", "ParallelDownloads")
open(f, "w").write(t)
PY

# 5. Menu de démarrage : nom, splash Plymouth
find "$PROFIL"/efiboot "$PROFIL"/grub "$PROFIL"/syslinux -type f \( -name '*.conf' -o -name '*.cfg' \) -print0 2>/dev/null |
while IFS= read -r -d '' f; do
  sed -i -E \
    -e 's/Arch Linux install medium/ExoLyx (live)/g' \
    -e 's/Arch Linux/ExoLyx/g' \
    -e '/archisobasedir=/ { /quiet splash/! s/$/ quiet splash cow_spacesize=4G/ }' "$f"
done
sed -i 's/^MENU TITLE .*/MENU TITLE ExoLyx/' "$PROFIL"/syslinux/*.cfg 2>/dev/null || true

# 6. Build
mkdir -p "$SORTIE"
mkarchiso -v -r -w "$(mktemp -d)/travail" -o "$SORTIE" "$PROFIL"
( cd "$SORTIE" && sha256sum exolyx-*.iso > SHA256SUMS )
ls -lh "$SORTIE"
