import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Paramètres de l'appli
Flickable {
    id: page
    contentHeight: colonne.implicitHeight + 48
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: BarreDefilement {}

    component Section: Text {
        font.pixelSize: 15
        font.weight: Font.DemiBold
        color: theme.texte
        Layout.topMargin: 14
    }

    component Ligne: Rectangle {
        id: ligne
        property string titre
        property string detail
        default property alias controle: emplacement.data
        Layout.fillWidth: true
        implicitHeight: 62
        radius: 10
        color: theme.surface
        border.color: theme.bordure
        ColumnLayout {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.right: emplacement.left
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Text { text: ligne.titre; font.pixelSize: 13; font.weight: Font.Medium; color: theme.texte; Layout.fillWidth: true; elide: Text.ElideRight }
            Text { text: ligne.detail; visible: text !== ""; font.pixelSize: 12; color: theme.texteDoux; Layout.fillWidth: true; elide: Text.ElideRight }
        }
        Row {
            id: emplacement
            anchors.right: parent.right
            anchors.rightMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
        }
    }

    component Interrupteur: Rectangle {
        id: inter
        property bool coche: false
        signal bascule()
        width: 42; height: 24; radius: 12
        color: coche ? theme.accent : theme.bordure
        Behavior on color { ColorAnimation { duration: 120 } }
        Rectangle {
            width: 18; height: 18; radius: 9
            y: 3
            x: inter.coche ? inter.width - width - 3 : 3
            color: inter.coche ? theme.surAccent : theme.texte
            Behavior on x { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        }
        MouseArea { anchors.fill: parent; onClicked: inter.bascule() }
    }

    component Segments: Row {
        id: segs
        property var options: []     // [{texte, valeur}]
        property string valeur
        signal choisi(string v)
        spacing: 0
        Repeater {
            model: segs.options
            delegate: Rectangle {
                required property var modelData
                required property int index
                readonly property bool actif: segs.valeur === modelData.valeur
                width: texteSeg.implicitWidth + 26
                height: 30
                radius: 6
                color: actif ? Qt.alpha(theme.accent, 0.18) : zoneSeg.containsMouse ? theme.surfaceHaute : "transparent"
                border.color: actif ? theme.accent : theme.bordure
                Text {
                    id: texteSeg
                    anchors.centerIn: parent
                    text: parent.modelData.texte
                    font.pixelSize: 13
                    font.weight: parent.actif ? Font.DemiBold : Font.Normal
                    color: parent.actif ? theme.texte : theme.texteDoux
                }
                MouseArea { id: zoneSeg; anchors.fill: parent; hoverEnabled: true; onClicked: segs.choisi(parent.modelData.valeur) }
            }
        }
    }

    ColumnLayout {
        id: colonne
        x: 28
        y: 24
        width: Math.min(page.width - 56, 760)
        spacing: 8

        Text { text: "Paramètres"; font.pixelSize: 24; font.weight: Font.Bold; color: theme.texte }

        Section { text: "Apparence" }
        Ligne {
            titre: "Thème"
            detail: "« Automatique » suit le jeu de couleurs de Plasma."
            Segments {
                options: [{ texte: "Automatique", valeur: "auto" }, { texte: "Sombre", valeur: "sombre" }, { texte: "Clair", valeur: "clair" }]
                valeur: controleur.modeTheme
                onChoisi: (v) => controleur.modeTheme = v
            }
        }
        Ligne {
            titre: "Taille des icônes"
            detail: "Dans la vue en grille."
            Segments {
                options: [{ texte: "Petites", valeur: "80" }, { texte: "Moyennes", valeur: "112" }, { texte: "Grandes", valeur: "144" }, { texte: "Très grandes", valeur: "192" }]
                valeur: String(controleur.tailleIcones)
                onChoisi: (v) => controleur.tailleIcones = parseInt(v)
            }
        }
        Ligne {
            titre: "Vue par défaut"
            Segments {
                options: [{ texte: "Grille", valeur: "grille" }, { texte: "Liste", valeur: "liste" }]
                valeur: controleur.vue
                onChoisi: (v) => controleur.vue = v
            }
        }

        Section { text: "Fichiers" }
        Ligne {
            titre: "Afficher les fichiers cachés"
            detail: "Raccourci : Ctrl+H"
            Interrupteur { coche: controleur.caches; onBascule: controleur.caches = !controleur.caches }
        }
        Ligne {
            titre: "Panneau d’aperçu"
            detail: "Raccourci : Espace"
            Interrupteur { coche: controleur.apercuVisible; onBascule: controleur.apercuVisible = !controleur.apercuVisible }
        }
        Ligne {
            titre: "Miniatures"
            detail: "Partagées avec les autres applis (~/.cache/thumbnails)."
            Bouton { texte: "Vider le cache"; onClique: controleur.viderCacheMiniatures() }
        }

        Section { text: "Étiquettes"; visible: controleur.etiquettes.length > 0 }
        Repeater {
            model: controleur.etiquettes
            delegate: Ligne {
                id: ligneEtiquette
                required property var modelData
                titre: modelData.nom
                detail: modelData.nombre + " élément" + (modelData.nombre > 1 ? "s" : "")
                Repeater {
                    model: ["accent", "accentFroid", "info", "attention", "erreur", "texteDoux"]
                    delegate: Rectangle {
                        required property string modelData
                        width: 22; height: 22; radius: 11
                        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                        color: (theme.clair, theme.jeton(modelData))
                        border.width: ligneEtiquette.modelData.couleur === modelData ? 2 : 0
                        border.color: theme.texte
                        MouseArea {
                            anchors.fill: parent
                            onClicked: controleur.definirCouleurEtiquette(ligneEtiquette.modelData.nom, parent.modelData)
                        }
                    }
                }
                BoutonIcone {
                    icone: "supprimer"
                    couleurIcone: theme.erreur
                    bulle: "Retirer cette étiquette de tous les fichiers"
                    onClique: controleur.oublierEtiquette(ligneEtiquette.modelData.nom)
                }
            }
        }

        Section { text: "À propos" }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 92
            radius: 10
            color: theme.surface
            border.color: theme.bordure
            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16
                Image { source: cheminLogo; sourceSize: Qt.size(120, 120); Layout.preferredWidth: 58; Layout.preferredHeight: 58 }
                ColumnLayout {
                    spacing: 3
                    Text { text: "Fichiers 1.0.0"; font.pixelSize: 15; font.weight: Font.DemiBold; color: theme.texte }
                    Text { text: "L’explorateur de fichiers d’ExoLyx — GPL 3.0 ou ultérieure"; font.pixelSize: 13; color: theme.texteDoux }
                }
            }
        }
    }
}
