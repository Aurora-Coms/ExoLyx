import QtQuick
import QtQuick.Controls.Basic

ToolTip {
    id: bulle
    delay: 550
    timeout: 6000
    padding: 0
    contentItem: Text {
        text: bulle.text
        color: theme.texte
        font.pixelSize: 12
        leftPadding: 9; rightPadding: 9; topPadding: 5; bottomPadding: 5
    }
    background: Rectangle {
        color: theme.surfaceHaute
        border.color: theme.bordure
        radius: 6
    }
}
