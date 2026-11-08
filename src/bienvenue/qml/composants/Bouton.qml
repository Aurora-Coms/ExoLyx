// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls.Basic

Button {
    id: b
    property bool principal: false
    property bool grand: false
    readonly property var p: ctrl.palette
    font.family: "Inter"
    font.pixelSize: grand ? 16 : 14
    font.weight: principal ? Font.DemiBold : Font.Normal
    leftPadding: grand ? 26 : 18; rightPadding: leftPadding
    topPadding: grand ? 13 : 9; bottomPadding: topPadding
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45

    contentItem: Text {
        text: b.text
        font: b.font
        color: b.principal ? b.p.surAccent : b.p.texte
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        implicitHeight: b.grand ? 48 : 38
        radius: 6
        color: b.principal ? (b.down ? b.p.accentFroid : b.hovered ? b.p.accentClair : b.p.accent)
                           : (b.down ? b.p.surface : b.hovered ? b.p.bordure : b.p.surfaceHaute)
        border.color: b.principal ? "transparent" : (b.hovered ? b.p.accent : b.p.bordure)
        border.width: 1
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
