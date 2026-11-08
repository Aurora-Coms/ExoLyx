import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Navigation, fil d'Ariane (ou chemin saisissable) et recherche
Item {
    id: barre
    property var onglet: controleur.onglet
    implicitHeight: 48

    function editerChemin() {
        if (!onglet || onglet.mode !== "dossier" && onglet.mode !== "recherche") {
            champChemin.text = onglet && onglet.cheminTexte ? onglet.cheminTexte : controleur.dossierPersonnel
        } else {
            champChemin.text = onglet.cheminTexte
        }
        edition.actif = true
        champChemin.forceActiveFocus()
        champChemin.selectAll()
    }
    function focaliserRecherche() {
        champRecherche.forceActiveFocus()
        champRecherche.selectAll()
    }

    Connections {
        target: controleur
        function onCourantChange() {
            edition.actif = false
            champRecherche.synchroniser()
        }
    }
    Connections {
        target: barre.onglet
        function onChange() { champRecherche.synchroniser() }
    }

    QtObject { id: edition; property bool actif: false }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 4

        BoutonIcone {
            icone: "retour"; actif: onglet && onglet.peutReculer
            bulle: "Précédent (Alt+←)"
            onClique: onglet.reculer()
        }
        BoutonIcone {
            icone: "avancer"; actif: onglet && onglet.peutAvancer
            bulle: "Suivant (Alt+→)"
            onClique: onglet.avancer()
        }
        BoutonIcone {
            icone: "haut"; actif: onglet && onglet.peutMonter
            bulle: "Dossier parent (Alt+↑)"
            onClique: onglet.monter()
        }
        BoutonIcone {
            icone: "rafraichir"
            bulle: "Actualiser (F5)"
            onClique: controleur.rafraichir()
            Layout.rightMargin: 4
        }

        // --- adresse ---
        Rectangle {
            id: cadreAdresse
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            radius: 6
            color: theme.fond
            border.color: champChemin.activeFocus ? theme.accent : theme.bordure
            border.width: champChemin.activeFocus ? 1.5 : 1

            MouseArea {
                // un clic dans le vide de l'adresse passe en saisie
                anchors.fill: parent
                cursorShape: Qt.IBeamCursor
                onClicked: barre.editerChemin()
            }

            Glyphe {
                id: glypheAdresse
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                nom: onglet ? onglet.icone : "dossier"
                taille: 16
                couleur: theme.texteDoux
            }

            ListView {
                id: ariane
                visible: !edition.actif
                anchors.left: glypheAdresse.right
                anchors.leftMargin: 4
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                orientation: ListView.Horizontal
                interactive: false
                clip: true
                model: onglet ? onglet.segments : []
                onContentWidthChanged: positionViewAtEnd()
                onWidthChanged: positionViewAtEnd()
                onCountChanged: positionViewAtEnd()
                delegate: Row {
                    id: segment
                    required property var modelData
                    required property int index
                    height: ariane.height
                    Glyphe {
                        visible: segment.index > 0
                        nom: "chevron"
                        taille: 14
                        couleur: theme.texteDoux
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        height: 26
                        width: texteSegment.implicitWidth + 14
                        radius: 5
                        color: depotSegment.containsDrag ? Qt.alpha(theme.accent, 0.25)
                             : zoneSegment.containsMouse ? theme.surfaceHaute : "transparent"
                        Text {
                            id: texteSegment
                            anchors.centerIn: parent
                            text: segment.modelData.nom
                            font.pixelSize: 13
                            font.weight: segment.index === ariane.count - 1 ? Font.DemiBold : Font.Normal
                            color: segment.index === ariane.count - 1 ? theme.texte : theme.texteDoux
                        }
                        MouseArea {
                            id: zoneSegment
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                            onClicked: (s) => {
                                const c = segment.modelData.chemin
                                if (c === "recherche:") return
                                if (s.button === Qt.MiddleButton) controleur.nouvelOnglet(c)
                                else controleur.naviguer(c)
                            }
                        }
                        DropArea {
                            id: depotSegment
                            anchors.fill: parent
                            keys: ["text/uri-list"]
                            onDropped: (d) => {
                                const c = segment.modelData.chemin
                                if (c.indexOf(":") < 0) d.accept(controleur.deposer(d.urls, c))
                            }
                        }
                    }
                }
            }

            TextInput {
                id: champChemin
                visible: edition.actif
                anchors.left: glypheAdresse.right
                anchors.leftMargin: 8
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 13
                color: theme.texte
                selectionColor: Qt.alpha(theme.accent, 0.45)
                selectedTextColor: theme.texte
                selectByMouse: true
                clip: true
                onAccepted: {
                    edition.actif = false
                    controleur.naviguer(text)
                    fenetre.focaliserVue()
                }
                onActiveFocusChanged: if (!activeFocus) edition.actif = false
                Keys.onEscapePressed: {
                    edition.actif = false
                    fenetre.focaliserVue()
                }
            }
        }

        // --- recherche ---
        Rectangle {
            Layout.preferredWidth: Math.min(280, barre.width * 0.28)
            Layout.preferredHeight: 34
            Layout.leftMargin: 4
            radius: 6
            color: theme.fond
            border.color: champRecherche.activeFocus ? theme.accent : theme.bordure
            border.width: champRecherche.activeFocus ? 1.5 : 1

            Glyphe {
                id: loupe
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                nom: "recherche"
                taille: 16
                couleur: champRecherche.activeFocus ? theme.accent : theme.texteDoux
            }
            TextInput {
                id: champRecherche
                anchors.left: loupe.right
                anchors.leftMargin: 8
                anchors.right: effacer.left
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: 13
                color: theme.texte
                selectionColor: Qt.alpha(theme.accent, 0.45)
                selectByMouse: true
                clip: true
                property bool synchro: false
                function synchroniser() {
                    synchro = true
                    text = barre.onglet && barre.onglet.mode === "recherche" ? barre.onglet.motif : ""
                    synchro = false
                }
                onTextEdited: delai.restart()
                onAccepted: { delai.stop(); controleur.rechercher(text) }
                Keys.onEscapePressed: {
                    delai.stop()
                    text = ""
                    controleur.rechercher("")
                    fenetre.focaliserVue()
                }
                Keys.onDownPressed: fenetre.focaliserVue()
                Text {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    visible: !parent.text && !parent.activeFocus
                    text: barre.onglet && barre.onglet.mode === "dossier" ? "Rechercher dans " + barre.onglet.titre
                                                                         : "Rechercher"
                    elide: Text.ElideRight
                    color: theme.texteDoux
                    font.pixelSize: 13
                }
                Timer {
                    id: delai
                    interval: 350
                    onTriggered: controleur.rechercher(champRecherche.text)
                }
            }
            Item {
                id: effacer
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                width: visible ? 22 : 0
                height: 22
                visible: champRecherche.text !== "" || (barre.onglet && barre.onglet.rechercheEnCours)
                // indicateur d'activité pendant la recherche
                Rectangle {
                    id: rouage
                    anchors.centerIn: parent
                    width: 14; height: 14; radius: 7
                    color: "transparent"
                    border.width: 2
                    border.color: Qt.alpha(theme.accent, 0.3)
                    visible: barre.onglet && barre.onglet.rechercheEnCours && !zoneEffacer.containsMouse
                    Rectangle {
                        width: 4; height: 4; radius: 2
                        color: theme.accent
                        x: 5 + 6 * Math.cos(angle) - 0
                        y: 5 + 6 * Math.sin(angle) - 0
                        property real angle: 0
                        NumberAnimation on angle { from: 0; to: Math.PI * 2; duration: 900; loops: Animation.Infinite; running: rouage.visible }
                    }
                }
                Glyphe {
                    anchors.centerIn: parent
                    visible: !rouage.visible
                    nom: "fermer"
                    taille: 14
                    couleur: zoneEffacer.containsMouse ? theme.texte : theme.texteDoux
                }
                MouseArea {
                    id: zoneEffacer
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        delai.stop()
                        if (barre.onglet && barre.onglet.rechercheEnCours) {
                            barre.onglet.annulerRecherche()
                        } else {
                            champRecherche.text = ""
                            controleur.rechercher("")
                        }
                    }
                }
                InfoBulle {
                    visible: zoneEffacer.containsMouse
                    text: barre.onglet && barre.onglet.rechercheEnCours ? "Arrêter la recherche" : "Effacer"
                }
            }
        }
    }
}
