import QtQuick
import QtQuick.Window

// Icône d'un élément : miniature si disponible, sinon icône de type ou de dossier
Item {
    id: racine
    property string chemin: ""
    property string categorie: "fichier"
    property bool dossier: false
    property bool miniature: false
    property real date: 0
    property string embleme: ""
    property real taille: 64
    property bool lien: false
    width: taille
    height: taille

    readonly property string urlType: dossier
        ? "image://icone/d/" + embleme + "/" + (theme.clair ? 1 : 0)
        : "image://icone/t/" + categorie + "/" + (theme.clair ? 1 : 0)

    Image {
        id: type
        anchors.fill: parent
        source: racine.urlType
        sourceSize: Qt.size(Math.ceil(racine.taille * Screen.devicePixelRatio), Math.ceil(racine.taille * Screen.devicePixelRatio))
        visible: !vignette.visible
        smooth: true
    }

    Rectangle {
        // cadre discret autour des miniatures
        anchors.centerIn: vignette
        width: vignette.paintedWidth + 4
        height: vignette.paintedHeight + 4
        radius: 4
        color: "transparent"
        border.color: theme.bordure
        visible: vignette.visible && vignette.paintedWidth > 0
    }

    Image {
        id: vignette
        anchors.fill: parent
        anchors.margins: racine.taille > 40 ? 3 : 1
        asynchronous: true
        fillMode: Image.PreserveAspectFit
        visible: racine.miniature && status === Image.Ready
        source: racine.miniature && racine.chemin ? "image://miniature/" + encodeURIComponent(racine.chemin) + "?" + racine.date : ""
        sourceSize: Qt.size(racine.taille <= 128 / Screen.devicePixelRatio ? 128 : 256,
                            racine.taille <= 128 / Screen.devicePixelRatio ? 128 : 256)
        smooth: true
        mipmap: true
    }

    Rectangle {
        // emblème de lien symbolique
        visible: racine.lien
        width: Math.max(14, racine.taille * 0.3)
        height: width
        radius: width / 2
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: theme.surface
        border.color: theme.bordure
        Glyphe {
            anchors.centerIn: parent
            nom: "lien"
            taille: parent.width * 0.7
            couleur: theme.info
        }
    }
}
