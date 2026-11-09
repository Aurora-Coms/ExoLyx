// SPDX-License-Identifier: GPL-3.0-or-later
// Style des applications — Ardoise (ExoLyx) ou d'origine.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: fen
    width: 840; height: 720
    minimumWidth: 640; minimumHeight: 560
    visible: true
    title: "Style des applications"

    SystemPalette { id: sp; colorGroup: SystemPalette.Active }
    readonly property bool sombre: sp.window.hslLightness < 0.5
    readonly property color fond: sp.window
    readonly property color surface: sombre ? Qt.lighter(sp.window, 1.18) : Qt.darker(sp.window, 1.03)
    readonly property color bord: Qt.rgba(sp.windowText.r, sp.windowText.g, sp.windowText.b, 0.14)
    readonly property color texte: sp.windowText
    readonly property color doux: Qt.rgba(sp.windowText.r, sp.windowText.g, sp.windowText.b, 0.62)
    readonly property color accent: sp.highlight
    color: fond
    font.family: "Inter"

    // Aperçu miniature d'une fenêtre de logiciel
    component Apercu: Rectangle {
        id: ap
        property color f: "#1e1f22"; property color p: "#2b2d30"; property color b: "#393b40"
        property color t: "#dfe1e5"; property color a: "#e8803a"; property color sel: "#2e436e"
        property bool dense: true
        radius: dense ? 4 : 8; color: f; border.color: b; clip: true
        Column {
            anchors.fill: parent
            Rectangle { width: parent.width; height: 16; color: ap.p
                Row { x: 8; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                    Repeater { model: 3; Rectangle { width: 6; height: 6; radius: 3; color: ap.t; opacity: 0.35 } } } }
            Row { width: parent.width; height: 18; spacing: 2; leftPadding: 6
                Repeater { model: ["accueil.py", "config.toml"]
                    Rectangle { width: 64; height: 16; y: 2; color: index === 0 ? ap.f : "transparent"
                        Text { anchors.centerIn: parent; text: modelData; color: ap.t; font.pixelSize: 8; opacity: index === 0 ? 1 : 0.6 }
                        Rectangle { visible: index === 0; anchors.bottom: parent.bottom; width: parent.width; height: 2; color: ap.a } } } }
            Rectangle { width: parent.width; height: 1; color: ap.b }
            Row { width: parent.width; height: parent.height - 35
                Rectangle { width: parent.width * 0.3; height: parent.height; color: ap.p
                    Column { x: 6; y: 6; spacing: ap.dense ? 3 : 6
                        Repeater { model: 4
                            Rectangle { width: (parent.parent.width - 12); height: ap.dense ? 9 : 12; radius: ap.dense ? 2 : 6
                                color: index === 1 ? ap.sel : "transparent"
                                Rectangle { x: 4; anchors.verticalCenter: parent.verticalCenter; width: parent.width * (0.7 - index * 0.1); height: 3; radius: 1.5; color: ap.t; opacity: 0.55 } } } } }
                Column { x: 8; y: 8; spacing: ap.dense ? 4 : 7; leftPadding: 8; topPadding: 8
                    Repeater { model: [0.8, 0.55, 0.7, 0.4, 0.62]
                        Rectangle { width: (ap.width * 0.6) * modelData; height: 3; radius: 1.5; color: index === 1 ? ap.a : ap.t; opacity: index === 1 ? 0.9 : 0.45 } } } }
        }
    }

    // Carte de choix du style
    component CarteStyle: Rectangle {
        id: carte
        property string cle; property string titre; property string detail
        default property alias apercu: zoneApercu.data
        readonly property bool choisi: ctrl.style === cle
        Layout.fillWidth: true; Layout.preferredHeight: 250
        radius: 10; color: fen.surface
        border.width: choisi ? 2 : 1; border.color: choisi ? fen.accent : (zone.containsMouse ? fen.doux : fen.bord)
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 10
            Item { id: zoneApercu; Layout.fillWidth: true; Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; spacing: 8
                Rectangle { width: 18; height: 18; radius: 9; color: carte.choisi ? fen.accent : "transparent"; border.color: carte.choisi ? fen.accent : fen.doux; border.width: 1.5
                    Rectangle { anchors.centerIn: parent; width: 7; height: 7; radius: 3.5; color: sp.highlightedText; visible: carte.choisi } }
                Text { text: carte.titre; color: fen.texte; font.pixelSize: 15; font.weight: Font.DemiBold }
            }
            Text { text: carte.detail; color: fen.doux; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
        MouseArea { id: zone; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: ctrl.choisirStyle(carte.cle) }
        Accessible.role: Accessible.RadioButton; Accessible.name: titre; Accessible.checked: choisi
    }

    ScrollView {
        anchors.fill: parent; anchors.bottomMargin: pied.height
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 18
            Item { Layout.preferredHeight: 6 }
            ColumnLayout { Layout.leftMargin: 24; Layout.rightMargin: 24; spacing: 4
                Text { text: "Style des applications"; color: fen.texte; font.pixelSize: 22; font.weight: Font.Bold }
                Text { text: "Choisissez l'interface des logiciels de base : le style Ardoise d'ExoLyx, ou leur interface d'origine qui suit les couleurs du bureau. GNOME Files n'est pas concerné."
                       color: fen.doux; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
            RowLayout { Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.fillWidth: true; spacing: 14
                CarteStyle { cle: "ardoise"; titre: "Ardoise (ExoLyx)"; detail: "Anthracite dense, accent orange, sélection bleu nuit. Ne change pas avec le fond d'écran."
                    Apercu { anchors.fill: parent } }
                CarteStyle { cle: "origine"; titre: "D'origine"; detail: "L'interface de base de chaque logiciel, aux couleurs du bureau (thème ExoLyx ou teintes dynamiques)."
                    Apercu { anchors.fill: parent; dense: false; f: sp.base; p: sp.window; b: fen.bord; t: sp.text; a: sp.highlight; sel: Qt.rgba(sp.highlight.r, sp.highlight.g, sp.highlight.b, 0.3) } }
            }
            ColumnLayout { Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.fillWidth: true; spacing: 8
                opacity: ctrl.style === "ardoise" ? 1 : 0.45
                Text { text: "Logiciels en style Ardoise"; color: fen.texte; font.pixelSize: 15; font.weight: Font.DemiBold }
                Text { text: ctrl.style === "ardoise" ? "Décochez un logiciel pour lui laisser son interface d'origine." : "Choisissez Ardoise pour régler logiciel par logiciel."
                       color: fen.doux; font.pixelSize: 12 }
                GridLayout { columns: fen.width > 720 ? 2 : 1; columnSpacing: 10; rowSpacing: 6; Layout.fillWidth: true
                    Repeater { model: ctrl.applis
                        Rectangle { Layout.fillWidth: true; height: 40; radius: 8; color: fen.surface; border.color: fen.bord
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 10
                                Image { source: "image://icone/" + modelData.icone; sourceSize: Qt.size(24, 24); Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
                                Text { text: modelData.nom; color: fen.texte; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                                Rectangle { // interrupteur
                                    width: 36; height: 20; radius: 10
                                    color: modelData.coche ? fen.accent : Qt.rgba(fen.texte.r, fen.texte.g, fen.texte.b, 0.18)
                                    Rectangle { width: 16; height: 16; radius: 8; y: 2; x: modelData.coche ? 18 : 2; color: modelData.coche ? sp.highlightedText : fen.fond
                                        Behavior on x { NumberAnimation { duration: 120 } } } }
                            }
                            MouseArea { anchors.fill: parent; enabled: ctrl.style === "ardoise"; cursorShape: Qt.PointingHandCursor; onClicked: ctrl.basculer(modelData.id) }
                            Accessible.role: Accessible.CheckBox; Accessible.name: modelData.nom; Accessible.checked: modelData.coche
                        } } }
            }
            Item { Layout.preferredHeight: 8 }
        }
    }

    // Pied : message + actions
    Rectangle {
        id: pied
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 60; color: fen.surface
        Rectangle { width: parent.width; height: 1; color: fen.bord }
        RowLayout { anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 24; spacing: 10
            Text { text: ctrl.message; color: fen.doux; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Button { id: bRetablir; text: "Rétablir par défaut"; enabled: !ctrl.parDefaut; onClicked: ctrl.retablir()
                contentItem: Text { text: bRetablir.text; color: fen.texte; opacity: bRetablir.enabled ? 1 : 0.4; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { implicitWidth: 150; implicitHeight: 34; radius: 6; color: bRetablir.hovered ? Qt.rgba(fen.texte.r, fen.texte.g, fen.texte.b, 0.08) : "transparent"; border.color: fen.bord } }
            Button { id: bAppliquer; text: "Appliquer"; enabled: ctrl.modifie; onClicked: ctrl.appliquer()
                contentItem: Text { text: bAppliquer.text; color: sp.highlightedText; font.pixelSize: 13; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { implicitWidth: 120; implicitHeight: 34; radius: 6; color: fen.accent; opacity: bAppliquer.enabled ? 1 : 0.4 } }
        }
    }
}
