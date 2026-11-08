# Installateur Calamares d'ExoLyx — notes et points à vérifier

Paquet : `exolyx-calamares-config` (dépend uniquement de `calamares`).
Rédigé pour la syntaxe **Calamares 3.3 (Qt6/KF6)** ; le CI compile la version AUR **3.4.2**.
La 3.4 reprend le format de configuration de la 3.3 (pas de renommage de
module ni de clé connu pour ce qui est utilisé ici), mais cela n'a pas pu
être vérifié dans ce conteneur (pas d'accès aux miroirs Arch ni à l'AUR) :
**lancer d'abord `sudo calamares -d -D8` sur l'ISO et lire le journal**
(`~/.cache/calamares/session.log`) : les clés inconnues ou les modules
introuvables y apparaissent.

## Organisation

| Source (src/calamares/)            | Installé dans                                   |
|------------------------------------|-------------------------------------------------|
| `settings.conf`                    | `/etc/calamares/settings.conf`                  |
| `modules/*.conf`                   | `/etc/calamares/modules/`                       |
| `branding/exolyx/`                 | `/usr/share/calamares/branding/exolyx/`         |
| `scripts/nettoyage.sh`, `finalisation.sh` | `/usr/lib/exolyx/calamares/`             |
| `lanceur/exolyx-installer`         | `/usr/bin/exolyx-installer` (sudo -E ou pkexec) |
| `lanceur/exolyx-installer.desktop` | `/usr/share/applications/`                      |
| `lanceur/exolyx-installer-dock.desktop` + `epingler-installateur.sh` | autostart : épingle l'installateur dans le gestionnaire de tâches (live seulement) |
| `outils/generer-images.py`         | régénère les PNG depuis `src/branding/logo.svg` (cairosvg) |
| `outils/capturer-diaporama.py`     | rend `show.qml` hors écran (une capture par diapositive) |

## Séquence d'exécution (ordre et raisons)

```
partition, mount, unpackfs,
shellprocess@nettoyage        ← avant users : supprime l'utilisateur live « exolyx »
machineid, fstab, locale, keyboard, localecfg, luksbootkeyfile, users,
displaymanager, networkcfg, hwclock, services-systemd,
shellprocess@finalisation     ← avant grubcfg/bootloader : modifie /etc/default/grub ;
                                se termine par pacman -Rns calamares exolyx-calamares-config
initcpiocfg,
shellprocess@initramfs        ← garantit les hooks plymouth et grub-btrfs-overlayfs
initcpio, grubcfg, bootloader, umount
```

- `shellprocess@initramfs` est en ligne (pas de script) car le paquet de
  configuration est déjà désinstallé à ce stade.
- `mount.conf` lie `/run/archiso/bootmnt` dans la cible (extraMounts) pour que
  le nettoyage copie `vmlinuz-linux` et les microcodes depuis le support sans
  dépendre de la variable `${ROOT}` de shellprocess.

## À vérifier au premier essai réel

### Clés et formats Calamares (incertitudes 3.3 → 3.4)
1. **partition.conf** : bloc `efi:` (`mountPoint`, `recommendedSize`, `minimumSize`,
   `label`). Si le journal signale ces clés comme inconnues, revenir aux clés
   historiques commentées (`efiSystemPartition`, `efiSystemPartitionSize`).
   Vérifier que la partition EFI créée fait bien 512 Mio et est montée sur `/boot/efi`.
2. **partition.conf** : `luksGeneration: luks1` (GRUB + /boot chiffré). Vérifier
   que GRUB demande la phrase de passe puis que l'initramfs n'en redemande pas
   (fichier clé de `luksbootkeyfile`, clé `luks2Hash` sans effet en LUKS1).
3. **mount.conf** : `options` sous forme de liste et `mountOptions` /
   `ssdOptions` déplacés depuis fstab.conf (format 3.3). Contrôler `/etc/fstab`
   de la cible : `compress=zstd:1,noatime` sur les 5 sous-volumes Btrfs et
   `discard=async` sur SSD ; `subvol=/@snapshots` monté sur `/.snapshots`.
4. **services-systemd.conf** : format `units:` (3.3+). Si refusé, l'ancien
   format est `services:` / `timers:`. Les unités non obligatoires
   (`mandatory: false`) ne doivent qu'avertir si absentes (cups, bluetooth…).
5. **branding.desc** : couleurs en `SidebarBackground/SidebarText/SidebarTextCurrent/SidebarBackgroundCurrent`
   (anciens noms `sidebarXxx` répétés, ignorés). Vérifier la barre latérale :
   fond `#0D1310`, élément courant sur fond `#A8D479`.
6. **welcome.conf** : `internetCheckUrl` en liste (3.3+) ; « internet » et
   « power » non bloquants, « storage » (20 Gio), « ram » (2 Gio) et « root » bloquants.
7. **grubcfg.conf** : `kernel_params: [quiet, splash]` doit produire
   `GRUB_CMDLINE_LINUX_DEFAULT="… quiet splash"` (grubcfg réécrit cette ligne ;
   la finalisation l'a déjà réglée aussi). Vérifier que `GRUB_THEME` posé par
   `appliquer-theme.sh` est **conservé** (`overwrite: false`).
8. **bootloader.conf** : `efiBootloaderId: ExoLyx` → `/boot/efi/EFI/ExoLyx/grubx64.efi`
   + repli `EFI/BOOT/BOOTX64.EFI`. En BIOS, l'effacement complet crée une table
   MBR : vérifier `grub-install --target=i386-pc` sur le disque entier. En BIOS
   + GPT manuel, il faut une partition `bios_grub` (Calamares ne la crée pas).
9. **initcpiocfg** : vérifier dans le journal la ligne `HOOKS=` finale
   (affichée par `shellprocess@initramfs`) : `plymouth` après `udev`,
   pas de `archiso`, `encrypt` si chiffrement, `grub-btrfs-overlayfs` en dernier.
   Selon la version, initcpiocfg ajoute déjà `plymouth` (détection de
   `/usr/bin/plymouth`) ; le script n'ajoute rien dans ce cas.
10. **users.conf** : modèle de nom de machine `${first}-exolyx` (`hostname.template`).
    Vérifier `/etc/sudoers.d/10-installer` (`%wheel ALL=(ALL:ALL) ALL`) et les groupes.
11. **unpackfs.conf** : `/run/archiso/bootmnt/arch/x86_64/airootfs.sfs`. Avec
    l'option de démarrage `copytoram`, le squashfs est dans
    `/run/archiso/copytoram/airootfs.sfs` : l'installation échouerait (ne pas
    proposer copytoram, ou ajouter une seconde configuration).
12. **finished.conf** : `restartNowMode: user-checked`, `notifyOnFinished`.
13. **shellprocess** : commandes exécutées via `sh -c` dans le chroot ; le préfixe
    `-` rend un échec non bloquant. Le nettoyage et la finalisation sont, eux,
    bloquants si le script renvoie ≠ 0 (ils terminent toujours par `exit 0`).
14. **locale** : pas de géolocalisation ; LANG devrait valoir `fr_FR.UTF-8`
    (langue de l'interface = fr + zone Europe/Paris). Vérifier `/etc/locale.conf`
    et que `fr_FR.UTF-8` est décommenté dans `/etc/locale.gen`.
15. **keyboard** : la disposition proposée doit être `fr` (devinée depuis la
    session live). Vérifier `/etc/vconsole.conf` (`KEYMAP=fr…`) et
    `/etc/X11/xorg.conf.d/00-keyboard.conf`.

### Nettoyage du live (`scripts/nettoyage.sh`)
- Utilisateur `exolyx` (uid 1000) supprimé, y compris des listes de membres
  de `/etc/group` et `/etc/gshadow` ; le compte créé ensuite reçoit l'uid 1000.
- Fichiers supprimés : autologin SDDM (`/etc/sddm.conf.d/20-autologin-live.conf`),
  `sudoers.d/10-exolyx-live`, `polkit-1/rules.d/49-exolyx-live.rules`,
  `tmpfiles.d/exolyx-live.conf`, `mkinitcpio.conf.d/archiso.conf`, autologin
  getty, `/root/.automated_script.sh`, `/root/.zlogin`, `pacman-init.service`,
  `choose-mirror.service`, `livecd-*` (+ liens), `/etc/motd`, et par sécurité
  `etc-pacman.d-gnupg.mount` (tmpfs du trousseau), `journald` volatile,
  `logind do-not-suspend`, `sshd 10-archiso`.
- `mkinitcpio-archiso` retiré (`-Rdd`) ; preset `linux.preset` réécrit au format Arch standard.
- **À vérifier** : `find /etc/systemd/system -xtype l -delete` supprime les liens
  devenus orphelins — contrôler qu'aucun lien légitime (pointant vers une unité
  absente au moment de l'installation) n'est supprimé.

### Finalisation (`scripts/finalisation.sh`)
- Trousseau pacman initialisé (`pacman-key --init --populate archlinux`) car le
  live le garde en tmpfs. **Si le dépôt [exolyx] est signé un jour, importer sa
  clé ici.**
- Dépôt `[exolyx]` : seulement vérifié (ajouté par le post_install de
  `exolyx-system`) ; ajout de secours identique s'il manque.
- snapper : `create-config` en `--no-dbus` (pas de D-Bus dans le chroot), le
  sous-volume `.snapshots` créé par snapper est remplacé par `@snapshots`
  (remonté). Limites : 5 horaires, 7 jours, 2 semaines, 1 mois, 10 instantanés
  « number » ; `ALLOW_GROUPS=wheel` (permet `snapper list` à l'utilisateur,
  utilisé par exolyx-maj) ; quotas Btrfs + `setup-quota`.
  **À vérifier** : `snapper list` après le premier démarrage, présence du
  sous-menu « Instantanés ExoLyx » dans GRUB après une mise à jour
  (`grub-btrfsd` nécessite `inotify-tools`, à inclure dans l'ISO).
- ufw : édition de `/etc/default/ufw` et `/etc/ufw/ufw.conf` (`ENABLED=yes`)
  au lieu de `ufw enable` (qui agirait sur le noyau du live). Vérifier
  `sudo ufw status verbose` après démarrage : « deny (incoming), allow (outgoing) ».
- Plymouth : `plymouth-set-default-theme exolyx` (sans `-R`, l'initramfs est
  régénéré par le module initcpio).
- GRUB : `quiet splash`, `GRUB_DISABLE_OS_PROBER=false` si os-prober est présent,
  puis `/usr/share/exolyx/grub/appliquer-theme.sh` (**ne doit pas** lancer
  `grub-mkconfig` dans un chemin non monté ; le module bootloader génère grub.cfg).
- `zram-generator.conf` et `/etc/os-release` sont fournis par `exolyx-system`.
- Dernière commande : `SNAP_PAC_SKIP=y pacman -Rns --noconfirm calamares
  exolyx-calamares-config`. **Ce paquet ne doit dépendre que de calamares** :
  toute autre dépendance (snapper, grub-btrfs…) serait retirée par `-s`.
  Tous les paquets système doivent être listés explicitement dans
  `archiso/packages.x86_64`.

### Paquets nécessaires sur l'ISO (copiés tels quels dans la cible)
`calamares`, `ckbcomp` (fourni par le build), `btrfs-progs`, `grub`, `efibootmgr`,
`os-prober`, `snapper`, `snap-pac`, `grub-btrfs`, `inotify-tools`, `ufw`,
`plymouth`, `zram-generator`, `squashfs-tools`, `arch-install-scripts`,
`sudo`, `polkit`, `qt6-svg` (logo SVG), `noto-fonts`/`inter-font`.

### Lancement
- `exolyx-installer` : `sudo -E` (live : sudo sans mot de passe via
  `10-exolyx-live`), sinon `pkexec env DISPLAY=… WAYLAND_DISPLAY=… XDG_RUNTIME_DIR=…`.
  Sous Wayland, Calamares tourne en root sur le socket de l'utilisateur
  (avertissement Qt « runtime directory not owned by root » attendu, sans gravité).
- Épinglage dans le panneau : script Plasma via `qdbus6 … evaluateScript`
  (widgets `icontasks`/`taskmanager`) ; vérifier le nom réel du widget dans
  la mise en page `org.exolyx.sombre`.

### Diaporama
`show.qml` est autonome (n'importe que QtQuick, API 2 : `onActivate()` /
`onLeave()`), testé hors écran avec Qt 6 (aucun avertissement). Captures :
`outils/capturer-diaporama.py <dossier>`.
