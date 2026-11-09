# ExoLyx

Distribution Linux basée sur **Arch Linux** et **KDE Plasma 6**, entièrement en français, avec une identité visuelle vert pomme.

## Télécharger l'ISO
Onglet **Actions** → dernier build « Construire l'ISO ExoLyx » réussi → *Artifacts* → **exolyx-iso**.
Chaque modification envoyée sur `main` reconstruit l'ISO automatiquement (≈ 1 h).

## Tester dans VirtualBox
Voir [`vm/LISEZMOI.md`](vm/LISEZMOI.md) : double-clic sur `vm/creer-vm.bat`.

## Clé USB bootable
Rufus (Windows, mode **DD**), Ventoy, ou `dd` sous Linux.

## Contenu
| Composant | Paquet | Sources |
|---|---|---|
| Réglages système (identité, dépôt, zram) | `exolyx-system` | `src/systeme` |
| Apparence Plasma sombre/clair, Konsole | `exolyx-theme` | `src/theme` |
| Fonds d'écran | `exolyx-wallpapers` | `src/wallpapers` |
| Icônes (Trait / Duo / Relief) | `exolyx-icons` | `src/icones` |
| Curseur | `exolyx-cursors` | `src/curseurs` |
| Sons | `exolyx-sounds` | `src/sons` |
| Écran de connexion | `exolyx-sddm` | `src/sddm` |
| Démarrage (Plymouth) | `exolyx-plymouth` | `src/plymouth` |
| Menu de démarrage (GRUB) | `exolyx-grub-theme` | `src/grub` |
| Appli de **Bienvenue** | `exolyx-bienvenue` | `src/bienvenue` |
| **Mises à jour** en un clic | `exolyx-maj` | `src/maj` |
| Couleurs ExoLyx dans GNOME Files / GTK 4 | `exolyx-gtk` | `src/gtk` |
| Firefox (accueil, réglages), Kate, invite du terminal | `exolyx-applis` | `src/applis` |
| Installateur (Calamares) | `exolyx-calamares-config` | `src/calamares` |

Explorateur de fichiers : **GNOME Files** (Nautilus).

Système installé : Btrfs + instantanés automatiques (snapper, snap-pac, grub-btrfs), zram, pare-feu ufw, Plymouth.

## Construire soi-même (sous Arch)
```bash
sudo scripts/build-packages.sh   # paquets AUR + ExoLyx → ./depot
sudo scripts/build-iso.sh        # ISO → ./sortie
```
