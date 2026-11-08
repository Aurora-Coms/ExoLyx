import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Fenêtre principale de Fichiers (sans cadre système)
Window {
    id: fenetre
    width: 1200
    height: 760
    minimumWidth: 760
    minimumHeight: 480
    visible: true
    title: controleur.onglet ? controleur.onglet.titre + " — Fichiers" : "Fichiers"
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "transparent"

    readonly property bool agrandie: visibility === Window.Maximized || visibility === Window.FullScreen
    readonly property var onglet: controleur.onglet
    readonly property var modele: onglet ? onglet.modeleFichiers : null
    readonly property string mode: onglet ? onglet.mode : "accueil"
    readonly property bool vueFichiersActive: mode === "dossier" || mode === "recherche" || mode === "etiquette" || mode === "corbeille"
    readonly property bool saisieActive: activeFocusItem !== null && activeFocusItem.cursorPosition !== undefined
    readonly property bool dialogueOuvert: saisie.visible || confirmation.visible || conflit.visible || proprietes.visible
    readonly property bool raccourcisVue: !saisieActive && !dialogueOuvert
    readonly property int rayon: agrandie ? 0 : 14

    // --- actions partagées ---
    function basculerAgrandie() { agrandie ? showNormal() : showMaximized() }
    function focaliserVue() { if (vueFichiersActive) vueFichiers.focaliser() }

    function demanderCreation(genre) {
        if (!onglet || onglet.dossierCourant === "") return
        saisie.ouvrir(genre === "dossier" ? "Nouveau dossier" : "Nouveau fichier",
                      controleur.nomParDefaut(genre), "Créer",
                      (nom) => controleur.creer(genre, nom), genre !== "dossier")
    }
    function demanderRenommage() {
        const e = modele ? modele.premiereSelectionnee() : null
        if (!e) return
        saisie.ouvrir("Renommer « " + e.nom + " »", e.nom, "Renommer",
                      (nom) => controleur.renommer(e.chemin, nom), !e.dossier)
    }
    function demanderEtiquette() {
        saisie.ouvrir("Nouvelle étiquette", "", "Ajouter",
                      (nom) => controleur.etiquetterSelection(nom.trim(), true), false)
    }
    function ouvrirProprietes() { proprietes.ouvrir() }
    function confirmerSuppression() {
        if (!modele || modele.nbSelection === 0) return
        const n = modele.nbSelection
        const e = modele.premiereSelectionnee()
        confirmation.demander("Supprimer définitivement ?",
            (n === 1 ? "« " + e.nom + " » sera supprimé" : n + " éléments seront supprimés")
            + " sans passer par la corbeille. Cette action est irréversible.",
            "Supprimer", () => controleur.supprimerDefinitivement())
    }
    function confirmerVidage() {
        confirmation.demander("Vider la corbeille ?",
            "Tous les éléments de la corbeille seront supprimés définitivement.",
            "Vider la corbeille", () => controleur.viderCorbeille())
    }
    function supprimerSelon(definitif) {
        if (!vueFichiersActive || !modele || modele.nbSelection === 0) return
        if (definitif || mode === "corbeille") confirmerSuppression()
        else controleur.mettreALaCorbeille()
    }

    // menus contextuels
    function menuElement(item, x, y) { menuSelection.popup(item, x, y) }
    function menuFond(item, x, y) { menuDossierCourant.popup(item, x, y) }
    property string cheminMenu: ""
    property bool cheminMenuEpingle: false
    function menuDossier(chemin, epingle, item, x, y) {
        cheminMenu = chemin
        cheminMenuEpingle = epingle
        menuRaccourci.popup(item, x, y)
    }
    property string etiquetteMenu: ""
    function menuEtiquette(nom, item, x, y) { etiquetteMenu = nom; menuEtiq.popup(item, x, y) }
    function menuCorbeille(item, x, y) { menuCorb.popup(item, x, y) }
    function menuRecent(chemin, item, x, y) { cheminMenu = chemin; menuRec.popup(item, x, y) }

    function montrerMessage(texte) {
        toast.texte = texte
        toast.visible = true
        minuteurToast.restart()
    }

    Connections {
        target: controleur
        function onMessage(texte) { fenetre.montrerMessage(texte) }
        function onRenommerDemande() { fenetre.demanderRenommage() }
        function onCourantChange() { Qt.callLater(fenetre.focaliserVue) }
    }
    Connections {
        target: operations
        function onConflitDemande(ident, source, destination) { conflit.ajouter(ident, source, destination) }
    }
    Connections {
        target: fenetre.onglet
        function onChange() { Qt.callLater(fenetre.focaliserVue) }
    }

    // --- raccourcis clavier ---
    Shortcut { sequences: [StandardKey.Copy]; enabled: fenetre.raccourcisVue && fenetre.vueFichiersActive; onActivated: controleur.copier() }
    Shortcut { sequences: [StandardKey.Cut]; enabled: fenetre.raccourcisVue && fenetre.vueFichiersActive; onActivated: controleur.couper() }
    Shortcut { sequences: [StandardKey.Paste]; enabled: fenetre.raccourcisVue; onActivated: controleur.coller() }
    Shortcut { sequence: "F2"; enabled: fenetre.raccourcisVue; onActivated: controleur.demanderRenommage() }
    Shortcut { sequence: "Delete"; enabled: fenetre.raccourcisVue; onActivated: fenetre.supprimerSelon(false) }
    Shortcut { sequence: "Shift+Delete"; enabled: fenetre.raccourcisVue; onActivated: fenetre.supprimerSelon(true) }
    Shortcut { sequence: "Ctrl+T"; enabled: !fenetre.dialogueOuvert; onActivated: controleur.nouvelOnglet() }
    Shortcut { sequence: "Ctrl+W"; enabled: !fenetre.dialogueOuvert; onActivated: controleur.fermerOnglet(controleur.courant) }
    Shortcut { sequence: "Ctrl+Tab"; onActivated: controleur.activerOnglet((controleur.courant + 1) % controleur.onglets.length) }
    Shortcut { sequence: "Ctrl+Shift+Tab"; onActivated: controleur.activerOnglet((controleur.courant + controleur.onglets.length - 1) % controleur.onglets.length) }
    Shortcut { sequences: ["Ctrl+L", "Alt+D"]; enabled: !fenetre.dialogueOuvert; onActivated: barreAdresse.editerChemin() }
    Shortcut { sequence: "Ctrl+F"; enabled: !fenetre.dialogueOuvert; onActivated: barreAdresse.focaliserRecherche() }
    Shortcut { sequence: "Alt+Left"; enabled: !fenetre.dialogueOuvert; onActivated: fenetre.onglet.reculer() }
    Shortcut { sequence: "Alt+Right"; enabled: !fenetre.dialogueOuvert; onActivated: fenetre.onglet.avancer() }
    Shortcut { sequence: "Alt+Up"; enabled: !fenetre.dialogueOuvert; onActivated: fenetre.onglet.monter() }
    Shortcut { sequence: "Backspace"; enabled: fenetre.raccourcisVue; onActivated: fenetre.onglet.monter() }
    Shortcut { sequence: "Alt+Home"; enabled: !fenetre.dialogueOuvert; onActivated: controleur.naviguer(controleur.dossierPersonnel) }
    Shortcut { sequence: "Ctrl+H"; enabled: !fenetre.dialogueOuvert; onActivated: controleur.caches = !controleur.caches }
    Shortcut { sequences: [StandardKey.SelectAll]; enabled: fenetre.raccourcisVue && fenetre.vueFichiersActive; onActivated: fenetre.modele.toutSelectionner() }
    Shortcut { sequences: ["F5", "Ctrl+R"]; enabled: !fenetre.dialogueOuvert; onActivated: controleur.rafraichir() }
    Shortcut { sequences: ["Return", "Enter"]; enabled: fenetre.raccourcisVue && fenetre.vueFichiersActive; onActivated: controleur.ouvrirSelection() }
    Shortcut { sequence: "Space"; enabled: fenetre.raccourcisVue; onActivated: controleur.apercuVisible = !controleur.apercuVisible }
    Shortcut { sequence: "Ctrl+Shift+N"; enabled: !fenetre.dialogueOuvert; onActivated: fenetre.demanderCreation("dossier") }
    Shortcut { sequences: ["Alt+Return", "Alt+Enter", "Ctrl+I"]; enabled: !fenetre.dialogueOuvert; onActivated: fenetre.ouvrirProprietes() }
    Shortcut { sequence: "Ctrl+1"; onActivated: controleur.vue = "grille" }
    Shortcut { sequence: "Ctrl+2"; onActivated: controleur.vue = "liste" }
    Shortcut { sequences: [StandardKey.ZoomIn]; onActivated: controleur.tailleIcones = controleur.tailleIcones + 16 }
    Shortcut { sequences: [StandardKey.ZoomOut]; onActivated: controleur.tailleIcones = controleur.tailleIcones - 16 }

    // --- cadre de la fenêtre ---
    Rectangle {
        id: cadre
        anchors.fill: parent
        radius: fenetre.rayon
        color: theme.fond
        border.color: fenetre.agrandie ? "transparent" : theme.bordure
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 1
            spacing: 0

            BarreTitre {
                fenetre: fenetre
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: outils.implicitHeight
                color: theme.surfaceHaute
                Column {
                    id: outils
                    width: parent.width
                    BarreAdresse { id: barreAdresse; width: parent.width }
                    Rectangle { width: parent.width - 20; x: 10; height: 1; color: theme.bordure; opacity: 0.7 }
                    BarreCommandes { width: parent.width }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: theme.bordure }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                BarreLaterale {
                    Layout.preferredWidth: 236
                    Layout.fillHeight: true
                }

                Rectangle {
                    id: carteContenu
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.topMargin: 8
                    Layout.bottomMargin: 8
                    Layout.rightMargin: 8
                    radius: 10
                    color: theme.surface
                    border.color: theme.bordure

                    Item {
                        id: zoneContenu
                        anchors.fill: parent
                        anchors.margins: 1
                        anchors.bottomMargin: barreEtat.height + 1

                        PageAccueil {
                            anchors.fill: parent
                            visible: fenetre.mode === "accueil"
                        }
                        PageParametres {
                            anchors.fill: parent
                            visible: fenetre.mode === "parametres"
                        }
                        VueFichiers {
                            id: vueFichiers
                            anchors.fill: parent
                            visible: fenetre.vueFichiersActive
                            focus: visible
                        }
                    }

                    Item {
                        id: barreEtat
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 1
                        height: fenetre.vueFichiersActive ? 30 : 0
                        visible: fenetre.vueFichiersActive
                        Rectangle { width: parent.width - 16; x: 8; height: 1; color: theme.bordure }
                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 14
                            anchors.verticalCenter: parent.verticalCenter
                            text: fenetre.modele ? fenetre.modele.resumeSelection : ""
                            font.pixelSize: 12
                            color: theme.texteDoux
                        }
                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: 14
                            anchors.verticalCenter: parent.verticalCenter
                            text: fenetre.onglet && fenetre.onglet.rechercheEnCours ? "Recherche en cours…"
                                : indexEtiquettes.enCours ? "Indexation des étiquettes…"
                                : controleur.caches ? "Fichiers cachés affichés" : ""
                            font.pixelSize: 12
                            color: theme.texteDoux
                        }
                    }

                    PanneauOperations {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 14
                        anchors.bottomMargin: barreEtat.height + 12
                    }
                }

                PanneauApercu {
                    visible: controleur.apercuVisible
                    Layout.preferredWidth: 300
                    Layout.fillHeight: true
                    Layout.topMargin: 8
                    Layout.bottomMargin: 8
                    Layout.rightMargin: 8
                }
            }
        }

        // --- message éphémère ---
        Rectangle {
            id: toast
            property string texte: ""
            visible: false
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 54
            width: Math.min(texteToast.implicitWidth + 36, parent.width - 80)
            height: 40
            radius: 10
            color: theme.texte
            Text {
                id: texteToast
                anchors.centerIn: parent
                width: Math.min(implicitWidth, parent.width - 36)
                text: toast.texte
                elide: Text.ElideMiddle
                font.pixelSize: 13
                color: theme.fond
            }
            Timer { id: minuteurToast; interval: 3400; onTriggered: toast.visible = false }
            MouseArea { anchors.fill: parent; onClicked: toast.visible = false }
        }
    }

    // --- poignées de redimensionnement ---
    component Poignee: MouseArea {
        property int bords: 0
        enabled: !fenetre.agrandie
        onPressed: fenetre.startSystemResize(bords)
    }
    Poignee { bords: Qt.LeftEdge; cursorShape: Qt.SizeHorCursor; x: 0; y: 14; width: 5; height: parent.height - 28 }
    Poignee { bords: Qt.RightEdge; cursorShape: Qt.SizeHorCursor; x: parent.width - 5; y: 14; width: 5; height: parent.height - 28 }
    Poignee { bords: Qt.TopEdge; cursorShape: Qt.SizeVerCursor; x: 14; y: 0; width: parent.width - 28; height: 4 }
    Poignee { bords: Qt.BottomEdge; cursorShape: Qt.SizeVerCursor; x: 14; y: parent.height - 5; width: parent.width - 28; height: 5 }
    Poignee { bords: Qt.TopEdge | Qt.LeftEdge; cursorShape: Qt.SizeFDiagCursor; x: 0; y: 0; width: 14; height: 14 }
    Poignee { bords: Qt.TopEdge | Qt.RightEdge; cursorShape: Qt.SizeBDiagCursor; x: parent.width - 14; y: 0; width: 14; height: 14 }
    Poignee { bords: Qt.BottomEdge | Qt.LeftEdge; cursorShape: Qt.SizeBDiagCursor; x: 0; y: parent.height - 14; width: 14; height: 14 }
    Poignee { bords: Qt.BottomEdge | Qt.RightEdge; cursorShape: Qt.SizeFDiagCursor; x: parent.width - 14; y: parent.height - 14; width: 14; height: 14 }

    // --- dialogues ---
    DialogueSaisie { id: saisie }
    DialogueConfirmation { id: confirmation }
    DialogueConflit { id: conflit }
    DialogueProprietes { id: proprietes }

    // --- menus contextuels ---
    readonly property var entreeUnique: modele && modele.nbSelection === 1 ? modele.premiereSelectionnee() : null
    readonly property bool dossierUnique: entreeUnique !== null && entreeUnique.dossier === true

    MenuTheme {
        id: menuSelection
        property var etiquettesPosees: []
        onAboutToShow: etiquettesPosees = controleur.etiquettesCommunes()
        readonly property bool corbeille: fenetre.mode === "corbeille"

        ElementMenu { text: "Ouvrir"; icone: "ouvrir"; raccourci: "Entrée"; visible: !menuSelection.corbeille; onTriggered: controleur.ouvrirSelection() }
        ElementMenu { text: "Ouvrir dans un nouvel onglet"; icone: "plus"; visible: fenetre.dossierUnique && !menuSelection.corbeille; onTriggered: controleur.nouvelOnglet(fenetre.entreeUnique.chemin) }
        ElementMenu {
            text: "Ouvrir l’emplacement"; icone: "dossier"
            visible: fenetre.entreeUnique !== null && (fenetre.mode === "recherche" || fenetre.mode === "etiquette")
            onTriggered: controleur.ouvrirDossierParent(fenetre.entreeUnique.chemin)
        }
        ElementMenu { text: "Restaurer"; icone: "annuler"; visible: menuSelection.corbeille; onTriggered: controleur.restaurer() }
        ElementMenu { text: "Aperçu"; icone: "apercu"; raccourci: "Espace"; visible: !menuSelection.corbeille; onTriggered: controleur.apercuVisible = true }
        SeparateurMenu { visible: !menuSelection.corbeille }
        ElementMenu { text: "Couper"; icone: "couper"; raccourci: "Ctrl+X"; visible: !menuSelection.corbeille; onTriggered: controleur.couper() }
        ElementMenu { text: "Copier"; icone: "copier"; raccourci: "Ctrl+C"; visible: !menuSelection.corbeille; onTriggered: controleur.copier() }
        ElementMenu {
            text: "Coller dans ce dossier"; icone: "coller"
            visible: fenetre.dossierUnique && controleur.peutColler && !menuSelection.corbeille
            onTriggered: controleur.coller(fenetre.entreeUnique.chemin)
        }
        ElementMenu { text: "Renommer"; icone: "renommer"; raccourci: "F2"; visible: fenetre.entreeUnique !== null && !menuSelection.corbeille; onTriggered: fenetre.demanderRenommage() }
        ElementMenu { text: "Mettre à la corbeille"; icone: "supprimer"; raccourci: "Suppr"; visible: !menuSelection.corbeille; onTriggered: controleur.mettreALaCorbeille() }
        SeparateurMenu { visible: !menuSelection.corbeille }
        MenuTheme {
            id: sousMenuEtiquettes
            title: "Étiquettes"
            Instantiator {
                model: controleur.etiquettes
                delegate: ElementMenu {
                    required property var modelData
                    text: modelData.nom
                    pastille: (theme.clair, theme.jeton(modelData.couleur))
                    checkable: true
                    checked: menuSelection.etiquettesPosees.indexOf(modelData.nom) >= 0
                    onTriggered: controleur.etiquetterSelection(modelData.nom, menuSelection.etiquettesPosees.indexOf(modelData.nom) < 0)
                }
                onObjectAdded: (i, o) => sousMenuEtiquettes.insertItem(i, o)
                onObjectRemoved: (i, o) => sousMenuEtiquettes.removeItem(o)
            }
            SeparateurMenu { visible: controleur.etiquettes.length > 0 }
            ElementMenu { text: "Nouvelle étiquette…"; icone: "plus"; onTriggered: fenetre.demanderEtiquette() }
        }
        ElementMenu {
            text: fenetre.dossierUnique && controleur.estEpingle(fenetre.entreeUnique.chemin) ? "Désépingler" : "Épingler"
            icone: "epingle"
            visible: fenetre.dossierUnique && !menuSelection.corbeille
            onTriggered: controleur.estEpingle(fenetre.entreeUnique.chemin) ? controleur.desepingler(fenetre.entreeUnique.chemin)
                                                                            : controleur.epingler(fenetre.entreeUnique.chemin)
        }
        ElementMenu { text: "Ouvrir un terminal ici"; icone: "terminal"; visible: fenetre.dossierUnique && !menuSelection.corbeille; onTriggered: controleur.ouvrirTerminal(fenetre.entreeUnique.chemin) }
        SeparateurMenu {}
        ElementMenu { text: "Supprimer définitivement"; icone: "croixCercle"; raccourci: menuSelection.corbeille ? "Suppr" : "Maj+Suppr"; danger: true; onTriggered: fenetre.confirmerSuppression() }
        ElementMenu { text: "Propriétés"; icone: "proprietes"; raccourci: "Alt+Entrée"; onTriggered: fenetre.ouvrirProprietes() }
    }

    MenuTheme {
        id: menuDossierCourant
        readonly property bool corbeille: fenetre.mode === "corbeille"
        readonly property bool dossier: fenetre.mode === "dossier"
        ElementMenu { text: "Nouveau dossier"; icone: "dossierPlus"; raccourci: "Ctrl+Maj+N"; visible: menuDossierCourant.dossier; onTriggered: fenetre.demanderCreation("dossier") }
        ElementMenu { text: "Nouveau fichier texte"; icone: "fichierPlus"; visible: menuDossierCourant.dossier; onTriggered: fenetre.demanderCreation("fichier") }
        ElementMenu { text: "Coller"; icone: "coller"; raccourci: "Ctrl+V"; visible: menuDossierCourant.dossier; enabled: controleur.peutColler; onTriggered: controleur.coller() }
        SeparateurMenu { visible: menuDossierCourant.dossier }
        ElementMenu { text: "Tout sélectionner"; icone: "coche"; raccourci: "Ctrl+A"; onTriggered: fenetre.modele.toutSelectionner() }
        ElementMenu { text: "Afficher les fichiers cachés"; checkable: true; checked: controleur.caches; raccourci: "Ctrl+H"; onTriggered: controleur.caches = !controleur.caches }
        ElementMenu { text: "Actualiser"; icone: "rafraichir"; raccourci: "F5"; onTriggered: controleur.rafraichir() }
        SeparateurMenu { visible: menuDossierCourant.dossier }
        ElementMenu {
            text: fenetre.onglet && controleur.estEpingle(fenetre.onglet.chemin) ? "Désépingler ce dossier" : "Épingler ce dossier"
            icone: "epingle"; visible: menuDossierCourant.dossier
            onTriggered: controleur.estEpingle(fenetre.onglet.chemin) ? controleur.desepingler(fenetre.onglet.chemin) : controleur.epingler(fenetre.onglet.chemin)
        }
        ElementMenu { text: "Ouvrir un terminal ici"; icone: "terminal"; visible: menuDossierCourant.dossier; onTriggered: controleur.ouvrirTerminal() }
        ElementMenu { text: "Propriétés du dossier"; icone: "proprietes"; visible: menuDossierCourant.dossier; onTriggered: fenetre.ouvrirProprietes() }
        ElementMenu { text: "Vider la corbeille"; icone: "supprimer"; danger: true; visible: menuDossierCourant.corbeille; enabled: !controleur.corbeilleVide; onTriggered: fenetre.confirmerVidage() }
    }

    MenuTheme {
        id: menuRaccourci
        ElementMenu { text: "Ouvrir"; icone: "ouvrir"; onTriggered: controleur.naviguer(fenetre.cheminMenu) }
        ElementMenu { text: "Ouvrir dans un nouvel onglet"; icone: "plus"; onTriggered: controleur.nouvelOnglet(fenetre.cheminMenu) }
        ElementMenu { text: "Ouvrir un terminal ici"; icone: "terminal"; onTriggered: controleur.ouvrirTerminal(fenetre.cheminMenu) }
        SeparateurMenu {}
        ElementMenu {
            text: fenetre.cheminMenuEpingle ? "Désépingler" : "Épingler"
            icone: "epingle"
            onTriggered: fenetre.cheminMenuEpingle ? controleur.desepingler(fenetre.cheminMenu) : controleur.epingler(fenetre.cheminMenu)
        }
    }

    MenuTheme {
        id: menuEtiq
        ElementMenu { text: "Afficher les éléments"; icone: "etiquette"; onTriggered: controleur.naviguer("etiquette:" + fenetre.etiquetteMenu) }
        ElementMenu { text: "Ouvrir dans un nouvel onglet"; icone: "plus"; onTriggered: controleur.nouvelOnglet("etiquette:" + fenetre.etiquetteMenu) }
        SeparateurMenu {}
        ElementMenu { text: "Retirer de tous les fichiers"; icone: "supprimer"; danger: true; onTriggered: controleur.oublierEtiquette(fenetre.etiquetteMenu) }
    }

    MenuTheme {
        id: menuCorb
        ElementMenu { text: "Ouvrir"; icone: "ouvrir"; onTriggered: controleur.naviguer("corbeille:") }
        ElementMenu { text: "Vider la corbeille"; icone: "supprimer"; danger: true; enabled: !controleur.corbeilleVide; onTriggered: fenetre.confirmerVidage() }
    }

    MenuTheme {
        id: menuRec
        ElementMenu { text: "Ouvrir"; icone: "ouvrir"; onTriggered: controleur.ouvrirChemin(fenetre.cheminMenu) }
        ElementMenu { text: "Ouvrir l’emplacement"; icone: "dossier"; onTriggered: controleur.ouvrirDossierParent(fenetre.cheminMenu) }
    }
}
