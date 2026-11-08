// Écran de chargement de session ExoLyx
import QtQuick

Rectangle {
    id: racine
    color: "#F4F8F1"
    property int stage

    onStageChanged: if (stage === 2) apparition.start()

    Item {
        id: centre
        anchors.centerIn: parent
        width: 300; height: 300
        opacity: 0

        Image {
            anchors.centerIn: parent
            width: 160; height: 160
            source: "images/logo.svg"
            sourceSize: Qt.size(320, 320)
            smooth: true
        }
        // Lune en orbite
        Item {
            anchors.fill: parent
            RotationAnimator on rotation { from: 0; to: 360; duration: 2400; loops: Animation.Infinite; running: true }
            Rectangle { width: 12; height: 12; radius: 6; color: "#5E9B2E"; x: parent.width / 2 - 6; y: 0 }
        }
    }

    Text {
        anchors.top: centre.bottom
        anchors.topMargin: 28
        anchors.horizontalCenter: parent.horizontalCenter
        text: "ExoLyx"
        color: "#16201A"
        font.pixelSize: 26
        font.family: "Inter"
        font.weight: Font.Light
        font.letterSpacing: 6
        opacity: centre.opacity
    }

    // Progression discrète
    Rectangle {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 72
        anchors.horizontalCenter: parent.horizontalCenter
        width: 180; height: 3; radius: 2
        color: Qt.rgba(0.5, 0.6, 0.5, 0.25)
        Rectangle {
            width: parent.width * Math.min(1, racine.stage / 6); height: parent.height; radius: 2
            color: "#5E9B2E"
            Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
        }
    }

    NumberAnimation { id: apparition; target: centre; property: "opacity"; from: 0; to: 1; duration: 600; easing.type: Easing.InOutQuad }
    Component.onCompleted: apparition.start()
}
