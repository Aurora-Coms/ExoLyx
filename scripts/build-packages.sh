#!/usr/bin/env bash
# Construit les paquets AUR nécessaires et tous les paquets ExoLyx dans un dépôt local.
# À lancer sur Arch Linux en root (crée un utilisateur « constructeur » pour makepkg).
# Usage : scripts/build-packages.sh [dossier-depot]   (défaut : ./depot)
set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
DEPOT="$(realpath -m "${1:-$RACINE/depot}")"
AUR=(calamares)

[[ $EUID -eq 0 ]] || { echo "À lancer en root."; exit 1; }
mkdir -p "$DEPOT"
id constructeur &>/dev/null || useradd -m constructeur
echo "constructeur ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/constructeur
TRAVAIL=$(mktemp -d); chown constructeur: "$TRAVAIL"
# makepkg travaille sur une copie du dépôt (droits d'écriture)
cp -a "$RACINE" "$TRAVAIL/exolyx"; chown -R constructeur: "$TRAVAIL/exolyx"

construire() { # $1 = dossier contenant le PKGBUILD, $2.. = options makepkg en plus
  local d="$1"; shift
  echo "::group::Paquet $(basename "$d")"
  ( cd "$d" && sudo -u constructeur PKGDEST="$TRAVAIL/sortie" makepkg -s --noconfirm --needed --cleanbuild "$@" )
  echo "::endgroup::"
}
mkdir -p "$TRAVAIL/sortie"; chown constructeur: "$TRAVAIL/sortie"

# 1. ckbcomp (dépendance de calamares) depuis l'archive Debian, dernière version publiée
VCK=$(curl -fsSL https://deb.debian.org/debian/pool/main/c/console-setup/ |
      grep -oP 'console-setup_\K[0-9.]+(?=\.tar\.xz)' | sort -Vu | tail -1)
[[ -n $VCK ]] || { echo "Version de console-setup introuvable"; exit 1; }
curl -fsSL --retry 5 -o "$TRAVAIL/cs.tar.xz" "https://deb.debian.org/debian/pool/main/c/console-setup/console-setup_${VCK}.tar.xz"
mkdir -p "$TRAVAIL/ckbcomp"
sed -e "s/@VERSION@/$VCK/" -e "s/@SHA256@/$(sha256sum "$TRAVAIL/cs.tar.xz" | cut -d' ' -f1)/" \
    "$RACINE/scripts/ckbcomp/PKGBUILD.in" > "$TRAVAIL/ckbcomp/PKGBUILD"
cp "$TRAVAIL/cs.tar.xz" "$TRAVAIL/ckbcomp/console-setup_${VCK}.tar.xz"
chown -R constructeur: "$TRAVAIL/ckbcomp"
construire "$TRAVAIL/ckbcomp"
pacman -U --noconfirm --needed "$TRAVAIL"/sortie/ckbcomp-[0-9]*.pkg.tar.zst

# 2. AUR
for p in "${AUR[@]}"; do
  sudo -u constructeur git clone --depth 1 "https://aur.archlinux.org/$p.git" "$TRAVAIL/aur-$p"
  construire "$TRAVAIL/aur-$p"
  pacman -U --noconfirm --needed "$TRAVAIL"/sortie/"$p"-[0-9]*.pkg.tar.zst
done

# 3. Paquets ExoLyx
for d in "$TRAVAIL"/exolyx/packages/*/; do
  [[ -f "$d/PKGBUILD" ]] && construire "$d"
done

cp "$TRAVAIL"/sortie/*.pkg.tar.zst "$DEPOT"/
( cd "$DEPOT" && rm -f exolyx.db* exolyx.files* && repo-add -q exolyx.db.tar.gz ./*.pkg.tar.zst )
echo "Dépôt prêt : $DEPOT"; ls -1 "$DEPOT"
