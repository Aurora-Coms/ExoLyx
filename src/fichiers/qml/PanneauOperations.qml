import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Opérations en cours : progression, fichier courant, vitesse, annulation
Rectangle {
    id: panneau
    width: 380
    height: Math.min(colonne.implicitHeight + 24, 320)
    radius: 10
    color: theme.surfaceHaute
    border.color: theme.bordure
    visible: liste.count > 0

    ColumnLayout {
        id: colonne
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: operations.actif ? "Opérations en cours" : "Opérations terminées"
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: theme.texte
            }
            BoutonIcone {
                visible: !operations.actif
                icone: "fermer"; implicitWidth: 24; implicitHeight: 24; tailleIcone: 14
                bulle: "Masquer"
                onClique: operations.effacerTerminees()
            }
        }
        ListView {
            id: liste
            Layout.fillWidth: true
            Layout.preferredHeight: contentHeight
            Layout.maximumHeight: 260
            clip: true
            spacing: 10
            model: operations
            interactive: contentHeight > height
            delegate: ColumnLayout {
                id: op
                required property string titre
                required property string courant
                required property real progression
                required property string detail
                required property string vitesse
                required property bool terminee
                required property int ident
                required property int erreurs
                width: liste.width
                spacing: 5
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Glyphe {
                        nom: op.terminee ? (op.erreurs > 0 ? "attention" : "coche") : "copier"
                        taille: 16
                        couleur: op.terminee ? (op.erreurs > 0 ? theme.attention : theme.accent) : theme.texteDoux
                    }
                    Text {
                        Layout.fillWidth: true
                        text: op.titre
                        elide: Text.ElideMiddle
                        font.pixelSize: 13
                        color: theme.texte
                    }
                    BoutonIcone {
                        visible: !op.terminee
                        icone: "croixCercle"; implicitWidth: 24; implicitHeight: 24; tailleIcone: 15
                        couleurIcone: theme.texteDoux
                        bulle: "Annuler"
                        onClique: operations.annuler(op.ident)
                    }
                }
                Jauge {
                    Layout.fillWidth: true
                    valeur: op.progression
                    couleurRemplie: op.erreurs > 0 ? theme.attention : theme.accent
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        Layout.fillWidth: true
                        text: op.terminee ? (op.erreurs > 0 ? op.erreurs + " erreur(s)" : "Terminé") : op.courant
                        elide: Text.ElideMiddle
                        font.pixelSize: 12
                        color: theme.texteDoux
                    }
                    Text {
                        text: op.detail + (op.vitesse ? "  ·  " + op.vitesse : "")
                        font.pixelSize: 12
                        color: theme.texteDoux
                    }
                }
            }
        }
    }
}
