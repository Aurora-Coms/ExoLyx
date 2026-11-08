import QtQuick
import QtQuick.Controls.Basic

ScrollBar {
    id: barre
    policy: ScrollBar.AsNeeded
    minimumSize: 0.08
    contentItem: Rectangle {
        implicitWidth: barre.hovered || barre.pressed ? 8 : 5
        implicitHeight: 5
        radius: width / 2
        color: barre.pressed ? theme.texteDoux : Qt.alpha(theme.texteDoux, barre.hovered ? 0.6 : 0.35)
        opacity: barre.active || barre.hovered ? 1 : 0.0
        Behavior on opacity { NumberAnimation { duration: 250 } }
        Behavior on implicitWidth { NumberAnimation { duration: 100 } }
    }
    background: Item {}
}
