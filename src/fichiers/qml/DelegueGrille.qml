import QtQuick

Item {
    id: delegue
    required property var model
    required property int index
    property var vue

    Rectangle {
        id: carte
        anchors.fill: parent
        anchors.margins: 4
        radius: 10
        color: depot.containsDrag ? Qt.alpha(theme.accent, 0.3)
             : delegue.model.selectionne ? Qt.alpha(theme.accent, theme.clair ? 0.2 : 0.16)
             : zone.containsMouse ? theme.surfaceHaute : "transparent"
        border.color: delegue.model.selectionne || depot.containsDrag ? Qt.alpha(theme.accent, 0.7) : "transparent"
        border.width: 1
        opacity: delegue.model.cache ? 0.6 : 1

        IconeEntree {
            id: icone
            anchors.horizontalCenter: parent.horizontalCenter
            y: 10
            taille: delegue.vue.tailleIcone
            chemin: delegue.model.chemin
            categorie: delegue.model.categorie
            dossier: delegue.model.dossier
            miniature: delegue.model.miniature
            date: delegue.model.date
            lien: delegue.model.lien
        }

        Row {
            // pastilles d'étiquettes
            anchors.right: icone.right
            anchors.top: icone.top
            anchors.topMargin: delegue.model.dossier ? icone.height * 0.22 : 0
            spacing: -3
            Repeater {
                model: delegue.model.etiquettes
                delegate: Rectangle {
                    required property string modelData
                    width: 12; height: 12; radius: 6
                    color: (theme.clair, theme.jeton(controleur.couleurEtiquette(modelData)))
                    border.color: theme.surface
                    border.width: 2
                }
            }
        }

        Text {
            anchors.top: icone.bottom
            anchors.topMargin: 6
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            horizontalAlignment: Text.AlignHCenter
            text: delegue.model.nom
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            maximumLineCount: delegue.model.selectionne ? 3 : 2
            elide: Text.ElideRight
            font.pixelSize: 13
            lineHeight: 0.95
            color: theme.texte
        }
    }

    ZoneElement {
        id: zone
        anchors.fill: carte
        vue: delegue.vue
        ligne: delegue.index
        selectionne: delegue.model.selectionne
        dossier: delegue.model.dossier
        chemin: delegue.model.chemin
    }

    DropArea {
        id: depot
        anchors.fill: carte
        enabled: delegue.model.dossier && delegue.vue.mode !== "corbeille"
        keys: ["text/uri-list"]
        onDropped: (d) => d.accept(controleur.deposer(d.urls, delegue.model.chemin))
    }

    InfoBulle {
        visible: zone.containsMouse && !zone.pressed
        delay: 1100
        text: delegue.model.nom + (delegue.model.dossier ? "" : "\n" + delegue.model.type + " — " + delegue.model.tailleTexte)
              + "\nModifié : " + delegue.model.dateTexte
    }
}
