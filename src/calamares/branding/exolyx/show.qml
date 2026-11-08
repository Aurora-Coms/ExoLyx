/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Diaporama ExoLyx affiché pendant l'installation (Calamares 3.3, Qt 6).
 * Autonome : n'importe que QtQuick (pas de module calamares.slideshow),
 * ce qui permet aussi de le tester hors de Calamares.
 * API 2 : Calamares appelle onActivate() / onLeave().
 */
import QtQuick

Rectangle {
    id: racine
    color: "#0D1310"
    implicitWidth: 820
    implicitHeight: 460

    // ---- API Calamares --------------------------------------------------
    property bool actif: true
    property int courant: 0
    readonly property int nombre: diapos.length
    function onActivate() { actif = true; courant = 0 }
    function onLeave() { actif = false }

    // ---- Palette (src/branding/palette.md, sombre) ------------------------
    readonly property color accent: "#A8D479"
    readonly property color accentClair: "#BDD479"
    readonly property color accentFroid: "#8DD479"
    readonly property color surface: "#141C17"
    readonly property color surfaceHaute: "#1C2620"
    readonly property color bordure: "#2A362E"
    readonly property color texte: "#E6EFE1"
    readonly property color texteDoux: "#97A893"
    readonly property color info: "#79C2D4"
    readonly property color attention: "#E8C26A"
    readonly property real echelle: Math.min(width / 820, height / 460)

    readonly property var diapos: [
        { titre: "Bienvenue dans ExoLyx",
          texte: "Merci d'avoir choisi ExoLyx ! Pendant que l'installation se poursuit, découvrez ce qui vous attend : un bureau KDE Plasma moderne, rapide et entièrement en français." },
        { titre: "Vos fichiers, bien rangés",
          texte: "Le gestionnaire de fichiers Dolphin ouvre vos documents, photos et clés USB en un clic. Onglets, aperçus et recherche instantanée sont inclus." },
        { titre: "Instantanés et sécurité",
          texte: "Avant et après chaque mise à jour, ExoLyx crée un instantané du système. Un souci ? Redémarrez sur « Instantanés ExoLyx » dans le menu de démarrage. Le pare-feu est activé dès le départ." },
        { titre: "Des milliers d'applications",
          texte: "Discover installe et met à jour vos logiciels, y compris ceux de Flathub (Steam, Spotify, Discord…). Les mises à jour se font ensuite en un clic." },
        { titre: "À votre image",
          texte: "Thème sombre ou clair, fonds d'écran, trois styles d'icônes : l'appli de bienvenue vous guidera au premier démarrage pour tout régler." }
    ]

    Timer {
        interval: 9000
        repeat: true
        running: racine.actif
        onTriggered: racine.courant = (racine.courant + 1) % racine.nombre
    }

    // Halo d'ambiance
    Rectangle {
        width: parent.width * 0.9; height: width; radius: width / 2
        x: parent.width * 0.42; y: -height * 0.35
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#1A2A1C" }
            GradientStop { position: 1.0; color: "#0D1310" }
        }
        opacity: 0.8
    }

    Repeater {
        model: racine.nombre
        delegate: Item {
            id: diapo
            required property int index
            anchors.fill: parent
            opacity: racine.courant === index ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 600; easing.type: Easing.InOutQuad } }

            // Colonne de texte
            Column {
                x: 48 * racine.echelle
                width: parent.width * 0.44
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -12 * racine.echelle
                spacing: 16 * racine.echelle

                Text {
                    text: (diapo.index + 1) + " / " + racine.nombre
                    color: racine.accent
                    font.family: "Inter"; font.pixelSize: 14 * racine.echelle; font.weight: Font.DemiBold
                    font.letterSpacing: 1
                }
                Text {
                    width: parent.width
                    text: racine.diapos[diapo.index].titre
                    color: racine.texte
                    wrapMode: Text.WordWrap
                    font.family: "Inter"; font.pixelSize: 32 * racine.echelle; font.weight: Font.Bold
                }
                Rectangle { width: 48 * racine.echelle; height: 4 * racine.echelle; radius: 2; color: racine.accent }
                Text {
                    width: parent.width
                    text: racine.diapos[diapo.index].texte
                    color: racine.texteDoux
                    wrapMode: Text.WordWrap
                    lineHeight: 1.25
                    font.family: "Inter"; font.pixelSize: 16 * racine.echelle
                }
            }

            // Illustration
            Item {
                id: zone
                x: parent.width * 0.52
                width: parent.width * 0.44
                height: parent.height * 0.72
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -12 * racine.echelle

                Loader {
                    anchors.fill: parent
                    sourceComponent: [illusBienvenue, illusFichiers, illusInstantanes, illusApplis, illusPerso][diapo.index]
                }
            }
        }
    }

    // Points de navigation
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18 * racine.echelle
        spacing: 10
        Repeater {
            model: racine.nombre
            delegate: Rectangle {
                required property int index
                width: racine.courant === index ? 26 : 10
                height: 10; radius: 5
                color: racine.courant === index ? racine.accent : racine.bordure
                Behavior on width { NumberAnimation { duration: 250 } }
                MouseArea { anchors.fill: parent; anchors.margins: -4; onClicked: racine.courant = parent.index }
            }
        }
    }

    // ---- Illustrations ----------------------------------------------------
    Component {
        id: illusBienvenue
        Item {
            Image {
                anchors.centerIn: parent
                width: Math.min(parent.width, parent.height) * 0.95; height: width
                source: "logo-diapo.png"
                fillMode: Image.PreserveAspectFit
                smooth: true; mipmap: true
            }
        }
    }

    // Fenêtre type « gestionnaire de fichiers »
    Component {
        id: illusFichiers
        Rectangle {
            radius: 14; color: racine.surface; border.color: racine.bordure
            Rectangle { // barre de titre
                width: parent.width; height: 34; radius: 14; color: racine.surfaceHaute
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 14; color: racine.surfaceHaute }
                Row {
                    x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 6
                    Repeater { model: 3; Rectangle { width: 10; height: 10; radius: 5; color: racine.bordure } }
                }
                Rectangle { x: parent.width * 0.28; width: parent.width * 0.5; height: 18; radius: 6
                    anchors.verticalCenter: parent.verticalCenter; color: racine.surface
                    Text { x: 8; anchors.verticalCenter: parent.verticalCenter; text: "Dossier personnel"; color: racine.texteDoux; font.family: "Inter"; font.pixelSize: 10 } }
            }
            Column { // panneau latéral
                x: 12; y: 48; spacing: 9
                Repeater {
                    model: ["Accueil", "Documents", "Images", "Musique", "Téléchargements"]
                    Row {
                        required property string modelData
                        required property int index
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 3; color: parent.index === 0 ? racine.accent : racine.texteDoux; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: parent.modelData; color: parent.index === 0 ? racine.texte : racine.texteDoux; font.family: "Inter"; font.pixelSize: 11 }
                    }
                }
            }
            Grid { // dossiers
                x: parent.width * 0.38; y: 52
                columns: 3; columnSpacing: parent.width * 0.045; rowSpacing: 16
                Repeater {
                    model: ["Bureau", "Documents", "Images", "Musique", "Vidéos", "Modèles"]
                    Column {
                        required property string modelData
                        spacing: 4
                        Item {
                            width: 46; height: 36
                            Rectangle { width: 20; height: 8; radius: 3; color: racine.accentFroid }
                            Rectangle { y: 4; width: 46; height: 32; radius: 5
                                gradient: Gradient {
                                    GradientStop { position: 0; color: racine.accentClair }
                                    GradientStop { position: 1; color: racine.accentFroid }
                                } }
                        }
                        Text { text: parent.modelData; color: racine.texte; font.family: "Inter"; font.pixelSize: 10; width: 62; x: -8; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                    }
                }
            }
        }
    }

    // Frise d'instantanés + bouclier
    Component {
        id: illusInstantanes
        Item {
            Rectangle {
                id: frise
                width: parent.width; height: parent.height * 0.62
                radius: 14; color: racine.surface; border.color: racine.bordure
                Text { x: 16; y: 12; text: "Instantanés ExoLyx"; color: racine.texte; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.DemiBold }
                Rectangle { x: 26; y: 52; width: 3; height: parent.height - 66; color: racine.bordure }
                Column {
                    x: 20; y: 46; spacing: 10
                    Repeater {
                        model: [ { t: "Après mise à jour", h: "aujourd'hui 10:42" },
                                 { t: "Avant mise à jour", h: "aujourd'hui 10:40" },
                                 { t: "Instantané horaire", h: "aujourd'hui 09:00" } ]
                        Row {
                            required property var modelData
                            required property int index
                            spacing: 12
                            Rectangle { width: 15; height: 15; radius: 8; color: parent.index === 0 ? racine.accent : racine.surfaceHaute; border.color: racine.accent; border.width: 2; anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                Text { text: parent.parent.modelData.t; color: racine.texte; font.family: "Inter"; font.pixelSize: 12 }
                                Text { text: parent.parent.modelData.h; color: racine.texteDoux; font.family: "Inter"; font.pixelSize: 10 }
                            }
                        }
                    }
                }
            }
            Rectangle {
                anchors.top: frise.bottom; anchors.topMargin: 14
                width: parent.width; height: parent.height - frise.height - 14
                radius: 14; color: racine.surface; border.color: racine.bordure
                Row {
                    anchors.verticalCenter: parent.verticalCenter; x: 16; spacing: 14
                    Item { // bouclier
                        width: 34; height: 40; anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: 34; height: 26; radius: 6; color: racine.accent }
                        Rectangle { x: 7; y: 14; width: 20; height: 20; rotation: 45; color: racine.accent }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 4; text: "✓"; color: "#0D1310"; font.pixelSize: 18; font.bold: true }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: "Pare-feu actif"; color: racine.texte; font.family: "Inter"; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Text { text: "Connexions entrantes bloquées"; color: racine.texteDoux; font.family: "Inter"; font.pixelSize: 11 }
                    }
                }
            }
        }
    }

    // Grille d'applications
    Component {
        id: illusApplis
        Rectangle {
            id: cadreApplis
            radius: 14; color: racine.surface; border.color: racine.bordure
            Text { x: 16; y: 14; text: "Discover"; color: racine.texte; font.family: "Inter"; font.pixelSize: 14; font.weight: Font.DemiBold }
            Rectangle { x: parent.width - 96; y: 12; width: 80; height: 20; radius: 6; color: racine.surfaceHaute
                Text { anchors.centerIn: parent; text: "Flathub"; color: racine.accent; font.family: "Inter"; font.pixelSize: 10 } }
            Grid {
                x: 16; y: 46; columns: 2; columnSpacing: 12; rowSpacing: 10
                Repeater {
                    model: [ { n: "LibreOffice", c: "#79C2D4" }, { n: "Steam", c: "#8DD479" },
                             { n: "VLC", c: "#E8C26A" }, { n: "Spotify", c: "#A8D479" },
                             { n: "GIMP", c: "#BDD479" }, { n: "Krita", c: "#E5766B" },
                             { n: "Discord", c: "#79C2D4" }, { n: "OBS Studio", c: "#97A893" } ]
                    Rectangle {
                        required property var modelData
                        width: (cadreApplis.width - 44) / 2; height: (cadreApplis.height - 46 - 16 - 30) / 4; radius: 10; color: racine.surfaceHaute
                        Rectangle { x: 8; anchors.verticalCenter: parent.verticalCenter; width: 26; height: 26; radius: 7; color: parent.modelData.c
                            Text { anchors.centerIn: parent; text: parent.parent.modelData.n.charAt(0); color: "#0D1310"; font.family: "Inter"; font.bold: true; font.pixelSize: 13 } }
                        Text { x: 42; anchors.verticalCenter: parent.verticalCenter; text: parent.modelData.n; color: racine.texte; font.family: "Inter"; font.pixelSize: 11 }
                    }
                }
            }
        }
    }

    // Sombre / clair + pastilles de couleur
    Component {
        id: illusPerso
        Item {
            Rectangle { // aperçu sombre
                width: parent.width * 0.62; height: parent.height * 0.62
                radius: 14; color: "#141C17"; border.color: racine.bordure
                Rectangle { width: parent.width; height: 26; radius: 14; color: "#1C2620"
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 12; color: "#1C2620" } }
                Column { x: 14; y: 40; spacing: 8
                    Rectangle { width: 90; height: 10; radius: 5; color: "#E6EFE1" }
                    Rectangle { width: 120; height: 8; radius: 4; color: "#97A893" }
                    Rectangle { width: 70; height: 22; radius: 6; color: "#A8D479" } }
                Text { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10; text: "Sombre"; color: "#97A893"; font.family: "Inter"; font.pixelSize: 11 }
            }
            Rectangle { // aperçu clair
                x: parent.width * 0.34; y: parent.height * 0.24
                width: parent.width * 0.62; height: parent.height * 0.62
                radius: 14; color: "#F4F8F1"; border.color: "#D3DECB"
                Rectangle { width: parent.width; height: 26; radius: 14; color: "#E9F0E4"
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 12; color: "#E9F0E4" } }
                Column { x: 14; y: 40; spacing: 8
                    Rectangle { width: 90; height: 10; radius: 5; color: "#16201A" }
                    Rectangle { width: 120; height: 8; radius: 4; color: "#5B6B57" }
                    Rectangle { width: 70; height: 22; radius: 6; color: "#5E9B2E" } }
                Text { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 10; text: "Clair"; color: "#5B6B57"; font.family: "Inter"; font.pixelSize: 11 }
            }
            Row {
                anchors.bottom: parent.bottom; spacing: 10
                Repeater {
                    model: ["Trait", "Duo", "Relief"]
                    Rectangle {
                        required property string modelData
                        required property int index
                        width: 64; height: 26; radius: 13
                        color: index === 0 ? racine.accent : racine.surfaceHaute
                        border.color: racine.bordure
                        Text { anchors.centerIn: parent; text: parent.modelData; color: parent.index === 0 ? "#0D1310" : racine.texte; font.family: "Inter"; font.pixelSize: 11 }
                    }
                }
            }
        }
    }
}
