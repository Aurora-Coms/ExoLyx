#!/bin/bash
# Réapplique l'identité ExoLyx (os-release, issue, dépôt pacman) — appelé à l'installation
# et après chaque mise à jour du paquet « filesystem » ou « pacman ».
set -e
install -m644 /usr/lib/exolyx/os-release /usr/lib/os-release
cat > /etc/issue <<'ISSUE'
ExoLyx \r (\l)

ISSUE
if ! grep -q '^\[exolyx\]' /etc/pacman.conf; then
  # Le dépôt ExoLyx passe avant [core] pour fournir les paquets maison
  sed -i '0,/^\[core\]/s//[exolyx]\nSigLevel = Optional TrustAll\nServer = https:\/\/github.com\/Aurora-Coms\/ExoLyx\/releases\/download\/depot\n\n[core]/' /etc/pacman.conf
fi
grep -q '^ParallelDownloads' /etc/pacman.conf || sed -i 's/^#ParallelDownloads.*/ParallelDownloads = 5/' /etc/pacman.conf
grep -q '^Color' /etc/pacman.conf || sed -i 's/^#Color/Color/' /etc/pacman.conf
exit 0
