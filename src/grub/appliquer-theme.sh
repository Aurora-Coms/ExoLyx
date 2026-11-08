#!/usr/bin/env bash
# Active le thème GRUB « exolyx » dans /etc/default/grub (idempotent).
#
#   appliquer-theme.sh [-r RACINE] [--regenerer]
#
#   -r RACINE      système cible monté (ex. /mnt) : modifie RACINE/etc/default/grub
#   --regenerer    lance ensuite grub-mkconfig -o /boot/grub/grub.cfg (hors chroot : non)
#
# Appelé par l'installateur ExoLyx (qui régénère lui-même grub.cfg).
# Règle : GRUB_THEME, GRUB_GFXMODE (auto si absent) et s'assure que la sortie
# n'est pas forcée en mode texte (GRUB_TERMINAL_OUTPUT=console la commente).
set -euo pipefail

RACINE=""
REGENERER=0
while [ $# -gt 0 ]; do
  case "$1" in
    -r|--racine) RACINE="${2:?racine manquante}"; shift 2 ;;
    --regenerer) REGENERER=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Option inconnue : $1" >&2; exit 2 ;;
  esac
done

THEME="/usr/share/grub/themes/exolyx/theme.txt"
CONF="$RACINE/etc/default/grub"

if [ ! -f "$CONF" ]; then
  echo "Erreur : $CONF introuvable (paquet grub installé ?)" >&2
  exit 1
fi
if [ ! -f "$RACINE$THEME" ]; then
  echo "Attention : $RACINE$THEME absent (paquet exolyx-grub-theme installé ?)" >&2
fi

# définit (ou remplace, même commentée) une variable de /etc/default/grub
definir() {
  local cle="$1" val="$2"
  if grep -Eq "^[#[:space:]]*${cle}=" "$CONF"; then
    # remplace la première occurrence (active ou commentée), supprime les suivantes
    awk -v cle="$cle" -v ligne="${cle}=${val}" '
      $0 ~ "^[#[:space:]]*" cle "=" { if (!fait) { print ligne; fait = 1 }; next }
      { print }' "$CONF" > "$CONF.exolyx.tmp"
    cat "$CONF.exolyx.tmp" > "$CONF"
    rm -f "$CONF.exolyx.tmp"
  else
    printf '%s=%s\n' "$cle" "$val" >> "$CONF"
  fi
}

definir GRUB_THEME "\"$THEME\""
# résolution : garde un réglage explicite existant, sinon « auto »
if ! grep -Eq '^GRUB_GFXMODE=' "$CONF"; then
  definir GRUB_GFXMODE "auto"
fi
# un terminal forcé en mode console empêche l'affichage du thème
sed -i -E 's/^(GRUB_TERMINAL_OUTPUT=["]?console["]?)/#\1/' "$CONF"

echo "Thème GRUB ExoLyx activé dans $CONF"

if [ "$REGENERER" = 1 ]; then
  if [ -n "$RACINE" ]; then
    arch-chroot "$RACINE" grub-mkconfig -o /boot/grub/grub.cfg
  else
    grub-mkconfig -o /boot/grub/grub.cfg
  fi
fi
