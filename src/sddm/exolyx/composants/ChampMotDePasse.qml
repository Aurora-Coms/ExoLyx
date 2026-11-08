// Champ mot de passe unique, vert, avec bouton de validation intégré.
// `secouer()` déclenche le tremblement d'erreur.
import QtQuick
import QtQuick.Controls.Basic

Item {
    id: racine
    property real s: 1.0
    property bool occupe: false
    property bool enErreur: false
    property alias text: champ.text
    property alias champ: champ
    signal valide()

    width: 360 * s
    height: 52 * s

    function secouer() { secousse.restart() }
    function vider() { champ.text = "" }
    function saisir(t) { champ.insert(champ.cursorPosition, t) }
    function prendreFocus() { champ.forceActiveFocus() }

    transform: Translate { id: decalage; x: 0 }

    SequentialAnimation {
        id: secousse
        NumberAnimation { target: decalage; property: "x"; to: -20 * racine.s; duration: 55; easing.type: Easing.OutQuad }
        NumberAnimation { target: decalage; property: "x"; to: 17 * racine.s; duration: 80 }
        NumberAnimation { target: decalage; property: "x"; to: -12 * racine.s; duration: 75 }
        NumberAnimation { target: decalage; property: "x"; to: 8 * racine.s; duration: 70 }
        NumberAnimation { target: decalage; property: "x"; to: -4 * racine.s; duration: 60 }
        NumberAnimation { target: decalage; property: "x"; to: 0; duration: 55; easing.type: Easing.InQuad }
    }

    TextField {
        id: champ
        anchors.fill: parent
        echoMode: TextInput.Password
        passwordCharacter: "●"
        passwordMaskDelay: 0
        enabled: !racine.occupe
        placeholderText: "Mot de passe"
        placeholderTextColor: "#97A893"
        color: "#E6EFE1"
        selectionColor: "#A8D479"
        selectedTextColor: "#0D1310"
        font.family: "Inter"
        font.pixelSize: 17 * racine.s
        font.letterSpacing: echoMode === TextInput.Password && text.length > 0 ? 3 * racine.s : 0
        leftPadding: 22 * racine.s
        rightPadding: bouton.width + 14 * racine.s
        verticalAlignment: TextInput.AlignVCenter
        inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
        background: Rectangle {
            radius: height / 2
            color: Qt.rgba(0.11, 0.15, 0.13, 0.82)
            border.width: Math.max(1.5, 2 * racine.s)
            border.color: racine.enErreur ? "#E5766B" : (champ.activeFocus ? "#A8D479" : "#6FA845")
            Behavior on border.color { ColorAnimation { duration: 180 } }
            // lueur verte
            Rectangle {
                anchors.fill: parent
                anchors.margins: -4 * racine.s
                radius: height / 2
                color: "transparent"
                border.width: 4 * racine.s
                border.color: racine.enErreur ? "#E5766B" : "#A8D479"
                opacity: champ.activeFocus ? 0.18 : 0
                Behavior on opacity { NumberAnimation { duration: 200 } }
            }
        }
        Keys.onReturnPressed: racine.valide()
        Keys.onEnterPressed: racine.valide()
    }

    Rectangle {
        id: bouton
        width: parent.height - 10 * racine.s
        height: width
        radius: width / 2
        anchors.right: parent.right
        anchors.rightMargin: 5 * racine.s
        anchors.verticalCenter: parent.verticalCenter
        color: zone.containsMouse ? "#BDD479" : "#A8D479"
        Image {
            anchors.centerIn: parent
            width: parent.width * 0.5; height: width
            source: "../images/icones/fleche-sombre.png"
            smooth: true; mipmap: true
            visible: !racine.occupe
        }
        // anneau de chargement pendant la connexion
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.42; height: width
            radius: width / 2
            color: "transparent"
            border.width: 2.5 * racine.s
            border.color: "#0D1310"
            visible: racine.occupe
            Rectangle {
                width: parent.width * 0.5; height: width
                color: "#A8D479"
                anchors.right: parent.right; anchors.top: parent.top
            }
            RotationAnimation on rotation {
                running: racine.occupe
                from: 0; to: 360; duration: 800; loops: Animation.Infinite
            }
        }
        MouseArea {
            id: zone
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: racine.valide()
        }
    }
}
