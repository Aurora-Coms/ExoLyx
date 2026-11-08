// SPDX-License-Identifier: GPL-3.0-or-later
// Case à cocher dessinée à la main (indicateur seul).
import QtQuick

Rectangle {
    id: c
    property bool coche: false
    readonly property var p: ctrl.palette
    width: 22; height: 22; radius: 6
    color: coche ? p.accent : "transparent"
    border.color: coche ? p.accent : p.texteDoux
    border.width: 2
    Behavior on color { ColorAnimation { duration: 120 } }
    // coche dessinée avec deux segments
    Item {
        anchors.fill: parent
        visible: c.coche
        Rectangle { x: 4.5; y: 10.5; width: 6; height: 2.6; radius: 1.3; rotation: 45; color: c.p.surAccent }
        Rectangle { x: 7.6; y: 9; width: 11; height: 2.6; radius: 1.3; rotation: -50; color: c.p.surAccent }
    }
}
