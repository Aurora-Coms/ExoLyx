// Disposition ExoLyx : un dock flottant centré en bas de l'écran
var panneau = new Panel;
panneau.location = "bottom";
panneau.height = 2 * Math.floor(gridUnit * 2.8 / 2);
try { panneau.floating = true; } catch (e) {}
try { panneau.lengthMode = "fit"; } catch (e) {}
try { panneau.alignment = "center"; } catch (e) {}
try { panneau.hiding = "dodgewindows"; } catch (e) {}

var menu = panneau.addWidget("org.kde.plasma.kickoff");
menu.currentConfigGroup = ["General"];
menu.writeConfig("icon", "start-here-kde-plasma");
menu.writeConfig("favoritesPortedToKAstats", "true");

var lanceurs = [];
if (applicationExists("exolyx-installer.desktop")) lanceurs.push("applications:exolyx-installer.desktop");
lanceurs = lanceurs.concat([
    "applications:org.gnome.Nautilus.desktop",
    "applications:firefox.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:org.kde.discover.desktop",
    "applications:systemsettings.desktop"
]);
var taches = panneau.addWidget("org.kde.plasma.icontasks");
taches.currentConfigGroup = ["General"];
taches.writeConfig("launchers", lanceurs);
taches.writeConfig("showOnlyCurrentDesktop", "false");

panneau.addWidget("org.kde.plasma.marginsseparator");
panneau.addWidget("org.kde.plasma.systemtray");
var horloge = panneau.addWidget("org.kde.plasma.digitalclock");
horloge.currentConfigGroup = ["Appearance"];
horloge.writeConfig("showDate", "true");
horloge.writeConfig("dateFormat", "shortDate");
panneau.addWidget("org.kde.plasma.showdesktop");

// Fond d'écran
var bureaux = desktops();
for (var i = 0; i < bureaux.length; i++) {
    var b = bureaux[i];
    b.wallpaperPlugin = "org.kde.image";
    b.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    b.writeConfig("Image", "file:///usr/share/wallpapers/ExoLyx-Clair/");
}
