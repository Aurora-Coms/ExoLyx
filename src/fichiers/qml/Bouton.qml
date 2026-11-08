import QtQuick

// Bouton de dialogue : principal (accent) ou secondaire
Rectangle {
    id: racine
    property string texte: ""
    property bool principal: false
    property bool danger: false
    property bool actif: true
    signal clique()
    implicitHeight: 34
    implicitWidth: Math.max(96, etiquette.implicitWidth + 32)
    radius: 6
    opacity: actif ? 1 : 0.45
    readonly property string couleurFond: danger ? theme.erreur : theme.accent
    color: principal || danger
        ? (zone.pressed ? Qt.darker(couleurFond, 1.15) : zone.containsMouse ? Qt.lighter(couleurFond, 1.06) : couleurFond)
        : (zone.pressed ? theme.bordure : zone.containsMouse ? theme.surfaceHaute : "transparent")
    border.color: principal || danger ? "transparent" : theme.bordure
    border.width: 1
    Text {
        id: etiquette
        anchors.centerIn: parent
        text: racine.texte
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: racine.principal || racine.danger ? theme.surAccent : theme.texte
    }
    MouseArea {
        id: zone
        anchors.fill: parent
        hoverEnabled: true
        onClicked: if (racine.actif) racine.clique()
    }
}
