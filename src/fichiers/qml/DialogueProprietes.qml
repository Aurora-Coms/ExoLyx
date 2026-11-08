import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Propriétés de la sélection : informations, taille calculée, étiquettes
Dialogue {
    id: dialogue
    width: Math.min(500, (parent ? parent.width : 500) - 48)
    property var infos: ({})
    property var etiquettes: []
    property string erreur: ""

    function ouvrir() {
        infos = controleur.proprietesSelection()
        if (!infos.nom) return
        etiquettes = infos.etiquettes || []
        titre = infos.multiple ? "Propriétés de la sélection" : "Propriétés"
        erreur = ""
        open()
    }
    function basculer(nom, ajouter) {
        erreur = controleur.basculerEtiquette(infos.chemins, nom, ajouter)
        const liste = etiquettes.slice()
        const i = liste.indexOf(nom)
        if (ajouter && i < 0 && !erreur) liste.push(nom)
        if (!ajouter && i >= 0) liste.splice(i, 1)
        etiquettes = liste
    }

    Connections {
        target: controleur
        function onTailleCalculee(chemin, taille, contenu) {
            if (!dialogue.visible) return
            if ((dialogue.infos.multiple && chemin === "*") || chemin === dialogue.infos.chemin) {
                const copie = Object.assign({}, dialogue.infos)
                copie.taille = taille
                copie.contenu = contenu
                dialogue.infos = copie
            }
        }
    }

    RowLayout {
        spacing: 14
        Layout.fillWidth: true
        IconeEntree {
            taille: 56
            chemin: dialogue.infos.chemin || ""
            dossier: !!dialogue.infos.dossier
            categorie: dialogue.infos.categorie || "fichier"
            miniature: !!dialogue.infos.miniature
            date: dialogue.infos.date || 0
        }
        ColumnLayout {
            spacing: 2
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: dialogue.infos.nom || ""
                font.pixelSize: 15
                font.weight: Font.DemiBold
                color: theme.texte
                wrapMode: Text.WrapAnywhere
                maximumLineCount: 2
                elide: Text.ElideRight
            }
            Text { text: dialogue.infos.type || ""; font.pixelSize: 13; color: theme.texteDoux }
        }
    }

    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: theme.bordure }

    GridLayout {
        columns: 2
        columnSpacing: 16
        rowSpacing: 7
        Layout.fillWidth: true
        component Cle: Text { font.pixelSize: 13; color: theme.texteDoux; Layout.alignment: Qt.AlignTop }
        component Valeur: TextEdit {
            font.pixelSize: 13; color: theme.texte; readOnly: true; selectByMouse: true
            selectionColor: Qt.alpha(theme.accent, 0.45)
            wrapMode: TextEdit.WrapAnywhere; Layout.fillWidth: true
        }
        Cle { text: "Emplacement" }
        Valeur { text: dialogue.infos.emplacement || "" }
        Cle { text: "Cible du lien"; visible: !!dialogue.infos.lien }
        Valeur { text: dialogue.infos.lien || ""; visible: !!dialogue.infos.lien }
        Cle { text: "Taille" }
        Valeur { text: dialogue.infos.taille || "" }
        Cle { text: "Contenu"; visible: !!dialogue.infos.contenu }
        Valeur { text: dialogue.infos.contenu || ""; visible: !!dialogue.infos.contenu }
        Cle { text: "Modifié"; visible: !dialogue.infos.multiple }
        Valeur { text: dialogue.infos.modifie || ""; visible: !dialogue.infos.multiple }
        Cle { text: "Dernier accès"; visible: !dialogue.infos.multiple }
        Valeur { text: dialogue.infos.accede || ""; visible: !dialogue.infos.multiple }
        Cle { text: "Propriétaire"; visible: !dialogue.infos.multiple }
        Valeur { text: dialogue.infos.proprietaire || ""; visible: !dialogue.infos.multiple }
        Cle { text: "Permissions"; visible: !dialogue.infos.multiple }
        Valeur { text: dialogue.infos.permissions || ""; font.family: "JetBrains Mono"; visible: !dialogue.infos.multiple }
        Cle { text: "Type MIME"; visible: !!dialogue.infos.mime }
        Valeur { text: dialogue.infos.mime || ""; visible: !!dialogue.infos.mime }
    }

    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: theme.bordure }

    Text { text: "Étiquettes"; font.pixelSize: 13; font.weight: Font.DemiBold; color: theme.texte }
    Flow {
        Layout.fillWidth: true
        spacing: 6
        Repeater {
            model: dialogue.etiquettes
            delegate: Rectangle {
                id: puce
                required property string modelData
                readonly property string couleur: (theme.clair, theme.jeton(controleur.couleurEtiquette(modelData)))
                height: 28
                width: rangee.implicitWidth + 18
                radius: 14
                color: Qt.alpha(couleur, 0.15)
                border.color: Qt.alpha(couleur, 0.55)
                Row {
                    id: rangee
                    anchors.centerIn: parent
                    spacing: 6
                    Rectangle { width: 8; height: 8; radius: 4; color: puce.couleur; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: puce.modelData; font.pixelSize: 13; color: theme.texte; anchors.verticalCenter: parent.verticalCenter }
                    Glyphe {
                        nom: "fermer"; taille: 13; couleur: zoneRetirer.containsMouse ? theme.texte : theme.texteDoux
                        anchors.verticalCenter: parent.verticalCenter
                        MouseArea { id: zoneRetirer; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true; onClicked: dialogue.basculer(puce.modelData, false) }
                    }
                }
            }
        }
        // suggestions : étiquettes existantes non posées
        Repeater {
            model: controleur.etiquettes.filter(e => dialogue.etiquettes.indexOf(e.nom) < 0)
            delegate: Rectangle {
                id: suggestion
                required property var modelData
                height: 28
                width: texteSugg.implicitWidth + 22
                radius: 14
                color: zoneSugg.containsMouse ? theme.surfaceHaute : "transparent"
                border.color: theme.bordure
                Text { id: texteSugg; anchors.centerIn: parent; text: "+ " + suggestion.modelData.nom; font.pixelSize: 13; color: theme.texteDoux }
                MouseArea { id: zoneSugg; anchors.fill: parent; hoverEnabled: true; onClicked: dialogue.basculer(suggestion.modelData.nom, true) }
            }
        }
    }
    ChampTexte {
        id: champEtiquette
        Layout.fillWidth: true
        placeholderText: "Ajouter une étiquette puis Entrée"
        onAccepted: {
            if (text.trim() !== "") dialogue.basculer(text.trim(), true)
            text = ""
        }
    }
    Text {
        visible: dialogue.erreur !== ""
        text: dialogue.erreur
        color: theme.erreur
        font.pixelSize: 12
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    boutons: [
        Bouton { texte: "Fermer"; principal: true; onClique: dialogue.close() }
    ]
}
