import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Accueil : accès rapide, lecteurs, étiquettes, fichiers récents
Flickable {
    id: page
    contentHeight: colonne.implicitHeight + 48
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: BarreDefilement {}

    readonly property int marge: 28

    component TitreSection: Text {
        font.pixelSize: 15
        font.weight: Font.DemiBold
        color: theme.texte
        Layout.topMargin: 10
    }

    component Carte: Rectangle {
        id: carte
        property bool survol: zoneCarte.containsMouse
        property string cibleDepot: ""
        signal clique()
        signal cliqueMilieu()
        signal cliqueDroit(real x, real y)
        radius: 10
        color: depotCarte.containsDrag ? Qt.alpha(theme.accent, 0.22) : survol ? theme.surfaceHaute : theme.surface
        border.color: survol || depotCarte.containsDrag ? Qt.alpha(theme.accent, 0.55) : theme.bordure
        Behavior on color { ColorAnimation { duration: 90 } }
        MouseArea {
            id: zoneCarte
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
            onClicked: (s) => {
                if (s.button === Qt.MiddleButton) carte.cliqueMilieu()
                else if (s.button === Qt.RightButton) carte.cliqueDroit(s.x, s.y)
                else carte.clique()
            }
        }
        DropArea {
            id: depotCarte
            anchors.fill: parent
            enabled: carte.cibleDepot !== ""
            keys: ["text/uri-list"]
            onDropped: (d) => d.accept(controleur.deposer(d.urls, carte.cibleDepot))
        }
    }

    ColumnLayout {
        id: colonne
        x: page.marge
        y: 24
        width: page.width - 2 * page.marge
        spacing: 12

        RowLayout {
            spacing: 14
            Layout.fillWidth: true
            Image {
                source: cheminLogo
                sourceSize: Qt.size(96, 96)
                Layout.preferredWidth: 46
                Layout.preferredHeight: 46
            }
            ColumnLayout {
                spacing: 2
                Text {
                    text: {
                        const h = new Date().getHours()
                        return h < 5 || h >= 18 ? "Bonsoir" : "Bonjour"
                    }
                    font.pixelSize: 24
                    font.weight: Font.Bold
                    color: theme.texte
                }
                Text {
                    text: "Retrouvez vos dossiers, vos lecteurs et vos derniers fichiers."
                    font.pixelSize: 13
                    color: theme.texteDoux
                }
            }
        }

        // --- accès rapide ---
        TitreSection { text: "Accès rapide" }
        Flow {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: controleur.accesRapide
                delegate: Carte {
                    id: carteDossier
                    required property var modelData
                    width: 186
                    height: 64
                    cibleDepot: modelData.chemin
                    onClique: controleur.naviguer(modelData.chemin)
                    onCliqueMilieu: controleur.nouvelOnglet(modelData.chemin)
                    onCliqueDroit: (x, y) => fenetre.menuDossier(modelData.chemin, controleur.estEpingle(modelData.chemin), carteDossier, x, y)
                    IconeEntree {
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        taille: 40
                        dossier: true
                        embleme: carteDossier.modelData.embleme
                    }
                    Text {
                        x: 62
                        width: parent.width - x - 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: carteDossier.modelData.nom
                        elide: Text.ElideRight
                        font.pixelSize: 13
                        font.weight: Font.Medium
                        color: theme.texte
                    }
                }
            }
        }

        // --- lecteurs ---
        TitreSection { text: "Lecteurs" }
        Flow {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: controleur.lecteurs
                delegate: Carte {
                    id: carteLecteur
                    required property var modelData
                    width: 286
                    height: 82
                    cibleDepot: modelData.montage
                    onClique: controleur.ouvrirLecteur(modelData.peripherique, modelData.montage)
                    Rectangle {
                        x: 14
                        anchors.verticalCenter: parent.verticalCenter
                        width: 44; height: 44; radius: 10
                        color: Qt.alpha(theme.accent, 0.14)
                        Glyphe {
                            anchors.centerIn: parent
                            nom: carteLecteur.modelData.amovible ? "usb" : "lecteur"
                            taille: 24
                            couleur: theme.accent
                        }
                    }
                    ColumnLayout {
                        x: 72
                        width: parent.width - x - 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        Text {
                            Layout.fillWidth: true
                            text: carteLecteur.modelData.nom
                            elide: Text.ElideRight
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            color: theme.texte
                        }
                        Jauge {
                            Layout.fillWidth: true
                            visible: carteLecteur.modelData.montage !== ""
                            valeur: carteLecteur.modelData.ratio
                        }
                        Text {
                            Layout.fillWidth: true
                            text: carteLecteur.modelData.montage
                                  ? carteLecteur.modelData.libreTexte + " libres sur " + carteLecteur.modelData.totalTexte
                                  : "Non monté — cliquez pour l’ouvrir"
                            elide: Text.ElideRight
                            font.pixelSize: 12
                            color: theme.texteDoux
                        }
                    }
                }
            }
        }

        // --- étiquettes ---
        TitreSection { text: "Étiquettes"; visible: controleur.etiquettes.length > 0 }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            visible: controleur.etiquettes.length > 0
            Repeater {
                model: controleur.etiquettes
                delegate: Rectangle {
                    id: puce
                    required property var modelData
                    readonly property string couleur: (theme.clair, theme.jeton(modelData.couleur))
                    height: 32
                    width: contenuPuce.implicitWidth + 26
                    radius: 16
                    color: zonePuce.containsMouse ? Qt.alpha(couleur, 0.22) : Qt.alpha(couleur, 0.12)
                    border.color: Qt.alpha(couleur, 0.5)
                    Row {
                        id: contenuPuce
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle { width: 9; height: 9; radius: 4.5; color: puce.couleur; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: puce.modelData.nom; font.pixelSize: 13; color: theme.texte; anchors.verticalCenter: parent.verticalCenter }
                        Text {
                            text: puce.modelData.nombre
                            visible: puce.modelData.nombre > 0
                            font.pixelSize: 12
                            color: theme.texteDoux
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: zonePuce
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: controleur.naviguer("etiquette:" + puce.modelData.nom)
                    }
                }
            }
        }

        // --- récents ---
        TitreSection { text: "Récents" }
        Text {
            visible: controleur.recents.length === 0
            text: "Les fichiers que vous ouvrez apparaîtront ici."
            font.pixelSize: 13
            color: theme.texteDoux
        }
        GridLayout {
            id: grilleRecents
            Layout.fillWidth: true
            visible: controleur.recents.length > 0
            columns: Math.max(1, Math.floor((width + columnSpacing) / (300 + columnSpacing)))
            columnSpacing: 10
            rowSpacing: 10
            Repeater {
                model: controleur.recents
                delegate: Carte {
                    id: carteRecent
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 62
                    onClique: controleur.ouvrirChemin(modelData.chemin)
                    onCliqueDroit: (x, y) => fenetre.menuRecent(modelData.chemin, carteRecent, x, y)
                    IconeEntree {
                        id: iconeRecent
                        x: 12
                        anchors.verticalCenter: parent.verticalCenter
                        taille: 38
                        chemin: carteRecent.modelData.chemin
                        categorie: carteRecent.modelData.categorie
                        miniature: carteRecent.modelData.miniature
                        date: carteRecent.modelData.date
                    }
                    ColumnLayout {
                        x: 60
                        width: parent.width - x - 12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 2
                        Text {
                            Layout.fillWidth: true
                            text: carteRecent.modelData.nom
                            elide: Text.ElideMiddle
                            font.pixelSize: 13
                            color: theme.texte
                        }
                        Text {
                            Layout.fillWidth: true
                            text: carteRecent.modelData.dateTexte + "  ·  " + carteRecent.modelData.dossierParent.replace(controleur.dossierPersonnel, "~")
                            elide: Text.ElideMiddle
                            font.pixelSize: 12
                            color: theme.texteDoux
                        }
                    }
                }
            }
        }
    }
}
