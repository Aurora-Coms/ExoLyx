import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Barre latérale : Accueil, Épinglés, Lecteurs, Étiquettes, Corbeille, Paramètres
Item {
    id: barre
    readonly property string cheminCourant: controleur.onglet ? controleur.onglet.chemin : ""

    component Titre: Item {
        id: titre
        property string texte
        property bool depot: false
        signal deposeUrls(var urls)
        Layout.fillWidth: true
        implicitHeight: 30
        Text {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 6
            text: titre.texte
            font.pixelSize: 11
            font.weight: Font.DemiBold
            font.letterSpacing: 0.6
            font.capitalization: Font.AllUppercase
            color: zoneDepot.containsDrag ? theme.accent : theme.texteDoux
        }
        DropArea {
            id: zoneDepot
            enabled: titre.depot
            anchors.fill: parent
            keys: ["text/uri-list"]
            onDropped: (d) => { titre.deposeUrls(d.urls); d.acceptProposedAction() }
        }
    }

    component Entree: Rectangle {
        id: entree
        property string icone: "dossier"
        property string texte: ""
        property string cible: ""
        property string cibleDepot: ""
        property string couleurIcone: actif ? theme.accent : theme.texteDoux
        property string pastille: ""
        property real jauge: -1
        property string detail: ""
        property bool actif: barre.cheminCourant === cible && cible !== ""
        property alias boutonFin: emplacementFin.data
        signal clique()
        signal cliqueMilieu()
        signal cliqueDroit(real x, real y)
        Layout.fillWidth: true
        implicitHeight: jauge >= 0 ? 46 : 34
        radius: 6
        color: depot.containsDrag ? Qt.alpha(theme.accent, 0.22)
             : actif ? Qt.alpha(theme.accent, theme.clair ? 0.16 : 0.13)
             : zone.containsMouse ? theme.surfaceHaute : "transparent"
        Rectangle {
            visible: entree.actif
            width: 3; height: 16; radius: 1.5
            anchors.verticalCenter: parent.verticalCenter
            x: 0
            color: theme.accent
        }
        MouseArea {
            id: zone
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
            onClicked: (s) => {
                if (s.button === Qt.MiddleButton) entree.cliqueMilieu()
                else if (s.button === Qt.RightButton) entree.cliqueDroit(s.x, s.y)
                else entree.clique()
            }
        }
        DropArea {
            id: depot
            anchors.fill: parent
            enabled: entree.cibleDepot !== ""
            keys: ["text/uri-list"]
            onDropped: (d) => d.accept(controleur.deposer(d.urls, entree.cibleDepot))
        }
        Rectangle {
            id: puce
            visible: entree.pastille !== ""
            x: 15; width: 10; height: 10; radius: 5
            y: (entree.jauge >= 0 ? 17 : entree.height / 2) - 5
            color: entree.pastille
        }
        Glyphe {
            id: glyphe
            visible: entree.pastille === ""
            x: 12
            y: (entree.jauge >= 0 ? 17 : entree.height / 2) - taille / 2
            nom: entree.icone
            taille: 17
            couleur: entree.couleurIcone
        }
        Text {
            id: libelle
            x: 38
            y: (entree.jauge >= 0 ? 17 : entree.height / 2) - height / 2
            width: entree.width - x - 8 - emplacementFin.width - (detailTexte.visible ? detailTexte.width + 6 : 0)
            text: entree.texte
            elide: Text.ElideRight
            font.pixelSize: 13
            font.weight: entree.actif ? Font.DemiBold : Font.Normal
            color: theme.texte
        }
        Text {
            id: detailTexte
            visible: entree.detail !== "" && entree.jauge < 0
            anchors.right: emplacementFin.left
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            text: entree.detail
            font.pixelSize: 11
            color: theme.texteDoux
        }
        Jauge {
            visible: entree.jauge >= 0
            x: 38
            y: 31
            width: entree.width - x - 12 - emplacementFin.width
            height: 4
            valeur: Math.max(0, entree.jauge)
        }
        Row {
            id: emplacementFin
            anchors.right: parent.right
            anchors.rightMargin: 4
            y: (entree.jauge >= 0 ? 17 : entree.height / 2) - height / 2
        }
    }

    Flickable {
        id: defile
        anchors.fill: parent
        anchors.bottomMargin: bas.height
        contentHeight: colonne.implicitHeight + 8
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: BarreDefilement {}

        ColumnLayout {
            id: colonne
            width: defile.width - 16
            x: 8
            spacing: 1

            Entree {
                icone: "accueil"; texte: "Accueil"; cible: "accueil:"
                onClique: controleur.naviguer("accueil:")
                onCliqueMilieu: controleur.nouvelOnglet("accueil:")
                Layout.topMargin: 4
            }
            Entree {
                id: entreeMaison
                icone: "dossier"; texte: "Dossier personnel"
                cible: controleur.dossierPersonnel; cibleDepot: cible
                onClique: controleur.naviguer(cible)
                onCliqueMilieu: controleur.nouvelOnglet(cible)
                onCliqueDroit: (x, y) => fenetre.menuDossier(cible, false, entreeMaison, x, y)
            }

            Titre {
                texte: "Épinglés"
                depot: true
                onDeposeUrls: (urls) => controleur.epinglerUrls(urls)
            }
            Repeater {
                model: controleur.epingles
                delegate: Entree {
                    id: entreeEpingle
                    required property var modelData
                    icone: modelData.embleme || "dossier"
                    texte: modelData.nom
                    cible: modelData.chemin
                    cibleDepot: modelData.chemin
                    onClique: controleur.naviguer(cible)
                    onCliqueMilieu: controleur.nouvelOnglet(cible)
                    onCliqueDroit: (x, y) => fenetre.menuDossier(cible, true, entreeEpingle, x, y)
                }
            }
            Text {
                visible: controleur.epingles.length === 0
                Layout.leftMargin: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Glissez un dossier ici pour l’épingler."
                font.pixelSize: 12
                color: theme.texteDoux
            }

            Titre { texte: "Lecteurs" }
            Repeater {
                model: controleur.lecteurs
                delegate: Entree {
                    id: lecteur
                    required property var modelData
                    icone: modelData.amovible ? "usb" : "lecteur"
                    texte: modelData.nom
                    cible: modelData.montage
                    cibleDepot: modelData.montage
                    jauge: modelData.montage ? modelData.ratio : -1
                    detail: modelData.montage ? "" : modelData.totalTexte
                    couleurIcone: actif ? theme.accent : modelData.montage ? theme.texteDoux : Qt.alpha(theme.texteDoux, 0.6)
                    onClique: controleur.ouvrirLecteur(modelData.peripherique, modelData.montage)
                    boutonFin: BoutonIcone {
                        visible: lecteur.modelData.amovible && lecteur.modelData.montage !== ""
                        icone: "ejecter"
                        implicitWidth: 26; implicitHeight: 26; tailleIcone: 15
                        couleurIcone: theme.texteDoux
                        bulle: "Éjecter"
                        onClique: controleur.ejecterLecteur(lecteur.modelData.peripherique)
                    }
                }
            }

            Titre { texte: "Étiquettes"; visible: controleur.etiquettes.length > 0 }
            Repeater {
                model: controleur.etiquettes
                delegate: Entree {
                    id: entreeEtiquette
                    required property var modelData
                    texte: modelData.nom
                    cible: "etiquette:" + modelData.nom
                    pastille: (theme.clair, theme.jeton(modelData.couleur))
                    detail: modelData.nombre > 0 ? String(modelData.nombre) : ""
                    onClique: controleur.naviguer(cible)
                    onCliqueMilieu: controleur.nouvelOnglet(cible)
                    onCliqueDroit: (x, y) => fenetre.menuEtiquette(modelData.nom, entreeEtiquette, x, y)
                }
            }
        }
    }

    ColumnLayout {
        id: bas
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 8
        anchors.bottomMargin: 10
        spacing: 1
        Rectangle { Layout.fillWidth: true; Layout.bottomMargin: 6; implicitHeight: 1; color: theme.bordure }
        Entree {
            id: entreeCorbeille
            icone: "supprimer"; texte: "Corbeille"; cible: "corbeille:"; cibleDepot: "corbeille:"
            detail: controleur.corbeilleVide ? "" : "•"
            onClique: controleur.naviguer("corbeille:")
            onCliqueMilieu: controleur.nouvelOnglet("corbeille:")
            onCliqueDroit: (x, y) => fenetre.menuCorbeille(entreeCorbeille, x, y)
        }
        Entree {
            icone: "parametres"; texte: "Paramètres"; cible: "parametres:"
            onClique: controleur.naviguer("parametres:")
        }
    }
}
