import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Saisie d'un nom : nouveau dossier/fichier, renommage, nouvelle étiquette
Dialogue {
    id: dialogue
    property string texteValider: "Valider"
    property string valeurInitiale: ""
    property bool selectionnerBase: true      // sélectionne le nom sans l'extension
    property string erreur: ""
    property var action: null                 // fonction(nom) -> message d'erreur ou ""

    function ouvrir(titre, valeur, bouton, fonction, base) {
        dialogue.titre = titre
        valeurInitiale = valeur
        texteValider = bouton
        action = fonction
        selectionnerBase = base !== false
        erreur = ""
        open()
    }
    function valider() {
        const message = action ? action(champ.text) : ""
        if (message) erreur = message
        else close()
    }

    onOpened: {
        champ.text = valeurInitiale
        champ.forceActiveFocus()
        const point = valeurInitiale.lastIndexOf(".")
        if (selectionnerBase && point > 0) champ.select(0, point)
        else champ.selectAll()
    }

    ChampTexte {
        id: champ
        Layout.fillWidth: true
        erreur: dialogue.erreur !== ""
        onTextEdited: dialogue.erreur = ""
        onAccepted: dialogue.valider()
    }
    Text {
        visible: dialogue.erreur !== ""
        text: dialogue.erreur
        color: theme.erreur
        font.pixelSize: 12
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
    }

    boutons: [
        Bouton { texte: "Annuler"; onClique: dialogue.close() },
        Bouton { texte: dialogue.texteValider; principal: true; actif: champ.text.trim() !== ""; onClique: dialogue.valider() }
    ]
}
