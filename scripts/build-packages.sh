#!/usr/bin/env bash
# Construit les paquets AUR nécessaires et tous les paquets ExoLyx dans un dépôt local.
# À lancer sur Arch Linux en root (crée un utilisateur « constructeur » pour makepkg).
# Usage : scripts/build-packages.sh [dossier-depot]   (défaut : ./depot)
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
DEPOT="$(realpath -m "${1:-$RACINE/depot}")"
AUR=(ckbcomp calamares)

[[ $EUID -eq 0 ]] || { echo "À lancer en root."; exit 1; }
mkdir -p "$DEPOT"
id constructeur &>/dev/null || useradd -m constructeur
echo "constructeur ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/constructeur
TRAVAIL=$(mktemp -d); chown constructeur: "$TRAVAIL"
# makepkg travaille sur une copie du dépôt (droits d'écriture)
cp -a "$RACINE" "$TRAVAIL/exolyx"; chown -R constructeur: "$TRAVAIL/exolyx"

construire() { # $1 = dossier contenant le PKGBUILD
  echo "::group::Paquet $(basename "$1")"
  ( cd "$1" && sudo -u constructeur PKGDEST="$TRAVAIL/sortie" makepkg -s --noconfirm --needed --cleanbuild )
  echo "::endgroup::"
}
mkdir -p "$TRAVAIL/sortie"; chown constructeur: "$TRAVAIL/sortie"

# 1. AUR (dans l'ordre : ckbcomp est une dépendance de calamares)
for p in "${AUR[@]}"; do
  sudo -u constructeur git clone --depth 1 "https://aur.archlinux.org/$p.git" "$TRAVAIL/aur-$p"
  construire "$TRAVAIL/aur-$p"
  pacman -U --noconfirm --needed "$TRAVAIL"/sortie/"$p"-[0-9]*.pkg.tar.zst
done

# 2. Paquets ExoLyx
for d in "$TRAVAIL"/exolyx/packages/*/; do
  [[ -f "$d/PKGBUILD" ]] && construire "$d"
done

cp "$TRAVAIL"/sortie/*.pkg.tar.zst "$DEPOT"/
( cd "$DEPOT" && rm -f exolyx.db* exolyx.files* && repo-add -q exolyx.db.tar.gz ./*.pkg.tar.zst )
echo "Dépôt prêt : $DEPOT"; ls -1 "$DEPOT"
