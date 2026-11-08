import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Commandes sur la sélection et réglages d'affichage
Item {
    id: barre
    property var onglet: controleur.onglet
    readonly property var modele: onglet ? onglet.modeleFichiers : null
    readonly property int nb: modele ? modele.nbSelection : 0
    readonly property string mode: onglet ? onglet.mode : "accueil"
    readonly property bool vueFichiers: mode === "dossier" || mode === "recherche" || mode === "etiquette" || mode === "corbeille"
    readonly property bool dansDossier: mode === "dossier"
    readonly property bool corbeille: mode === "corbeille"
    implicitHeight: 44

    component Separateur: Rectangle {
        Layout.preferredWidth: 1
        Layout.preferredHeight: 20
        Layout.leftMargin: 4
        Layout.rightMargin: 4
        color: theme.bordure
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 2

        BoutonIcone {
            id: boutonNouveau
            icone: "plus"
            texte: "Nouveau"
            fleche: true
            visible: !barre.corbeille
            actif: barre.dansDossier
            color: actif ? (survol ? Qt.lighter(theme.accent, 1.06) : theme.accent) : theme.surfaceHaute
            couleurIcone: actif ? theme.surAccent : theme.texte
            couleurTexte: couleurIcone
            onClique: menuNouveau.popup(boutonNouveau, 0, boutonNouveau.height + 4)
            Layout.rightMargin: 6
            MenuTheme {
                id: menuNouveau
                ElementMenu { text: "Dossier"; icone: "dossierPlus"; raccourci: "Ctrl+Maj+N"; onTriggered: fenetre.demanderCreation("dossier") }
                ElementMenu { text: "Fichier texte"; icone: "fichierPlus"; onTriggered: fenetre.demanderCreation("fichier") }
            }
        }

        // --- presse-papiers et sélection ---
        BoutonIcone { icone: "couper"; visible: !barre.corbeille; actif: barre.nb > 0 && barre.vueFichiers; bulle: "Couper (Ctrl+X)"; onClique: controleur.couper() }
        BoutonIcone { icone: "copier"; visible: !barre.corbeille; actif: barre.nb > 0 && barre.vueFichiers; bulle: "Copier (Ctrl+C)"; onClique: controleur.copier() }
        BoutonIcone { icone: "coller"; visible: !barre.corbeille; actif: controleur.peutColler && barre.dansDossier; bulle: "Coller (Ctrl+V)"; onClique: controleur.coller() }
        BoutonIcone {
            icone: "renommer"; visible: !barre.corbeille
            actif: barre.nb === 1 && barre.vueFichiers
            bulle: "Renommer (F2)"; onClique: controleur.demanderRenommage()
        }
        BoutonIcone {
            icone: "supprimer"; visible: !barre.corbeille
            actif: barre.nb > 0 && barre.vueFichiers
            bulle: "Mettre à la corbeille (Suppr)"; onClique: controleur.mettreALaCorbeille()
        }
        Separateur { visible: !barre.corbeille }
        BoutonIcone {
            icone: "proprietes"; visible: !barre.corbeille
            actif: barre.nb > 0 || barre.dansDossier
            bulle: "Propriétés (Alt+Entrée)"; onClique: fenetre.ouvrirProprietes()
        }
        BoutonIcone {
            icone: "terminal"; texte: "Terminal"; visible: !barre.corbeille
            actif: barre.dansDossier
            bulle: "Ouvrir un terminal ici"; onClique: controleur.ouvrirTerminal()
        }

        // --- corbeille ---
        BoutonIcone {
            icone: "annuler"; texte: "Restaurer"; visible: barre.corbeille
            actif: barre.nb > 0; onClique: controleur.restaurer()
        }
        BoutonIcone {
            icone: "croixCercle"; texte: "Supprimer définitivement"; visible: barre.corbeille
            actif: barre.nb > 0; onClique: fenetre.confirmerSuppression()
        }
        BoutonIcone {
            icone: "supprimer"; texte: "Vider la corbeille"; visible: barre.corbeille
            actif: !controleur.corbeilleVide
            couleurIcone: theme.erreur
            onClique: fenetre.confirmerVidage()
        }

        Item { Layout.fillWidth: true }

        BoutonIcone {
            id: boutonTri
            icone: "tri"; texte: "Trier"; fleche: true
            actif: barre.vueFichiers
            onClique: menuTri.popup(boutonTri, 0, boutonTri.height + 4)
            MenuTheme {
                id: menuTri
                ElementMenu { text: "Nom"; checkable: true; checked: controleur.tri === "nom"; onTriggered: controleur.tri = "nom" }
                ElementMenu { text: "Date de modification"; checkable: true; checked: controleur.tri === "date"; onTriggered: controleur.tri = "date" }
                ElementMenu { text: "Type"; checkable: true; checked: controleur.tri === "type"; onTriggered: controleur.tri = "type" }
                ElementMenu { text: "Taille"; checkable: true; checked: controleur.tri === "taille"; onTriggered: controleur.tri = "taille" }
                SeparateurMenu {}
                ElementMenu { text: "Croissant"; checkable: true; checked: !controleur.triDecroissant; onTriggered: controleur.triDecroissant = false }
                ElementMenu { text: "Décroissant"; checkable: true; checked: controleur.triDecroissant; onTriggered: controleur.triDecroissant = true }
            }
        }
        Separateur {}
        BoutonIcone {
            icone: "grille"; coche: controleur.vue === "grille"; actif: barre.vueFichiers
            bulle: "Grille (Ctrl+1)"; onClique: controleur.vue = "grille"
        }
        BoutonIcone {
            icone: "liste"; coche: controleur.vue === "liste"; actif: barre.vueFichiers
            bulle: "Liste détaillée (Ctrl+2)"; onClique: controleur.vue = "liste"
        }
        Separateur {}
        BoutonIcone {
            icone: "apercu"; coche: controleur.apercuVisible
            bulle: "Panneau d’aperçu (Espace)"; onClique: controleur.apercuVisible = !controleur.apercuVisible
        }
    }
}
