# Conventions du dépôt ExoLyx

## Arborescence
```
archiso/            profil mkarchiso (basé sur releng)
packages/<nom>/     un PKGBUILD par paquet ExoLyx
src/<composant>/    sources de chaque composant (thèmes, applis…)
src/branding/       logo.svg + palette.md : SOURCE DE VÉRITÉ des couleurs
scripts/            build-packages.sh, build-iso.sh
vm/                 création de la machine virtuelle VirtualBox
.github/workflows/  build automatique de l'ISO
```

## PKGBUILD
- Les sources sont locales : `package()` copie depuis `"$startdir/../../src/<composant>"`.
- `pkgver=1.0.0`, `pkgrel=1`, `arch=('any')` sauf binaire compilé, `license=('GPL-3.0-or-later')`.
- `url="https://github.com/Aurora-Coms/ExoLyx"`, `maintainer` : A.DERBEZ.
- Aucune étape réseau dans `package()`.
- Le CI exécute `makepkg -s --noconfirm` (utilisateur non-root) dans `packages/<nom>/`.

## Applis maison (Python)
- Python 3 + PyQt6 + QML (QtQuick.Controls « Basic » stylé à la main, pas de thème Qt externe).
- Installées dans `/usr/share/exolyx/<appli>/`, lanceur `/usr/bin/exolyx-<appli>`, fichier `.desktop`
  dans `/usr/share/applications/` avec `Name=` en français.
- Textes de l'interface en français.
- Thème sombre/clair : lire `~/.config/kdeglobals` → `[General] ColorScheme` (contient « Clair » = clair),
  sinon sombre.

## Couleurs
Toujours celles de `src/branding/palette.md`. Accent sombre `#A8D479`, fond `#0D1310`.

## SVG
Pas de filtres SVG (`<filter>`), compatibles QtSvg (Tiny 1.2 au mieux) : dégradés linéaires/radiaux, chemins, opacité.
