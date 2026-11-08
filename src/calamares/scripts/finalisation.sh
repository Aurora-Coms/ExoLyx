#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ExoLyx — finalisation de la cible (chroot, instance shellprocess@finalisation).
# Exécuté AVANT grubcfg/bootloader : toute modification de /etc/default/grub
# se fait ici. Chaque étape est tolérante : un échec est journalisé mais
# n'interrompt pas l'installation.
set -uo pipefail

journal() { printf '[finalisation] %s\n' "$*"; }
etape() { journal "$1"; shift; "$@" || journal "  échec (non bloquant) : $*"; }

# 1. Trousseau pacman ---------------------------------------------------------
# Sur le live, /etc/pacman.d/gnupg est un tmpfs : la cible arrive sans trousseau.
if [ ! -s /etc/pacman.d/gnupg/pubring.gpg ] && [ ! -s /etc/pacman.d/gnupg/pubring.kbx ]; then
    etape "initialisation du trousseau pacman" pacman-key --init
    etape "importation des clés Arch Linux" pacman-key --populate archlinux
fi

# 2. Dépôt ExoLyx --------------------------------------------------------------
# Ajouté par le post_install du paquet exolyx-system : on vérifie seulement.
if grep -q '^\[exolyx\]' /etc/pacman.conf; then
    journal "dépôt [exolyx] présent dans /etc/pacman.conf"
else
    journal "ATTENTION : dépôt [exolyx] absent, ajout de secours"
    printf '\n[exolyx]\nSigLevel = Optional TrustAll\nServer = https://github.com/Aurora-Coms/ExoLyx/releases/download/depot\n' >> /etc/pacman.conf
fi

# 3. Snapper ----------------------------------------------------------------
if [ "$(findmnt -no FSTYPE /)" = "btrfs" ] && command -v snapper >/dev/null; then
    journal "configuration de snapper"
    if [ ! -f /etc/snapper/configs/root ]; then
        # /.snapshots est le sous-volume @snapshots : snapper veut créer le sien.
        source_snap="$(findmnt -no SOURCE /.snapshots 2>/dev/null | sed 's/\[.*//')"
        umount /.snapshots 2>/dev/null || true
        rmdir /.snapshots 2>/dev/null || rm -rf /.snapshots
        etape "création de la configuration root" snapper --no-dbus -c root create-config /
        # On remplace le sous-volume .snapshots créé par snapper par @snapshots.
        btrfs subvolume delete /.snapshots >/dev/null 2>&1 || true
        mkdir -p /.snapshots
        if [ -n "$source_snap" ]; then
            mount -o subvol=/@snapshots,noatime,compress=zstd:1 "$source_snap" /.snapshots || true
        fi
        chmod 750 /.snapshots
    fi
    cfg=/etc/snapper/configs/root
    if [ -f "$cfg" ]; then
        regle() { if grep -q "^$1=" "$cfg"; then sed -i "s|^$1=.*|$1=\"$2\"|" "$cfg"; else echo "$1=\"$2\"" >> "$cfg"; fi; }
        regle ALLOW_GROUPS wheel
        regle SYNC_ACL yes
        regle TIMELINE_CREATE yes
        regle TIMELINE_CLEANUP yes
        regle TIMELINE_LIMIT_HOURLY 5
        regle TIMELINE_LIMIT_DAILY 7
        regle TIMELINE_LIMIT_WEEKLY 2
        regle TIMELINE_LIMIT_MONTHLY 1
        regle TIMELINE_LIMIT_YEARLY 0
        regle NUMBER_CLEANUP yes
        regle NUMBER_LIMIT 10
        regle NUMBER_LIMIT_IMPORTANT 5
        regle SPACE_LIMIT 0.5
        regle FREE_LIMIT 0.2
        # Quotas Btrfs : permettent à snapper de respecter SPACE_LIMIT.
        etape "activation des quotas Btrfs" btrfs quota enable /
        etape "groupe de quotas snapper" snapper --no-dbus -c root setup-quota
    fi
    # Nom du sous-menu GRUB des instantanés.
    if [ -f /etc/default/grub-btrfs/config ]; then
        if grep -q 'GRUB_BTRFS_SUBMENUNAME=' /etc/default/grub-btrfs/config; then
            sed -i -E 's|^#?\s*GRUB_BTRFS_SUBMENUNAME=.*|GRUB_BTRFS_SUBMENUNAME="Instantanés ExoLyx"|' /etc/default/grub-btrfs/config
        else
            echo 'GRUB_BTRFS_SUBMENUNAME="Instantanés ExoLyx"' >> /etc/default/grub-btrfs/config
        fi
    fi
    for unite in snapper-timeline.timer snapper-cleanup.timer grub-btrfsd.service; do
        etape "activation de $unite" systemctl enable "$unite"
    done
else
    journal "racine non Btrfs : snapper et grub-btrfs non configurés"
    systemctl disable grub-btrfsd.service snapper-timeline.timer snapper-cleanup.timer 2>/dev/null || true
fi

# 4. Pare-feu (ufw) -----------------------------------------------------------
# On édite les fichiers plutôt que « ufw enable » : dans le chroot, ufw
# appliquerait les règles au noyau du live.
if command -v ufw >/dev/null; then
    journal "pare-feu : refuse l'entrant, autorise le sortant"
    sed -i -E 's/^DEFAULT_INPUT_POLICY=.*/DEFAULT_INPUT_POLICY="DROP"/; s/^DEFAULT_OUTPUT_POLICY=.*/DEFAULT_OUTPUT_POLICY="ACCEPT"/; s/^DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="DROP"/' /etc/default/ufw
    sed -i -E 's/^ENABLED=.*/ENABLED=yes/' /etc/ufw/ufw.conf
    etape "activation de ufw.service" systemctl enable ufw.service
fi

# 5. Plymouth -------------------------------------------------------------------
if command -v plymouth-set-default-theme >/dev/null; then
    # Sans -R : l'initramfs est régénéré plus loin par le module initcpio.
    etape "thème Plymouth exolyx" plymouth-set-default-theme exolyx
fi

# 6. GRUB -------------------------------------------------------------------------
if [ -f /etc/default/grub ]; then
    journal "réglage de /etc/default/grub"
    ligne="$(grep -E '^GRUB_CMDLINE_LINUX_DEFAULT=' /etc/default/grub | head -n1 | sed -E 's/^GRUB_CMDLINE_LINUX_DEFAULT="?([^"]*)"?/\1/')"
    for p in quiet splash; do
        case " $ligne " in *" $p "*) ;; *) ligne="$ligne $p" ;; esac
    done
    ligne="$(echo "$ligne" | sed -E 's/^\s+//; s/\s+/ /g')"
    if grep -qE '^GRUB_CMDLINE_LINUX_DEFAULT=' /etc/default/grub; then
        sed -i -E "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|GRUB_CMDLINE_LINUX_DEFAULT=\"$ligne\"|" /etc/default/grub
    else
        echo "GRUB_CMDLINE_LINUX_DEFAULT=\"$ligne\"" >> /etc/default/grub
    fi
    # Double amorçage : laisser os-prober détecter Windows s'il est installé.
    if command -v os-prober >/dev/null; then
        if grep -qE '^#?\s*GRUB_DISABLE_OS_PROBER=' /etc/default/grub; then
            sed -i -E 's/^#?\s*GRUB_DISABLE_OS_PROBER=.*/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
        else
            echo 'GRUB_DISABLE_OS_PROBER=false' >> /etc/default/grub
        fi
    fi
fi
if [ -x /usr/share/exolyx/grub/appliquer-theme.sh ]; then
    # Le script règle GRUB_THEME ; grub.cfg est généré ensuite par « bootloader ».
    etape "thème GRUB ExoLyx" /usr/share/exolyx/grub/appliquer-theme.sh
else
    journal "ATTENTION : /usr/share/exolyx/grub/appliquer-theme.sh introuvable"
fi

journal "terminé"
exit 0
