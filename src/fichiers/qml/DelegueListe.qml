import QtQuick

Item {
    id: delegue
    required property var model
    required property int index
    property var vue

    Rectangle {
        id: fondLigne
        anchors.fill: parent
        anchors.topMargin: 1
        anchors.bottomMargin: 1
        radius: 6
        color: depot.containsDrag ? Qt.alpha(theme.accent, 0.3)
             : delegue.model.selectionne ? Qt.alpha(theme.accent, theme.clair ? 0.2 : 0.16)
             : zone.containsMouse ? theme.surfaceHaute : "transparent"
    }

    Row {
        anchors.fill: parent
        opacity: delegue.model.cache ? 0.6 : 1
        Item {
            width: parent.width - colonnes.width
            height: parent.height
            IconeEntree {
                id: icone
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                taille: 22
                chemin: delegue.model.chemin
                categorie: delegue.model.categorie
                dossier: delegue.model.dossier
                miniature: delegue.model.miniature
                date: delegue.model.date
                lien: false
            }
            Text {
                id: nom
                anchors.left: icone.right
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(implicitWidth, parent.width - x - pastilles.width - 14)
                text: delegue.model.nom
                elide: Text.ElideMiddle
                font.pixelSize: 13
                color: theme.texte
            }
            Row {
                id: pastilles
                anchors.left: nom.right
                anchors.leftMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3
                Repeater {
                    model: delegue.model.etiquettes
                    delegate: Rectangle {
                        required property string modelData
                        width: 9; height: 9; radius: 4.5
                        color: (theme.clair, theme.jeton(controleur.couleurEtiquette(modelData)))
                    }
                }
            }
        }
        Row {
            id: colonnes
            Repeater {
                model: delegue.vue.colonnesListe
                delegate: Item {
                    required property var modelData
                    width: delegue.vue.largeurColonne(modelData, delegue.width)
                    height: delegue.height
                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: modelData.role === "tailleTexte" ? Text.AlignRight : Text.AlignLeft
                        text: {
                            const v = delegue.model[modelData.role]
                            if (modelData.role === "tailleTexte" && delegue.model.dossier) return "—"
                            return v === undefined || v === null ? "" : String(v)
                        }
                        elide: modelData.role === "origine" || modelData.role === "dossierParent" ? Text.ElideMiddle : Text.ElideRight
                        font.pixelSize: 13
                        color: theme.texteDoux
                    }
                }
            }
        }
    }

    ZoneElement {
        id: zone
        anchors.fill: parent
        vue: delegue.vue
        ligne: delegue.index
        selectionne: delegue.model.selectionne
        dossier: delegue.model.dossier
        chemin: delegue.model.chemin
    }

    DropArea {
        id: depot
        anchors.fill: parent
        enabled: delegue.model.dossier && delegue.vue.mode !== "corbeille"
        keys: ["text/uri-list"]
        onDropped: (d) => d.accept(controleur.deposer(d.urls, delegue.model.chemin))
    }
}
