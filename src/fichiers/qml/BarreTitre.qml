import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Barre de titre : onglets + boutons de fenêtre ; sert de poignée de déplacement
Item {
    id: barre
    property var fenetre
    implicitHeight: 46

    // zone de déplacement (sous les onglets)
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        onPressed: fenetre.startSystemMove()
        onDoubleClicked: fenetre.basculerAgrandie()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 8
        spacing: 6

        Image {
            source: cheminLogo
            sourceSize: Qt.size(44, 44)
            Layout.preferredWidth: 22
            Layout.preferredHeight: 22
            Layout.rightMargin: 4
            smooth: true
        }

        ListView {
            id: liste
            Layout.fillHeight: true
            Layout.topMargin: 7
            Layout.preferredWidth: Math.min(contentWidth, barre.width - 230)
            orientation: ListView.Horizontal
            interactive: contentWidth > width
            boundsBehavior: Flickable.StopAtBounds
            clip: true
            spacing: 2
            model: controleur.onglets
            currentIndex: controleur.courant
            readonly property real largeurOnglet: Math.max(120, Math.min(230, (barre.width - 240) / Math.max(1, count)))

            delegate: Item {
                id: onglet
                required property var modelData
                required property int index
                readonly property bool courant: index === controleur.courant
                width: liste.largeurOnglet
                height: liste.height

                Rectangle {
                    anchors.fill: parent
                    anchors.bottomMargin: -10      // déborde sous la barre pour se fondre avec elle
                    radius: 10
                    color: onglet.courant ? theme.surfaceHaute
                         : zoneOnglet.containsMouse || depotOnglet.containsDrag ? Qt.alpha(theme.surfaceHaute, 0.55) : "transparent"
                }
                Rectangle {
                    // séparateur entre onglets inactifs
                    width: 1; height: 16
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    color: theme.bordure
                    visible: !onglet.courant && onglet.index + 1 !== controleur.courant && onglet.index < liste.count - 1
                }

                MouseArea {
                    id: zoneOnglet
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                    onClicked: (s) => {
                        if (s.button === Qt.MiddleButton) controleur.fermerOnglet(onglet.index)
                        else controleur.activerOnglet(onglet.index)
                    }
                    onDoubleClicked: {}
                }

                DropArea {
                    id: depotOnglet
                    anchors.fill: parent
                    keys: ["text/uri-list"]
                    onEntered: minuteur.restart()
                    onExited: minuteur.stop()
                    onDropped: (d) => {
                        minuteur.stop()
                        const cible = onglet.modelData.dossierCourant
                        if (cible) d.accept(controleur.deposer(d.urls, cible))
                    }
                    Timer {
                        id: minuteur
                        interval: 650
                        onTriggered: controleur.activerOnglet(onglet.index)
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 6
                    spacing: 8
                    Glyphe {
                        nom: onglet.modelData.icone
                        taille: 16
                        couleur: onglet.courant ? theme.accent : theme.texteDoux
                    }
                    Text {
                        Layout.fillWidth: true
                        text: onglet.modelData.titre
                        elide: Text.ElideRight
                        font.pixelSize: 13
                        font.weight: onglet.courant ? Font.DemiBold : Font.Normal
                        color: onglet.courant ? theme.texte : theme.texteDoux
                    }
                    BoutonIcone {
                        icone: "fermer"
                        tailleIcone: 14
                        implicitWidth: 22
                        implicitHeight: 22
                        couleurIcone: theme.texteDoux
                        opacity: onglet.courant || zoneOnglet.containsMouse || survol ? 1 : 0
                        bulle: "Fermer l’onglet (Ctrl+W)"
                        onClique: controleur.fermerOnglet(onglet.index)
                    }
                }
            }
        }

        BoutonIcone {
            icone: "plus"
            implicitWidth: 30
            implicitHeight: 30
            bulle: "Nouvel onglet (Ctrl+T)"
            onClique: controleur.nouvelOnglet()
            Layout.alignment: Qt.AlignVCenter
        }

        Item { Layout.fillWidth: true }

        Row {
            spacing: 2
            Layout.alignment: Qt.AlignVCenter
            BoutonIcone {
                icone: "reduire"; implicitWidth: 40; tailleIcone: 16
                bulle: "Réduire"
                onClique: fenetre.showMinimized()
            }
            BoutonIcone {
                icone: fenetre.agrandie ? "restaurer" : "agrandir"; implicitWidth: 40; tailleIcone: 15
                bulle: fenetre.agrandie ? "Restaurer" : "Agrandir"
                onClique: fenetre.basculerAgrandie()
            }
            BoutonIcone {
                id: boutonFermer
                icone: "fermer"; implicitWidth: 40; tailleIcone: 16
                bulle: "Fermer"
                color: survol ? theme.erreur : "transparent"
                couleurIcone: survol ? theme.surAccent : theme.texte
                onClique: fenetre.close()
            }
        }
    }
}
