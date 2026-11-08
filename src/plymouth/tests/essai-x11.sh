#!/usr/bin/env bash
# Essai RÉEL du thème Plymouth « exolyx » avec le moteur de rendu X11 de
# Plymouth, dans un serveur X virtuel (Xvfb), et captures d'écran.
#
#   src/plymouth/tests/essai-x11.sh PREFIXE_PLYMOUTH DOSSIER_CAPTURES [LxH]
#
# PREFIXE_PLYMOUTH : Plymouth compilé avec -Dgtk=enabled (renderers/x11.so),
#                    par ex. installé dans /opt/ply (meson --prefix=/opt/ply).
#                    Attention : plymouthd charge ses greffons depuis le
#                    PLYMOUTH_PLUGIN_PATH compilé ; x11.so doit s'y trouver.
# Nécessite : Xvfb, xwd (x11-apps) ou ImageMagick « import », Python + Pillow.
# À lancer en root (plymouthd ouvre un tty et un socket abstrait).
set -euo pipefail

PREFIXE=${1:?préfixe plymouth}
SORTIE=${2:?dossier de sortie}
TAILLE=${3:-1920x1080}
ICI=$(cd "$(dirname "$0")" && pwd)
THEME_SRC="$ICI/../exolyx"
THEMES="$PREFIXE/share/plymouth/themes"
mkdir -p "$SORTIE" "$THEMES/exolyx" "$PREFIXE/etc/plymouth"

# thème copié avec chemins réécrits vers le préfixe
cp "$THEME_SRC"/*.png "$THEME_SRC"/exolyx.script "$THEMES/exolyx/"
sed "s#/usr/share/plymouth/themes#$THEMES#" "$THEME_SRC/exolyx.plymouth" > "$THEMES/exolyx/exolyx.plymouth"
printf '[Daemon]\nTheme=exolyx\nShowDelay=0\n' > "$PREFIXE/etc/plymouth/plymouthd.conf"

PLY="$PREFIXE/bin/plymouth"
NOM=$(echo "$TAILLE" | tr -d " ")${MODE:+-$MODE}
AFF=:57
Xvfb $AFF -screen 0 "${TAILLE}x24" -dpi 96 >/dev/null 2>&1 &
XPID=$!
sleep 1
export DISPLAY=$AFF
JOURNAL="$SORTIE/plymouth-$NOM-journal.txt"

capturer() {
  python3 - "$SORTIE/plymouth-$NOM-$1.png" <<'EOF'
import subprocess, sys, io
from PIL import Image
xwd = subprocess.run(["xwd", "-root", "-silent"], capture_output=True, check=True).stdout
try:
    Image.open(io.BytesIO(xwd)).convert("RGB").save(sys.argv[1])
except Exception:
    subprocess.run(["convert", "xwd:-", sys.argv[1]], input=xwd, check=True)
print("  capture :", sys.argv[1])
EOF
}

arreter() {
  timeout 3 "$PLY" quit 2>/dev/null || true
  pkill -f "$PREFIXE/sbin/plymouthd" 2>/dev/null || true
  sleep 0.5
  kill "$XPID" 2>/dev/null || true
}
trap arreter EXIT

# plymouthd a besoin d'un vrai terminal : on lui fournit un pseudo-terminal
python3 - "$PREFIXE/sbin/plymouthd" "$JOURNAL" "${MODE:-boot}" <<'EOF' &
import os, pty, subprocess, sys, time
maitre, esclave = pty.openpty()
tty = os.ttyname(esclave)
p = subprocess.Popen([sys.argv[1], "--no-daemon", "--debug", "--debug-file=" + sys.argv[2],
                      "--tty=" + tty, "--kernel-command-line=quiet splash plymouth.force-splash",
                      "--mode=" + sys.argv[3], "--graphical-boot"])
p.wait()
EOF
sleep 1.5
"$PLY" show-splash
sleep 1
capturer demarrage-debut
for p in 0.2 0.45; do
  # la progression « réelle » vient de systemd ; on fait avancer le temps
  "$PLY" update --status="essai-$p" || true
  sleep 1.6
done
capturer demarrage
"$PLY" display-message --text="Vérification du système de fichiers…"
sleep 0.5
capturer message
"$PLY" hide-message --text="Vérification du système de fichiers…" || true
# invite de mot de passe : on la laisse ouverte en arrière-plan
"$PLY" ask-for-password --prompt="Mot de passe pour déchiffrer cryptroot" >/dev/null 2>&1 &
DEMANDE=$!
sleep 1
capturer mot-de-passe
kill "$DEMANDE" 2>/dev/null || true
timeout 3 "$PLY" quit || true
sleep 0.5
echo "Journal : $JOURNAL"
grep -iE "script|error|erreur" "$JOURNAL" | grep -viE "^.*loading|keyboard" | tail -20 || true
