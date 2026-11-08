import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Contenu d'un dossier (ou de résultats) en grille ou en liste détaillée
FocusScope {
    id: racine
    property var onglet: controleur.onglet
    readonly property var modele: onglet ? onglet.modeleFichiers : null
    readonly property string mode: onglet ? onglet.mode : "dossier"
    readonly property bool enGrille: controleur.vue === "grille"
    readonly property var vueActive: enGrille ? grille : liste
    readonly property int tailleIcone: controleur.tailleIcones - 32
    readonly property int colonnes: Math.max(1, Math.floor(grille.width / grille.cellWidth))

    function focaliser() { vueActive.forceActiveFocus() }

    function montrerLigne(i) {
        if (i >= 0) vueActive.positionViewAtIndex(i, enGrille ? GridView.Contain : ListView.Contain)
    }

    Connections {
        target: racine.modele
        function onSelectionChange() {
            if (racine.modele && racine.modele.ligneCourante >= 0) racine.montrerLigne(racine.modele.ligneCourante)
        }
        function onRecharge() { racine.vueActive.contentY = racine.vueActive.originY }
    }

    // --- clavier : flèches, Début/Fin, saisie au vol ---
    property string saisie: ""
    Timer { id: oubliSaisie; interval: 900; onTriggered: racine.saisie = "" }

    function deplacerCurseur(delta, s) {
        if (!modele || modele.count === 0) return
        let i = modele.ligneCourante
        if (i < 0) i = delta > 0 ? -1 : modele.count
        const cible = Math.max(0, Math.min(modele.count - 1, i + delta))
        modele.selectionner(cible, (s & Qt.ShiftModifier) ? "etendre" : "seul")
        montrerLigne(cible)
    }

    Keys.onPressed: (e) => {
        if (!modele) return
        const pas = enGrille ? colonnes : 1
        const page = Math.max(1, Math.floor(vueActive.height / (enGrille ? grille.cellHeight : 34))) * pas
        switch (e.key) {
        case Qt.Key_Left: if (enGrille) { deplacerCurseur(-1, e.modifiers); e.accepted = true } return
        case Qt.Key_Right: if (enGrille) { deplacerCurseur(1, e.modifiers); e.accepted = true } return
        case Qt.Key_Up: deplacerCurseur(-pas, e.modifiers); e.accepted = true; return
        case Qt.Key_Down: deplacerCurseur(pas, e.modifiers); e.accepted = true; return
        case Qt.Key_PageUp: deplacerCurseur(-page, e.modifiers); e.accepted = true; return
        case Qt.Key_PageDown: deplacerCurseur(page, e.modifiers); e.accepted = true; return
        case Qt.Key_Home: deplacerCurseur(-modele.count, e.modifiers); e.accepted = true; return
        case Qt.Key_End: deplacerCurseur(modele.count, e.modifiers); e.accepted = true; return
        case Qt.Key_Escape:
            if (onglet.rechercheEnCours) onglet.annulerRecherche()
            else modele.viderSelection()
            e.accepted = true
            return
        }
        if (e.text.length === 1 && e.text > " " && !(e.modifiers & (Qt.ControlModifier | Qt.AltModifier))) {
            saisie += e.text
            oubliSaisie.restart()
            const i = modele.ligneParPrefixe(saisie)
            if (i >= 0) { modele.selectionner(i, "seul"); montrerLigne(i) }
            e.accepted = true
        }
    }

    // --- colonnes de la liste selon le contexte ---
    readonly property var colonnesListe: mode === "corbeille"
        ? [{ titre: "Emplacement d’origine", role: "origine", largeur: 0.34, tri: "" },
           { titre: "Supprimé", role: "dateSuppressionTexte", largeur: 150, tri: "" },
           { titre: "Taille", role: "tailleTexte", largeur: 90, tri: "taille" }]
        : (mode === "recherche" || mode === "etiquette")
        ? [{ titre: "Dossier", role: "dossierParent", largeur: 0.3, tri: "" },
           { titre: "Modifié", role: "dateTexte", largeur: 150, tri: "date" },
           { titre: "Taille", role: "tailleTexte", largeur: 90, tri: "taille" }]
        : [{ titre: "Modifié", role: "dateTexte", largeur: 160, tri: "date" },
           { titre: "Type", role: "type", largeur: 150, tri: "type" },
           { titre: "Taille", role: "tailleTexte", largeur: 90, tri: "taille" }]

    function largeurColonne(c, total) {
        return c.largeur < 1 ? Math.round(total * c.largeur) : c.largeur
    }

    // --- en-tête de la liste ---
    Rectangle {
        id: entete
        visible: !racine.enGrille
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        height: visible ? 34 : 0
        color: "transparent"
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: theme.bordure }

        component Colonne: Item {
            id: col
            property string titre
            property string tri
            property bool alignerDroite: false
            height: entete.height
            readonly property bool active: tri !== "" && controleur.tri === tri
            Rectangle {
                anchors.fill: parent
                anchors.margins: 3
                radius: 5
                color: zoneCol.containsMouse && col.tri !== "" ? theme.surfaceHaute : "transparent"
            }
            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: col.alignerDroite ? undefined : parent.left
                anchors.right: col.alignerDroite ? parent.right : undefined
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 4
                layoutDirection: col.alignerDroite ? Qt.RightToLeft : Qt.LeftToRight
                Text {
                    text: col.titre
                    font.pixelSize: 12
                    font.weight: col.active ? Font.DemiBold : Font.Normal
                    color: col.active ? theme.texte : theme.texteDoux
                }
                Glyphe {
                    visible: col.active
                    nom: "chevronBas"
                    taille: 12
                    couleur: theme.accent
                    rotation: controleur.triDecroissant ? 0 : 180
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            MouseArea {
                id: zoneCol
                anchors.fill: parent
                hoverEnabled: true
                onClicked: {
                    if (col.tri === "") return
                    if (col.active) controleur.triDecroissant = !controleur.triDecroissant
                    else { controleur.tri = col.tri; controleur.triDecroissant = col.tri === "date" || col.tri === "taille" }
                }
            }
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: 0
            Colonne {
                titre: "Nom"; tri: "nom"
                width: parent.width - colonnesEntete.width
            }
            Row {
                id: colonnesEntete
                Repeater {
                    model: racine.colonnesListe
                    delegate: Colonne {
                        required property var modelData
                        titre: modelData.titre
                        tri: modelData.tri
                        alignerDroite: modelData.role === "tailleTexte"
                        width: racine.largeurColonne(modelData, entete.width)
                    }
                }
            }
        }
    }

    // --- zone de fond : sélection rectangle, molette, menu, dépôt ---
    MouseArea {
        id: fond
        anchors.fill: parent
        anchors.topMargin: entete.height
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        property bool bande: false
        property point origine
        property point courant
        property bool additif: false

        function pointContenu(x, y) { return fond.mapToItem(racine.vueActive.contentItem, x, y) }

        function majBande() {
            const a = origine
            const b = pointContenu(courant.x, courant.y)
            const x1 = Math.min(a.x, b.x), x2 = Math.max(a.x, b.x)
            const y1 = Math.min(a.y, b.y), y2 = Math.max(a.y, b.y)
            const lignes = []
            if (racine.enGrille) {
                const cw = grille.cellWidth, ch = grille.cellHeight, n = racine.colonnes
                for (let r = Math.max(0, Math.floor(y1 / ch)); r <= Math.floor(y2 / ch); r++) {
                    for (let c = Math.max(0, Math.floor(x1 / cw)); c <= Math.min(n - 1, Math.floor(x2 / cw)); c++) {
                        // la carte est en retrait de 4 px dans sa cellule
                        if (x2 < c * cw + 4 || x1 > (c + 1) * cw - 4 || y2 < r * ch + 4 || y1 > (r + 1) * ch - 4) continue
                        const i = r * n + c
                        if (i < racine.modele.count) lignes.push(i)
                    }
                }
            } else {
                const h = 34
                for (let r = Math.max(0, Math.floor(y1 / h)); r <= Math.floor(y2 / h); r++)
                    if (r < racine.modele.count) lignes.push(r)
            }
            racine.modele.selectionnerLignes(lignes, additif)
        }

        onPressed: (s) => {
            racine.vueActive.forceActiveFocus()
            if (s.button === Qt.RightButton) {
                if (racine.modele) racine.modele.viderSelection()
                fenetre.menuFond(fond, s.x, s.y)
                return
            }
            additif = (s.modifiers & (Qt.ControlModifier | Qt.ShiftModifier)) !== 0
            if (!additif && racine.modele) racine.modele.viderSelection()
            origine = pointContenu(s.x, s.y)
            courant = Qt.point(s.x, s.y)
            bande = true
        }
        onPositionChanged: (s) => {
            if (!bande) return
            courant = Qt.point(s.x, s.y)
            majBande()
        }
        onReleased: bande = false
        onCanceled: bande = false
        onWheel: (w) => {
            const v = racine.vueActive
            const delta = w.pixelDelta.y !== 0 ? w.pixelDelta.y : w.angleDelta.y / 120 * 3 * 36
            const max = Math.max(v.originY, v.originY + v.contentHeight - v.height)
            v.contentY = Math.max(v.originY, Math.min(max, v.contentY - delta))
        }

        // défilement automatique pendant la sélection rectangle
        Timer {
            interval: 30
            repeat: true
            running: fond.bande && (fond.courant.y < 0 || fond.courant.y > fond.height)
            onTriggered: {
                const v = racine.vueActive
                const d = fond.courant.y < 0 ? fond.courant.y : fond.courant.y - fond.height
                const max = Math.max(v.originY, v.originY + v.contentHeight - v.height)
                v.contentY = Math.max(v.originY, Math.min(max, v.contentY + d * 0.4))
                fond.majBande()
            }
        }

        DropArea {
            id: depotFond
            anchors.fill: parent
            keys: ["text/uri-list"]
            enabled: racine.onglet && (racine.onglet.dossierCourant !== "" || racine.mode === "corbeille")
            onDropped: (d) => d.accept(controleur.deposer(d.urls, racine.mode === "corbeille" ? "corbeille:" : racine.onglet.dossierCourant))
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: 10
            color: "transparent"
            border.color: theme.accent
            border.width: 2
            visible: depotFond.containsDrag && !depotFond.drag.source
            opacity: 0.6
        }

        // --- grille ---
        GridView {
            id: grille
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 6
            anchors.topMargin: 8
            visible: racine.enGrille
            model: visible ? racine.modele : null
            interactive: false
            keyNavigationEnabled: false
            clip: true
            focus: visible
            cacheBuffer: 400
            cellWidth: Math.floor(Math.max(controleur.tailleIcones + 30, (width) / Math.max(1, Math.floor(width / (controleur.tailleIcones + 30)))))
            cellHeight: racine.tailleIcone + 66
            ScrollBar.vertical: BarreDefilement {}
            delegate: DelegueGrille {
                vue: racine
                width: grille.cellWidth
                height: grille.cellHeight
            }
        }

        // --- liste ---
        ListView {
            id: liste
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 2
            visible: !racine.enGrille
            model: visible ? racine.modele : null
            interactive: false
            keyNavigationEnabled: false
            clip: true
            focus: visible
            cacheBuffer: 600
            ScrollBar.vertical: BarreDefilement {}
            delegate: DelegueListe {
                vue: racine
                width: liste.width
                height: 34
            }
        }

        // rectangle de sélection
        Rectangle {
            visible: fond.bande && (Math.abs(fin.x - debut.x) > 3 || Math.abs(fin.y - debut.y) > 3)
            readonly property point debut: racine.vueActive.contentItem.mapToItem(fond, fond.origine.x, fond.origine.y)
            readonly property point fin: fond.courant
            x: Math.min(debut.x, fin.x)
            y: Math.min(debut.y, fin.y)
            width: Math.abs(fin.x - debut.x)
            height: Math.abs(fin.y - debut.y)
            color: Qt.alpha(theme.accent, 0.14)
            border.color: theme.accent
            border.width: 1
            radius: 3
        }

        // dossier vide, aucun résultat…
        Column {
            anchors.centerIn: parent
            spacing: 10
            visible: racine.modele && racine.modele.count === 0 && !(racine.onglet && racine.onglet.rechercheEnCours)
            Glyphe {
                anchors.horizontalCenter: parent.horizontalCenter
                nom: racine.mode === "recherche" ? "recherche" : racine.mode === "corbeille" ? "supprimer"
                   : racine.mode === "etiquette" ? "etiquette" : "dossier"
                taille: 44
                couleur: Qt.alpha(theme.texteDoux, 0.5)
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: racine.mode === "recherche" ? "Aucun résultat"
                    : racine.mode === "corbeille" ? "La corbeille est vide"
                    : racine.mode === "etiquette" ? "Aucun élément ne porte cette étiquette"
                    : "Ce dossier est vide"
                font.pixelSize: 15
                color: theme.texteDoux
            }
        }
    }
}
