import QtQuick
import QtQuick.Controls.Basic

TextField {
    id: champ
    property bool erreur: false
    implicitHeight: 34
    font.pixelSize: 13
    color: theme.texte
    placeholderTextColor: theme.texteDoux
    selectionColor: Qt.alpha(theme.accent, 0.45)
    selectedTextColor: theme.texte
    leftPadding: 10
    rightPadding: 10
    selectByMouse: true
    background: Rectangle {
        radius: 6
        color: theme.surfaceHaute
        border.width: champ.activeFocus || champ.erreur ? 1.5 : 1
        border.color: champ.erreur ? theme.erreur : champ.activeFocus ? theme.accent : theme.bordure
    }
}
