// Bouton rond avec icône et libellé (veille, redémarrer, éteindre, session…).
import QtQuick

Item {
    id: racine
    property alias icone: img.source
    property string libelle: ""
    property real s: 1.0
    property bool actif: true
    property bool afficherLibelle: true
    signal clique()

    width: Math.max(cercle.width, texte.implicitWidth)
    height: cercle.height + (afficherLibelle ? texte.implicitHeight + 6 * s : 0)
    opacity: actif ? 1.0 : 0.35

    Rectangle {
        id: cercle
        width: 46 * racine.s; height: width
        radius: width / 2
        anchors.horizontalCenter: parent.horizontalCenter
        color: zone.containsMouse && racine.actif ? Qt.rgba(0.66, 0.83, 0.47, 0.22) : Qt.rgba(0.11, 0.15, 0.13, 0.62)
        border.color: zone.containsMouse && racine.actif || racine.activeFocus ? "#A8D479" : "#2A362E"
        border.width: 1
        Behavior on color { ColorAnimation { duration: 140 } }
        Image {
            id: img
            anchors.centerIn: parent
            width: parent.width * 0.46; height: width
            smooth: true; mipmap: true
        }
    }
    Text {
        id: texte
        visible: racine.afficherLibelle
        anchors.top: cercle.bottom
        anchors.topMargin: 6 * racine.s
        anchors.horizontalCenter: parent.horizontalCenter
        text: racine.libelle
        color: "#97A893"
        font.family: "Inter"
        font.pixelSize: Math.max(10, 12 * racine.s)
    }
    MouseArea {
        id: zone
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: racine.actif ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (racine.actif) racine.clique()
    }
    Keys.onReturnPressed: if (actif) clique()
    Keys.onSpacePressed: if (actif) clique()
}
