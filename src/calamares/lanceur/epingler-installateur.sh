#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Mode live uniquement : épingle « Installer ExoLyx » en tête du gestionnaire
# de tâches du panneau Plasma (lanceur « applications:exolyx-installer.desktop »).
# Lancé par /etc/xdg/autostart/exolyx-installer-dock.desktop.
set -u
[ -d /run/archiso ] || exit 0

SCRIPT='
const lanceur = "applications:exolyx-installer.desktop";
for (const p of panels()) {
    for (const w of p.widgets()) {
        if (w.type !== "org.kde.plasma.icontasks" && w.type !== "org.kde.plasma.taskmanager") continue;
        w.currentConfigGroup = ["General"];
        let l = w.readConfig("launchers", []);
        if (typeof l === "string") l = l.length ? l.split(",") : [];
        if (l.indexOf(lanceur) === -1) {
            l.unshift(lanceur);
            w.writeConfig("launchers", l);
            w.reloadConfig();
        }
    }
}'

# plasmashell peut ne pas être prêt immédiatement : quelques essais.
for _ in 1 2 3 4 5 6 7 8 9 10; do
    for q in qdbus6 qdbus; do
        command -v "$q" >/dev/null || continue
        if "$q" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "$SCRIPT" >/dev/null 2>&1; then
            exit 0
        fi
    done
    sleep 2
done
exit 0
