import QtQuick

// Gestion souris commune aux éléments de grille et de liste :
// sélection (Ctrl/Maj), double-clic, menu contextuel, glisser
MouseArea {
    id: zone
    property var vue
    property int ligne: -1
    property bool selectionne: false
    property bool dossier: false
    property string chemin: ""
    property point depart
    property bool reduire: false
    property bool glisse: false
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton

    onPressed: (s) => {
        vue.focaliser()
        glisse = false
        reduire = false
        if (s.button === Qt.MiddleButton) return
        if (s.button === Qt.RightButton) {
            if (!selectionne) vue.modele.selectionner(ligne, "seul")
            fenetre.menuElement(zone, s.x, s.y)
            return
        }
        depart = Qt.point(s.x, s.y)
        if (s.modifiers & Qt.ControlModifier) vue.modele.selectionner(ligne, "basculer")
        else if (s.modifiers & Qt.ShiftModifier) vue.modele.selectionner(ligne, "etendre")
        else if (!selectionne) vue.modele.selectionner(ligne, "seul")
        else reduire = true
    }
    onPositionChanged: (s) => {
        if (!(pressedButtons & Qt.LeftButton) || glisse) return
        if (Math.abs(s.x - depart.x) + Math.abs(s.y - depart.y) < 10) return
        glisse = true
        reduire = false
        if (!selectionne) vue.modele.selectionner(ligne, "seul")
        controleur.glisserSelection()
        // le glisser système a consommé le relâchement : on remet la zone à zéro
        zone.enabled = false
        Qt.callLater(() => { zone.enabled = true })
    }
    onReleased: (s) => {
        if (reduire && !glisse) vue.modele.selectionner(ligne, "seul")
        reduire = false
    }
    onClicked: (s) => {
        if (s.button === Qt.MiddleButton && dossier) controleur.nouvelOnglet(chemin)
    }
    onDoubleClicked: (s) => {
        if (s.button !== Qt.LeftButton) return
        vue.modele.selectionner(ligne, "seul")
        if (vue.mode === "corbeille") fenetre.ouvrirProprietes()
        else controleur.ouvrirSelection()
    }
}
