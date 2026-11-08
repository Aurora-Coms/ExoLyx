import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

// Panneau d'aperçu de l'élément sélectionné : image, PDF (pages), texte, dossier
Rectangle {
    id: panneau
    property var modele: controleur.onglet ? controleur.onglet.modeleFichiers : null
    property var infos: ({ genre: "aucun" })
    property int page: 0
    color: theme.surface
    radius: 10
    border.color: theme.bordure

    function actualiser() {
        page = 0
        if (!modele || modele.nbSelection !== 1 || modele.ligneCourante < 0) {
            infos = { genre: "aucun" }
            return
        }
        const e = modele.entree(modele.ligneCourante)
        infos = e ? controleur.infosApercu(e.chemin) : { genre: "aucun" }
    }
    Timer { id: delai; interval: 120; onTriggered: panneau.actualiser() }
    Connections {
        target: panneau.modele
        function onSelectionChange() { delai.restart() }
        function onRecharge() { delai.restart() }
    }
    onModeleChanged: delai.restart()
    onVisibleChanged: if (visible) delai.restart()

    readonly property string url: infos.chemin ? encodeURIComponent(infos.chemin) : ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        // --- zone visuelle ---
        Rectangle {
            id: zoneVisuelle
            Layout.fillWidth: true
            Layout.fillHeight: panneau.infos.genre === "texte" || panneau.infos.genre === "pdf" || panneau.infos.genre === "image"
            Layout.preferredHeight: panneau.infos.genre === "aucun" || panneau.infos.genre === "dossier" ? 170 : 260
            radius: 8
            color: theme.fond
            clip: true

            Image {
                id: imageApercu
                anchors.fill: parent
                anchors.margins: 8
                visible: panneau.infos.genre === "image" || panneau.infos.genre === "pdf"
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                cache: false
                source: visible && panneau.url
                    ? "image://apercu/" + panneau.url + "?page=" + panneau.page + "&t=" + panneau.infos.mtime
                    : ""
                sourceSize: Qt.size(Math.ceil(width * Screen.devicePixelRatio), Math.ceil(height * Screen.devicePixelRatio))
                smooth: true
                mipmap: true
            }
            Text {
                anchors.centerIn: parent
                visible: imageApercu.visible && imageApercu.status === Image.Loading
                text: "Chargement…"
                color: theme.texteDoux
                font.pixelSize: 12
            }

            ScrollView {
                anchors.fill: parent
                anchors.margins: 2
                visible: panneau.infos.genre === "texte"
                ScrollBar.vertical: BarreDefilement {}
                TextArea {
                    readOnly: true
                    text: panneau.infos.genre === "texte" ? panneau.infos.texte : ""
                    font.family: "JetBrains Mono"
                    font.pixelSize: 12
                    color: theme.texte
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    selectionColor: Qt.alpha(theme.accent, 0.45)
                    background: null
                    padding: 10
                }
            }

            IconeEntree {
                anchors.centerIn: parent
                visible: panneau.infos.genre === "dossier" || panneau.infos.genre === "aucun" && panneau.infos.nom !== undefined
                taille: 96
                dossier: panneau.infos.genre === "dossier"
                categorie: panneau.infos.categorie || "fichier"
            }
            Column {
                anchors.centerIn: parent
                spacing: 10
                visible: panneau.infos.nom === undefined
                Glyphe { anchors.horizontalCenter: parent.horizontalCenter; nom: "apercu"; taille: 40; couleur: Qt.alpha(theme.texteDoux, 0.5) }
                Text {
                    width: zoneVisuelle.width - 40
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: panneau.modele && panneau.modele.nbSelection > 1
                          ? panneau.modele.nbSelection + " éléments sélectionnés"
                          : "Sélectionnez un fichier pour l’aperçu"
                    color: theme.texteDoux
                    font.pixelSize: 13
                }
            }
        }

        // --- pages PDF ---
        RowLayout {
            visible: panneau.infos.genre === "pdf" && panneau.infos.pages > 1
            Layout.alignment: Qt.AlignHCenter
            spacing: 6
            BoutonIcone { icone: "chevronGauche"; actif: panneau.page > 0; onClique: panneau.page-- ; bulle: "Page précédente" }
            Text {
                text: "Page " + (panneau.page + 1) + " sur " + panneau.infos.pages
                font.pixelSize: 13
                color: theme.texteDoux
            }
            BoutonIcone { icone: "chevron"; actif: panneau.page < panneau.infos.pages - 1; onClique: panneau.page++ ; bulle: "Page suivante" }
        }

        // --- informations ---
        ColumnLayout {
            visible: panneau.infos.nom !== undefined
            Layout.fillWidth: true
            spacing: 8
            Text {
                Layout.fillWidth: true
                text: panneau.infos.nom || ""
                wrapMode: Text.WrapAnywhere
                maximumLineCount: 3
                elide: Text.ElideRight
                font.pixelSize: 15
                font.weight: Font.DemiBold
                color: theme.texte
            }
            GridLayout {
                columns: 2
                columnSpacing: 12
                rowSpacing: 5
                Layout.fillWidth: true
                component Cle: Text { font.pixelSize: 12; color: theme.texteDoux }
                component Valeur: Text { font.pixelSize: 12; color: theme.texte; Layout.fillWidth: true; elide: Text.ElideRight }
                Cle { text: "Type" }
                Valeur { text: panneau.infos.type || "" }
                Cle { text: panneau.infos.dossier ? "Contenu" : "Taille"; visible: (panneau.infos.taille || panneau.infos.contenu) ? true : false }
                Valeur { text: panneau.infos.dossier ? (panneau.infos.contenu || "") : (panneau.infos.taille || ""); visible: (panneau.infos.taille || panneau.infos.contenu) ? true : false }
                Cle { text: "Dimensions"; visible: !!panneau.infos.dimensions }
                Valeur { text: panneau.infos.dimensions || ""; visible: !!panneau.infos.dimensions }
                Cle { text: "Pages"; visible: panneau.infos.genre === "pdf" }
                Valeur { text: String(panneau.infos.pages || ""); visible: panneau.infos.genre === "pdf" }
                Cle { text: "Modifié" }
                Valeur { text: panneau.infos.date || "" }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                visible: !!panneau.infos.etiquettes && panneau.infos.etiquettes.length > 0
                Repeater {
                    model: panneau.infos.etiquettes || []
                    delegate: Rectangle {
                        required property string modelData
                        readonly property string couleur: (theme.clair, theme.jeton(controleur.couleurEtiquette(modelData)))
                        height: 24
                        width: texteEtq.implicitWidth + 20
                        radius: 12
                        color: Qt.alpha(couleur, 0.15)
                        border.color: Qt.alpha(couleur, 0.5)
                        Text { id: texteEtq; anchors.centerIn: parent; text: parent.modelData; font.pixelSize: 12; color: theme.texte }
                    }
                }
            }
            Bouton {
                texte: panneau.infos.dossier ? "Ouvrir le dossier" : "Ouvrir"
                principal: true
                Layout.fillWidth: true
                Layout.topMargin: 4
                visible: controleur.onglet && controleur.onglet.mode !== "corbeille"
                onClique: controleur.ouvrirChemin(panneau.infos.chemin)
            }
        }
        Item { Layout.fillHeight: !zoneVisuelle.Layout.fillHeight; Layout.fillWidth: true }
    }
}
