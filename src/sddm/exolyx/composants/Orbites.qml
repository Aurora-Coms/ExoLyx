// Avatar de l'utilisateur placé au centre des orbites tressées du logo,
// avec une lune qui tourne autour. `vitesse` accélère pendant la connexion.
import QtQuick
import QtQuick.Effects

Item {
    id: racine

    // diamètre de l'avatar (= planète du logo)
    property real diametre: 180
    property url avatar: ""
    property string initiale: "?"
    property real vitesse: 1.0
    property bool enMarche: true
    property color accent: "#A8D479"

    // géométrie des images générées par outils/generer.py
    readonly property real _toileL: 900
    readonly property real _toileH: 520
    readonly property real _toileR: 256
    readonly property real _k: (diametre / 2) / _toileR
    // ellipse de l'orbite A du logo (rx = 112/66, ry = 38/66, inclinée de -24°)
    readonly property real _rx: 112 / 66 * diametre / 2
    readonly property real _ry: 38 / 66 * diametre / 2
    readonly property real _inclinaison: -24 * Math.PI / 180

    property real angle: -0.35   // radians, position de la lune

    width: _toileL * _k
    height: _toileH * _k

    FrameAnimation {
        running: racine.enMarche && racine.visible
        onTriggered: racine.angle = (racine.angle + frameTime * 0.9 * racine.vitesse) % (2 * Math.PI)
    }

    // position de la lune dans le repère de l'orbite inclinée
    readonly property real _x0: _rx * Math.cos(angle)
    readonly property real _y0: _ry * Math.sin(angle)
    readonly property real luneX: width / 2 + _x0 * Math.cos(_inclinaison) - _y0 * Math.sin(_inclinaison)
    readonly property real luneY: height / 2 + _x0 * Math.sin(_inclinaison) + _y0 * Math.cos(_inclinaison)
    // devant (sous l'horizon du logo) ou derrière l'avatar
    readonly property bool luneDevant: Math.sin(angle) > 0

    Image {
        id: arriere
        anchors.fill: parent
        source: "../images/orbites-arriere.png"
        smooth: true; mipmap: true
        z: 1
    }

    // ---- avatar circulaire ----
    Item {
        id: disque
        width: racine.diametre; height: width
        anchors.centerIn: parent
        z: 2

        Image {
            id: planete
            anchors.fill: parent
            source: "../images/planete.png"
            smooth: true; mipmap: true
            visible: photo.status !== Image.Ready
        }
        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -parent.height * 0.02
            visible: planete.visible
            text: racine.initiale
            color: "#0D1310"
            opacity: 0.78
            font.family: "Inter"
            font.weight: Font.DemiBold
            font.pixelSize: parent.height * 0.42
        }

        Image {
            id: photo
            anchors.fill: parent
            source: racine.avatar
            sourceSize.width: 512; sourceSize.height: 512
            fillMode: Image.PreserveAspectCrop
            smooth: true; mipmap: true
            asynchronous: false
            visible: false
            layer.enabled: true
        }
        Rectangle {
            id: masque
            anchors.fill: parent
            radius: width / 2
            visible: false
            layer.enabled: true
            layer.smooth: true
        }
        MultiEffect {
            anchors.fill: parent
            source: photo
            visible: photo.status === Image.Ready
            maskEnabled: true
            maskSource: masque
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }
        // liseré lumineux
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            border.color: racine.accent
            border.width: Math.max(2, racine.diametre * 0.018)
            opacity: photo.status === Image.Ready ? 0.9 : 0.0
        }
    }

    Image {
        id: avant
        anchors.fill: parent
        source: "../images/orbites-avant.png"
        smooth: true; mipmap: true
        z: 3
    }

    // ---- la lune ----
    Image {
        id: luneImg
        source: "../images/lune.png"
        readonly property real echelle: 0.86 + 0.16 * Math.sin(racine.angle)
        width: racine.diametre * 0.36 * echelle
        height: width
        x: racine.luneX - width / 2
        y: racine.luneY - height / 2
        z: racine.luneDevant ? 4 : 1.5
        smooth: true
    }

    // éclat des orbites quand elles accélèrent
    opacity: 1.0
    Behavior on vitesse { NumberAnimation { duration: 900; easing.type: Easing.InQuad } }
}
