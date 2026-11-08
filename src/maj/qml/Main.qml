// SPDX-License-Identifier: GPL-3.0-or-later
// Mises à jour ExoLyx — fenêtre principale.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "composants"

ApplicationWindow {
    id: fenetre
    readonly property var p: ctrl.palette
    width: 900; height: 640
    minimumWidth: 720; minimumHeight: 520
    visible: false
    title: "Mises à jour"
    color: p.fond
    font.family: "Inter"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 16

        // ---- En-tête --------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Image {
                source: ctrl.logo
                Layout.preferredWidth: 56; Layout.preferredHeight: 56
                sourceSize: Qt.size(112, 112)
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "Mises à jour"; color: fenetre.p.texte; font.pixelSize: 26; font.weight: Font.Bold }
                Text {
                    Layout.fillWidth: true
                    text: ctrl.resume
                    color: ctrl.etat === "erreur" ? fenetre.p.erreur : fenetre.p.texteDoux
                    font.pixelSize: 14; elide: Text.ElideRight
                }
            }
            Bouton {
                text: "Vérifier"
                enabled: !ctrl.occupe && ctrl.etat !== "verification"
                onClicked: ctrl.verifier()
            }
        }

        // ---- Bandeau instantanés -------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: bandeau.implicitHeight + 24
            radius: 10
            color: fenetre.p.accentVoile
            border.color: fenetre.p.bordure
            RowLayout {
                id: bandeau
                anchors.fill: parent; anchors.margins: 12; anchors.leftMargin: 16
                spacing: 14
                // bouclier
                Canvas {
                    Layout.preferredWidth: 24; Layout.preferredHeight: 28
                    property color teinte: fenetre.p.accent
                    property color coche: fenetre.p.surAccent
                    onTeinteChanged: requestPaint()
                    onPaint: {
                        var g = getContext("2d");
                        g.reset();
                        g.fillStyle = teinte;
                        g.beginPath();
                        g.moveTo(12, 1); g.lineTo(23, 5); g.lineTo(23, 13);
                        g.bezierCurveTo(23, 20, 18, 25, 12, 27);
                        g.bezierCurveTo(6, 25, 1, 20, 1, 13);
                        g.lineTo(1, 5); g.closePath(); g.fill();
                        g.strokeStyle = coche; g.lineWidth = 2.6; g.lineCap = "round"; g.lineJoin = "round";
                        g.beginPath(); g.moveTo(7, 14); g.lineTo(10.5, 17.5); g.lineTo(17, 10); g.stroke();
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: "Un instantané de sécurité est créé automatiquement avant et après chaque mise à jour (snap-pac). En cas de souci, vous pourrez revenir en arrière."
                    color: fenetre.p.texte; font.pixelSize: 13; wrapMode: Text.WordWrap
                }
                Bouton {
                    text: "Restaurer un instantané"
                    onClicked: { ctrl.chargerInstantanes(); fenetreInstantanes.open() }
                }
            }
        }

        // ---- Bandeau redémarrage ----------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            visible: ctrl.redemarrageRequis
            implicitHeight: 64
            radius: 10
            color: fenetre.p.attentionVoile
            border.color: fenetre.p.attention
            RowLayout {
                anchors.fill: parent; anchors.margins: 12; anchors.leftMargin: 16
                spacing: 14
                Text { text: "↻"; color: fenetre.p.attention; font.pixelSize: 24; font.bold: true }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 1
                    Text { text: "Redémarrage nécessaire"; color: fenetre.p.texte; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Text { Layout.fillWidth: true; text: "Mis à jour : " + ctrl.paquetsRedemarrage + ". Redémarrez pour utiliser les nouvelles versions."; color: fenetre.p.texteDoux; font.pixelSize: 12; elide: Text.ElideRight }
                }
                Bouton { principal: true; text: "Redémarrer maintenant"; onClicked: ctrl.redemarrer() }
            }
        }

        // ---- Liste ---------------------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 10
            color: fenetre.p.surface
            border.color: fenetre.p.bordure
            clip: true

            // en-têtes de colonnes
            RowLayout {
                id: entetes
                visible: liste.count > 0
                anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: 18; rightMargin: 18 }
                height: 36
                Text { Layout.fillWidth: true; text: "Paquet"; color: fenetre.p.texteDoux; font.pixelSize: 12; font.weight: Font.DemiBold }
                Text { Layout.preferredWidth: 300; text: "Version"; color: fenetre.p.texteDoux; font.pixelSize: 12; font.weight: Font.DemiBold }
                Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: "Taille"; color: fenetre.p.texteDoux; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
            Rectangle { visible: entetes.visible; y: 36; width: parent.width; height: 1; color: fenetre.p.bordure }

            ListView {
                id: liste
                anchors { fill: parent; topMargin: 37; bottomMargin: 2 }
                model: ctrl.majs
                boundsBehavior: Flickable.StopAtBounds
                section.property: "section"
                section.delegate: Rectangle {
                    required property string section
                    width: ListView.view.width; height: 32
                    color: fenetre.p.surfaceHaute
                    Text { x: 18; anchors.verticalCenter: parent.verticalCenter; text: parent.section; color: fenetre.p.accent; font.pixelSize: 12; font.weight: Font.DemiBold; font.capitalization: Font.AllUppercase; font.letterSpacing: 0.6 }
                }
                delegate: Rectangle {
                    id: ligne
                    required property var modelData
                    required property int index
                    width: ListView.view.width; height: 40
                    color: index % 2 ? "transparent" : (ctrl.sombre ? "#0FFFFFFF" : "#06000000")
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18
                        spacing: 8
                        Text { text: ligne.modelData.nom; color: fenetre.p.texte; font.pixelSize: 14; elide: Text.ElideRight; Layout.maximumWidth: 320 }
                        Rectangle {
                            visible: ligne.modelData.redemarrage
                            implicitWidth: tr.implicitWidth + 12; implicitHeight: 18; radius: 4
                            color: fenetre.p.attentionVoile
                            Text { id: tr; anchors.centerIn: parent; text: "redémarrage"; color: fenetre.p.attention; font.pixelSize: 10 }
                        }
                        Item { Layout.fillWidth: true }
                        Row {
                            Layout.preferredWidth: 300
                            spacing: 6
                            Text { width: Math.min(implicitWidth, 130); text: ligne.modelData.ancienne; color: fenetre.p.texteDoux; font.family: "JetBrains Mono"; font.pixelSize: 12; elide: Text.ElideRight }
                            Text { text: "→"; color: fenetre.p.accent; font.pixelSize: 12 }
                            Text { width: Math.min(implicitWidth, 150); text: ligne.modelData.nouvelle; color: fenetre.p.texte; font.family: "JetBrains Mono"; font.pixelSize: 12; elide: Text.ElideRight }
                        }
                        Text { Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; text: ligne.modelData.taille; color: fenetre.p.texteDoux; font.pixelSize: 12 }
                    }
                }
                ScrollBar.vertical: ScrollBar {
                    visible: liste.contentHeight > liste.height
                    contentItem: Rectangle { implicitWidth: 6; radius: 3; color: fenetre.p.bordure }
                }
            }

            // états vides
            Column {
                anchors.centerIn: parent
                visible: liste.count === 0
                spacing: 12
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 64; height: 64; radius: 32
                    color: ctrl.etat === "erreur" ? fenetre.p.attentionVoile : fenetre.p.accentVoile
                    Text {
                        anchors.centerIn: parent
                        text: ctrl.etat === "verification" ? "…" : ctrl.etat === "erreur" ? "!" : "✓"
                        color: ctrl.etat === "erreur" ? fenetre.p.attention : fenetre.p.accent
                        font.pixelSize: 30; font.bold: true
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: ctrl.etat === "verification" ? "Recherche des mises à jour…"
                        : ctrl.etat === "erreur" ? "Vérification impossible"
                        : ctrl.etat === "termine" ? "Mise à jour terminée" : "Votre système est à jour"
                    color: fenetre.p.texte; font.pixelSize: 18; font.weight: Font.DemiBold
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: ctrl.etat === "erreur" ? "Vérifiez votre connexion Internet puis réessayez." : ctrl.derniereVerification
                    color: fenetre.p.texteDoux; font.pixelSize: 13
                }
            }
        }

        // ---- Progression + journal --------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            visible: ctrl.occupe || ctrl.message !== ""
            implicitHeight: prog.implicitHeight + 24
            radius: 10
            color: fenetre.p.surface
            border.color: ctrl.message !== "" && !ctrl.occupe && ctrl.etat !== "termine" ? fenetre.p.erreur : fenetre.p.bordure
            ColumnLayout {
                id: prog
                anchors.fill: parent; anchors.margins: 12; anchors.leftMargin: 16
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: ctrl.libelle; color: fenetre.p.texte; font.pixelSize: 13; elide: Text.ElideRight }
                    Text { text: Math.round(ctrl.progression * 100) + " %"; color: fenetre.p.texteDoux; font.pixelSize: 13 }
                    Text {
                        text: ctrl.journalDeplie ? "Masquer le journal ▴" : "Afficher le journal ▾"
                        color: fenetre.p.accent; font.pixelSize: 13
                        MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: ctrl.journalDeplie = !ctrl.journalDeplie }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 8; radius: 4; color: fenetre.p.surfaceHaute
                    Rectangle {
                        height: parent.height; radius: 4; width: parent.width * ctrl.progression
                        color: fenetre.p.accent
                        Behavior on width { NumberAnimation { duration: 250 } }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 140
                    visible: ctrl.journalDeplie
                    radius: 6; color: fenetre.p.journal; border.color: fenetre.p.bordure
                    ScrollView {
                        anchors.fill: parent; anchors.margins: 6
                        TextArea {
                            readOnly: true; text: ctrl.journal; background: null
                            color: fenetre.p.texteDoux
                            font.family: "JetBrains Mono"; font.pixelSize: 11
                            wrapMode: TextArea.WrapAnywhere
                            onTextChanged: cursorPosition = length
                        }
                    }
                }
            }
        }

        // ---- Pied ----------------------------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Text {
                Layout.fillWidth: true
                visible: ctrl.redemarrageAnnonce && !ctrl.occupe
                text: "Ces mises à jour nécessiteront un redémarrage."
                color: fenetre.p.texteDoux; font.pixelSize: 13
            }
            Item { Layout.fillWidth: true; visible: !(ctrl.redemarrageAnnonce && !ctrl.occupe) }
            Bouton { text: "Fermer"; onClicked: fenetre.close() }
            Bouton {
                principal: true
                text: ctrl.occupe ? "Mise à jour en cours…" : "Tout mettre à jour"
                enabled: !ctrl.occupe && ctrl.nombre > 0
                onClicked: ctrl.toutMettreAJour()
            }
        }
    }

    // ---- Fenêtre « Restaurer un instantané » ------------------------------------
    Popup {
        id: fenetreInstantanes
        objectName: "fenetreInstantanes"
        anchors.centerIn: parent
        width: Math.min(parent.width - 60, 780)
        height: Math.min(parent.height - 60, 540)
        modal: true
        padding: 24
        background: Rectangle { radius: 14; color: fenetre.p.surface; border.color: fenetre.p.bordure }
        Overlay.modal: Rectangle { color: "#99000000" }

        contentItem: ColumnLayout {
            spacing: 12
            Text { text: "Restaurer un instantané"; color: fenetre.p.texte; font.pixelSize: 20; font.weight: Font.Bold }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: fenetre.p.texteDoux; font.pixelSize: 13; lineHeight: 1.2
                textFormat: Text.StyledText
                text: "<b>1.</b> Redémarrez l'ordinateur et choisissez « <b>Instantanés ExoLyx</b> » dans le menu de démarrage.<br>"
                    + "<b>2.</b> Sélectionnez l'instantané « pre » pris juste avant la mise à jour : le système démarre tel qu'il était.<br>"
                    + "<b>3.</b> Si tout fonctionne, rendez ce retour permanent dans un terminal : <tt>sudo snapper rollback</tt> puis redémarrez.<br>"
                    + "Vos documents (/home) ne sont jamais modifiés par une restauration."
            }
            Text { text: "Instantanés disponibles"; color: fenetre.p.texte; font.pixelSize: 14; font.weight: Font.DemiBold; Layout.topMargin: 4 }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 6; color: fenetre.p.journal; border.color: fenetre.p.bordure
                ScrollView {
                    anchors.fill: parent; anchors.margins: 8
                    TextArea {
                        readOnly: true; background: null
                        text: ctrl.instantanes !== "" ? ctrl.instantanes : "Chargement…"
                        color: fenetre.p.texte
                        font.family: "JetBrains Mono"; font.pixelSize: 11
                        wrapMode: TextArea.NoWrap
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Bouton { text: "Actualiser"; onClicked: ctrl.chargerInstantanes() }
                Bouton { principal: true; text: "Fermer"; onClicked: fenetreInstantanes.close() }
            }
        }
    }
}
