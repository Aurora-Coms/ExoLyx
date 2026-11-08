#!/usr/bin/env bash
# Exécuté dans un conteneur archlinux:latest privilégié (voir .github/workflows/iso.yml).
set -euo pipefail
cd /exolyx
sed -i 's/^#ParallelDownloads.*/ParallelDownloads = 10/' /etc/pacman.conf
pacman-key --init >/dev/null
pacman -Syu --noconfirm --needed archiso base-devel git python sudo
scripts/build-packages.sh /exolyx/depot
scripts/build-iso.sh /exolyx/depot /exolyx/sortie
# rendre les fichiers lisibles par le runner
chmod -R a+rX /exolyx/depot /exolyx/sortie
