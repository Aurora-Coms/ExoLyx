#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ExoLyx — nettoyage de la cible après unpackfs (exécuté dans le chroot par
# Calamares, instance shellprocess@nettoyage).
# Retire tout ce que l'ISO live ajoute : utilisateur live, autologin,
# réglages archiso, services live ; recopie le noyau ; réécrit le preset
# mkinitcpio au format standard.
set -uo pipefail

journal() { printf '[nettoyage] %s\n' "$*"; }
UTILISATEUR_LIVE="exolyx"
SUPPORT="/run/archiso/bootmnt"

# 1. Utilisateur live -------------------------------------------------------
if getent passwd "$UTILISATEUR_LIVE" >/dev/null; then
    journal "suppression de l'utilisateur live « $UTILISATEUR_LIVE »"
    pkill -KILL -u "$UTILISATEUR_LIVE" 2>/dev/null || true   # sans effet dans le chroot, par précaution
    userdel -r "$UTILISATEUR_LIVE" 2>/dev/null || userdel "$UTILISATEUR_LIVE" 2>/dev/null || true
fi
# Restes éventuels dans les fichiers de comptes fournis par l'ISO.
for f in /etc/passwd /etc/shadow /etc/group /etc/gshadow; do
    [ -f "$f" ] || continue
    # entrée propre à l'utilisateur
    sed -i -E "/^${UTILISATEUR_LIVE}:/d" "$f"
    # membre secondaire de groupes (group/gshadow : 4e champ)
    case "$f" in
        /etc/group|/etc/gshadow)
            awk -F: -v OFS=: -v u="$UTILISATEUR_LIVE" '{
                n = split($4, m, ","); r = ""
                for (i = 1; i <= n; i++) if (m[i] != u && m[i] != "") r = (r == "" ? m[i] : r "," m[i])
                $4 = r; print }' "$f" > "$f.exolyx" && cat "$f.exolyx" > "$f" && rm -f "$f.exolyx" ;;
    esac
done
rm -rf "/home/${UTILISATEUR_LIVE}" "/var/spool/mail/${UTILISATEUR_LIVE}" "/var/lib/AccountsService/users/${UTILISATEUR_LIVE}"

# 2. Fichiers propres au live -----------------------------------------------
journal "suppression des fichiers du live"
rm -f \
    /etc/sddm.conf.d/20-autologin-live.conf \
    /etc/sudoers.d/10-exolyx-live \
    /etc/polkit-1/rules.d/49-exolyx-live.rules \
    /etc/tmpfiles.d/exolyx-live.conf \
    /etc/mkinitcpio.conf.d/archiso.conf \
    /etc/systemd/system/getty@tty1.service.d/autologin.conf \
    /root/.automated_script.sh \
    /root/.zlogin \
    /etc/systemd/system/pacman-init.service \
    /etc/systemd/system/multi-user.target.wants/pacman-init.service \
    /etc/systemd/system/choose-mirror.service \
    /etc/systemd/system/multi-user.target.wants/choose-mirror.service \
    /etc/systemd/system/etc-pacman.d-gnupg.mount \
    /etc/systemd/journald.conf.d/volatile-storage.conf \
    /etc/systemd/logind.conf.d/do-not-suspend.conf \
    /etc/ssh/sshd_config.d/10-archiso.conf \
    /etc/motd
rmdir /etc/systemd/system/getty@tty1.service.d 2>/dev/null || true
# Services livecd-* et tous leurs liens d'activation.
find /etc/systemd/system -name 'livecd-*' \( -type f -o -type l \) -print -delete 2>/dev/null || true
# Liens orphelins restants (cibles supprimées ci-dessus).
find /etc/systemd/system -xtype l -print -delete 2>/dev/null || true

# 3. Noyau et microcodes -----------------------------------------------------
# L'airootfs n'a pas toujours le noyau dans /boot : on le recopie depuis l'ISO.
if [ -f "$SUPPORT/arch/boot/x86_64/vmlinuz-linux" ]; then
    journal "copie du noyau depuis le support"
    install -Dm644 "$SUPPORT/arch/boot/x86_64/vmlinuz-linux" /boot/vmlinuz-linux
elif noyau="$(ls -1 /usr/lib/modules/*/vmlinuz 2>/dev/null | sort -V | tail -n1)" && [ -n "$noyau" ]; then
    journal "copie du noyau depuis $noyau"
    install -Dm644 "$noyau" /boot/vmlinuz-linux
else
    journal "ATTENTION : noyau introuvable, /boot/vmlinuz-linux absent"
fi
for ucode in intel-ucode.img amd-ucode.img; do
    if [ ! -f "/boot/$ucode" ] && [ -f "$SUPPORT/arch/boot/$ucode" ]; then
        install -Dm644 "$SUPPORT/arch/boot/$ucode" "/boot/$ucode"
    fi
done
# Images initramfs du live (seront régénérées par le module initcpio).
rm -f /boot/initramfs-linux*.img /boot/archiso.img

# 4. Preset mkinitcpio standard ---------------------------------------------
journal "réécriture de /etc/mkinitcpio.d/linux.preset"
install -d /etc/mkinitcpio.d
cat > /etc/mkinitcpio.d/linux.preset <<'PRESET'
# mkinitcpio preset file for the 'linux' package

#ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-linux"

PRESETS=('default' 'fallback')

#default_config="/etc/mkinitcpio.conf"
default_image="/boot/initramfs-linux.img"
#default_uki="/efi/EFI/Linux/arch-linux.efi"
#default_options="--splash /usr/share/systemd/bootctl/splash-arch.bmp"

#fallback_config="/etc/mkinitcpio.conf"
fallback_image="/boot/initramfs-linux-fallback.img"
#fallback_uki="/efi/EFI/Linux/arch-linux-fallback.efi"
fallback_options="-S autodetect"
PRESET

# 5. Paquet du hook archiso ---------------------------------------------------
if pacman -Qq mkinitcpio-archiso >/dev/null 2>&1; then
    journal "désinstallation de mkinitcpio-archiso"
    SNAP_PAC_SKIP=y pacman -Rdd --noconfirm mkinitcpio-archiso || true
fi
# Le hook « archiso » ne doit plus figurer dans mkinitcpio.conf
# (initcpiocfg réécrit HOOKS ensuite, ceci est une sécurité).
sed -i -E '/^HOOKS=/ s/\s*\barchiso[a-z_]*\b//g' /etc/mkinitcpio.conf 2>/dev/null || true

journal "terminé"
exit 0
