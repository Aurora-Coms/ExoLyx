import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Conflit de noms pendant une copie/un déplacement : une file d'attente si plusieurs
Dialogue {
    id: dialogue
    titre: actuel && actuel.source.dossier && actuel.destination.dossier ? "Ce dossier existe déjà" : "Un élément porte déjà ce nom"
    width: Math.min(560, (parent ? parent.width : 560) - 48)
    closePolicy: Popup.NoAutoClose
    property var file: []
    property var actuel: null
    property bool pourTous: false

    function ajouter(ident, source, destination) {
        file.push({ ident: ident, source: controleur.infosApercu(source), destination: controleur.infosApercu(destination),
                    dossierDest: destination.substring(0, destination.lastIndexOf("/")) })
        if (!visible) suivant()
    }
    function suivant() {
        if (file.length === 0) { actuel = null; close(); return }
        actuel = file.shift()
        pourTous = false
        open()
    }
    function repondre(choix) {
        if (actuel) operations.repondreConflit(actuel.ident, choix, pourTous)
        close()
        Qt.callLater(suivant)
    }

    component Fiche: Rectangle {
        id: fiche
        property string titreFiche
        property var infos: ({})
        Layout.fillWidth: true
        implicitHeight: 74
        radius: 10
        color: theme.fond
        border.color: theme.bordure
        IconeEntree {
            id: ic
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            taille: 44
            chemin: fiche.infos.chemin || ""
            dossier: !!fiche.infos.dossier
            categorie: fiche.infos.categorie || "fichier"
            miniature: fiche.infos.genre === "image" || fiche.infos.genre === "pdf"
            date: fiche.infos.mtime || 0
        }
        ColumnLayout {
            anchors.left: ic.right
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Text { text: fiche.titreFiche; font.pixelSize: 11; font.weight: Font.DemiBold; color: theme.texteDoux; font.capitalization: Font.AllUppercase }
            Text { text: fiche.infos.nom || ""; font.pixelSize: 13; color: theme.texte; elide: Text.ElideMiddle; Layout.fillWidth: true }
            Text {
                text: [fiche.infos.dossier ? fiche.infos.contenu : fiche.infos.taille, fiche.infos.date].filter(x => x).join("  ·  ")
                font.pixelSize: 12; color: theme.texteDoux
            }
        }
    }

    Text {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        font.pixelSize: 13
        color: theme.texteDoux
        text: dialogue.actuel ? "« " + (dialogue.actuel.destination.nom || "") + " » existe déjà dans « "
                                + dialogue.actuel.dossierDest.split("/").pop() + " »." : ""
    }
    Fiche { titreFiche: "Élément existant"; infos: dialogue.actuel ? dialogue.actuel.destination : ({}) }
    Fiche { titreFiche: "Nouvel élément"; infos: dialogue.actuel ? dialogue.actuel.source : ({}) }

    Item {
        // case à cocher « pour tous »
        Layout.topMargin: 2
        implicitWidth: caseTous.implicitWidth
        implicitHeight: caseTous.implicitHeight
        Row {
            id: caseTous
            spacing: 8
            Rectangle {
                width: 18; height: 18; radius: 5
                anchors.verticalCenter: parent.verticalCenter
                color: dialogue.pourTous ? theme.accent : "transparent"
                border.color: dialogue.pourTous ? theme.accent : theme.texteDoux
                Glyphe { anchors.centerIn: parent; visible: dialogue.pourTous; nom: "coche"; taille: 14; couleur: theme.surAccent }
            }
            Text { text: "Faire de même pour les conflits suivants"; font.pixelSize: 13; color: theme.texte; anchors.verticalCenter: parent.verticalCenter }
        }
        MouseArea { anchors.fill: parent; onClicked: dialogue.pourTous = !dialogue.pourTous }
    }

    boutons: [
        Bouton { texte: "Annuler"; onClique: dialogue.repondre("annuler") },
        Bouton { texte: "Ignorer"; onClique: dialogue.repondre("ignorer") },
        Bouton { texte: "Garder les deux"; onClique: dialogue.repondre("renommer") },
        Bouton {
            texte: dialogue.actuel && dialogue.actuel.source.dossier && dialogue.actuel.destination.dossier ? "Fusionner" : "Remplacer"
            principal: true
            onClique: dialogue.repondre("remplacer")
        }
    ]
}
