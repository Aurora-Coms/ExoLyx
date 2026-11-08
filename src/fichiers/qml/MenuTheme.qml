import QtQuick
import QtQuick.Controls.Basic

// Menu contextuel aux couleurs ExoLyx
Menu {
    id: menu
    padding: 5
    implicitWidth: 272
    delegate: ElementMenu {}
    background: Rectangle {
        implicitWidth: 272
        color: theme.surface
        border.color: theme.bordure
        radius: 10
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 90 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 70 } }
}
