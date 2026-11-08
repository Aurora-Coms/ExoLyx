// Thème SDDM « exolyx » — SDDM ≥ 0.21, Qt 6, sans dépendance à Plasma.
//
// États : repos (horloge + bienvenue) → actif (fond flouté, avatar dans les
// orbites, champ mot de passe) → connexion (les orbites accélèrent).
// Objets fournis par SDDM : sddm, userModel, sessionModel, config, keyboard.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import "composants"

Rectangle {
    id: racine
    width: 1920
    height: 1080
    color: "#0D1310"

    // ---------- échelle : référence 1920×1080 ----------
    readonly property real s: Math.max(0.75, Math.min(width / 1920, height / 1080))
    readonly property string police: (config && config.police) ? config.police : "Inter"
    readonly property color accent: "#A8D479"

    // ---------- état ----------
    property bool actif: false
    property bool connexion: false
    property bool erreur: false
    property string messageErreur: ""
    property int indexUtilisateur: (userModel && userModel.lastIndex >= 0) ? userModel.lastIndex : 0
    property int indexSession: (sessionModel && sessionModel.lastIndex >= 0) ? sessionModel.lastIndex : 0
    property date maintenant: new Date()

    readonly property var utilisateur: listeUtilisateurs.count > 0 && indexUtilisateur < listeUtilisateurs.count
                                       ? listeUtilisateurs.itemAt(indexUtilisateur) : null
    readonly property string nomUtilisateur: utilisateur ? utilisateur.nom : ""
    readonly property string nomAffiche: utilisateur ? (utilisateur.nomReel !== "" ? utilisateur.nomReel : utilisateur.nom) : ""
    readonly property bool plusieursUtilisateurs: listeUtilisateurs.count > 1
    readonly property bool majuscules: keyboard ? keyboard.capsLock : false

    function urlFichier(chemin) {
        if (!chemin || chemin === "") return ""
        var c = String(chemin)
        return c.indexOf("/") === 0 ? "file://" + c : c
    }
    function capitaliser(t) { return t.length ? t.charAt(0).toUpperCase() + t.slice(1) : t }

    function activer(texte) {
        actif = true
        champ.prendreFocus()
        if (texte && texte.length === 1 && texte.charCodeAt(0) >= 32) champ.saisir(texte)
        inactivite.restart()
    }
    function reposer() {
        if (connexion) return
        actif = false
        erreur = false
        champ.vider()
        racine.forceActiveFocus()
    }
    function connecter() {
        if (connexion || nomUtilisateur === "") return
        erreur = false
        connexion = true
        sddm.login(nomUtilisateur, champ.text, indexSession)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            racine.connexion = false
            racine.erreur = true
            racine.messageErreur = "Mot de passe incorrect. Réessayez."
            champ.vider()
            champ.secouer()
            champ.prendreFocus()
        }
        function onLoginSucceeded() {
            racine.erreur = false
        }
        function onInformationMessage(message) {
            racine.messageErreur = message
        }
    }

    // collecte des données des modèles (nom, avatar…)
    Item {
        visible: false
        Repeater {
            id: listeUtilisateurs
            model: userModel
            delegate: Item {
                required property var model
                readonly property string nom: model.name || ""
                readonly property string nomReel: model.realName || ""
                readonly property string icone: model.icon || ""
            }
        }
        Repeater {
            id: listeSessions
            model: sessionModel
            delegate: Item {
                required property var model
                readonly property string nom: model.name || ""
            }
        }
    }

    Timer {
        interval: 1000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: racine.maintenant = new Date()
    }
    Timer {
        id: inactivite
        interval: 60000
        onTriggered: if (champ.text === "" && !menuSessions.opened) racine.reposer()
    }

    // ================= FOND =================
    Image {
        id: fond
        anchors.fill: parent
        source: (config && config.background) ? config.background : "images/fond.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        smooth: true
        visible: false
    }
    MultiEffect {
        id: fondEffet
        anchors.fill: parent
        source: fond
        autoPaddingEnabled: false
        blurEnabled: true
        blurMax: 64
        blur: racine.actif ? 1.0 : 0.0
        saturation: racine.actif ? -0.15 : 0.0
        Behavior on blur { NumberAnimation { duration: 450; easing.type: Easing.OutCubic } }
        Behavior on saturation { NumberAnimation { duration: 450 } }
    }
    // voile sombre (lisibilité) : léger au repos, plus dense une fois actif
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(0.05, 0.07, 0.06, racine.actif ? 0.62 : 0.55) }
            GradientStop { position: 0.55; color: Qt.rgba(0.05, 0.07, 0.06, racine.actif ? 0.55 : 0.0) }
            GradientStop { position: 1.0; color: Qt.rgba(0.05, 0.07, 0.06, racine.actif ? 0.62 : 0.0) }
        }
    }

    // activation à la souris
    MouseArea {
        anchors.fill: parent
        onClicked: racine.actif ? champ.prendreFocus() : racine.activer("")
        onPositionChanged: if (racine.actif) inactivite.restart()
        hoverEnabled: racine.actif
    }

    // ================= REPOS =================
    Item {
        id: repos
        anchors.fill: parent
        opacity: racine.actif ? 0 : 1
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 350 } }

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 130 * racine.s
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: -20 * racine.s
            spacing: 6 * racine.s

            Text {
                text: Qt.formatTime(racine.maintenant, "HH:mm")
                color: "#E6EFE1"
                font.family: racine.police
                font.weight: Font.Light
                font.pixelSize: 168 * racine.s
                font.letterSpacing: -4 * racine.s
            }
            Text {
                text: racine.capitaliser(racine.maintenant.toLocaleDateString(Qt.locale("fr_FR"), "dddd d MMMM yyyy"))
                color: "#E6EFE1"
                opacity: 0.92
                font.family: racine.police
                font.pixelSize: 34 * racine.s
            }
            Item { width: 1; height: 22 * racine.s }
            Rectangle { width: 64 * racine.s; height: 4 * racine.s; radius: height / 2; color: racine.accent }
            Item { width: 1; height: 8 * racine.s }
            Text {
                text: (config && config.message) ? config.message : "Bienvenue sur ExoLyx"
                color: racine.accent
                font.family: racine.police
                font.weight: Font.Medium
                font.pixelSize: 26 * racine.s
            }
            Text {
                visible: sddm && sddm.hostName !== undefined && sddm.hostName !== ""
                text: sddm ? sddm.hostName : ""
                color: "#97A893"
                font.family: racine.police
                font.pixelSize: 18 * racine.s
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 54 * racine.s
            text: "Appuyez sur une touche ou cliquez pour vous connecter"
            color: "#E6EFE1"
            font.family: racine.police
            font.pixelSize: 17 * racine.s
            SequentialAnimation on opacity {
                running: repos.visible
                loops: Animation.Infinite
                NumberAnimation { from: 0.35; to: 0.85; duration: 1600; easing.type: Easing.InOutSine }
                NumberAnimation { from: 0.85; to: 0.35; duration: 1600; easing.type: Easing.InOutSine }
            }
        }
    }

    // ================= ACTIF =================
    Item {
        id: connexionVue
        anchors.fill: parent
        opacity: racine.actif ? 1 : 0
        visible: opacity > 0
        enabled: racine.actif
        Behavior on opacity { NumberAnimation { duration: 380 } }

        // logo + heure en haut
        Row {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: 32 * racine.s
            spacing: 12 * racine.s
            Image {
                source: "images/logo.png"
                width: 40 * racine.s; height: width
                smooth: true; mipmap: true
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: "ExoLyx"
                color: "#E6EFE1"
                font.family: racine.police
                font.weight: Font.DemiBold
                font.pixelSize: 21 * racine.s
                anchors.verticalCenter: parent.verticalCenter
            }
        }
        Column {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 32 * racine.s
            Text {
                anchors.right: parent.right
                text: Qt.formatTime(racine.maintenant, "HH:mm")
                color: "#E6EFE1"
                font.family: racine.police
                font.weight: Font.Medium
                font.pixelSize: 26 * racine.s
            }
            Text {
                anchors.right: parent.right
                text: racine.capitaliser(racine.maintenant.toLocaleDateString(Qt.locale("fr_FR"), "dddd d MMMM"))
                color: "#97A893"
                font.family: racine.police
                font.pixelSize: 15 * racine.s
            }
        }

        // ---- bloc central ----
        Column {
            id: centre
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: -30 * racine.s
            spacing: 0

            Orbites {
                id: orbites
                anchors.horizontalCenter: parent.horizontalCenter
                diametre: 200 * racine.s
                avatar: racine.utilisateur ? racine.urlFichier(racine.utilisateur.icone) : ""
                initiale: racine.nomAffiche !== "" ? racine.nomAffiche.charAt(0).toUpperCase() : "?"
                vitesse: racine.connexion ? 9.0 : 1.0
                enMarche: racine.actif
                scale: racine.connexion ? 1.06 : 1.0
                Behavior on scale { NumberAnimation { duration: 900; easing.type: Easing.OutCubic } }
            }
            Item { width: 1; height: 18 * racine.s }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: racine.nomAffiche
                color: "#E6EFE1"
                font.family: racine.police
                font.weight: Font.DemiBold
                font.pixelSize: 30 * racine.s
            }
            Item { width: 1; height: 22 * racine.s }
            ChampMotDePasse {
                id: champ
                anchors.horizontalCenter: parent.horizontalCenter
                s: racine.s
                occupe: racine.connexion
                enErreur: racine.erreur
                onValide: racine.connecter()
                Keys.onEscapePressed: racine.reposer()
                onTextChanged: { inactivite.restart(); if (text !== "") racine.erreur = false }
            }
            // ligne d'état : erreur / verr. maj. (hauteur fixe : pas de saut de mise en page)
            Item {
                width: 420 * racine.s
                height: 44 * racine.s
                anchors.horizontalCenter: parent.horizontalCenter
                Row {
                    anchors.centerIn: parent
                    spacing: 18 * racine.s
                    Text {
                        visible: racine.erreur
                        text: racine.messageErreur
                        color: "#E5766B"
                        font.family: racine.police
                        font.pixelSize: 16 * racine.s
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Row {
                        visible: racine.majuscules
                        spacing: 6 * racine.s
                        anchors.verticalCenter: parent.verticalCenter
                        Image {
                            source: "images/icones/majuscules-attention.png"
                            width: 18 * racine.s; height: width
                            smooth: true; mipmap: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: "Verr. Maj. activé"
                            color: "#E8C26A"
                            font.family: racine.police
                            font.pixelSize: 15 * racine.s
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            // ---- choix de l'utilisateur ----
            ListView {
                id: choixUtilisateur
                visible: racine.plusieursUtilisateurs
                anchors.horizontalCenter: parent.horizontalCenter
                orientation: ListView.Horizontal
                spacing: 10 * racine.s
                height: 46 * racine.s
                width: Math.min(contentWidth, racine.width * 0.6)
                clip: true
                interactive: contentWidth > width
                model: userModel
                delegate: Rectangle {
                    id: puce
                    required property int index
                    required property var model
                    readonly property bool courant: index === racine.indexUtilisateur
                    readonly property string libelle: (model.realName && model.realName !== "") ? model.realName : model.name
                    height: choixUtilisateur.height
                    width: rangee.implicitWidth + 26 * racine.s
                    radius: height / 2
                    color: courant ? Qt.rgba(0.66, 0.83, 0.47, 0.16) : (zonePuce.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(0.08, 0.11, 0.09, 0.55))
                    border.width: 1
                    border.color: courant ? racine.accent : "#2A362E"
                    Row {
                        id: rangee
                        anchors.centerIn: parent
                        spacing: 9 * racine.s
                        Rectangle {
                            width: 30 * racine.s; height: width; radius: width / 2
                            color: puce.courant ? racine.accent : "#2A362E"
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.centerIn: parent
                                text: puce.libelle.charAt(0).toUpperCase()
                                color: puce.courant ? "#0D1310" : "#E6EFE1"
                                font.family: racine.police
                                font.weight: Font.DemiBold
                                font.pixelSize: 14 * racine.s
                            }
                        }
                        Text {
                            text: puce.libelle
                            color: puce.courant ? "#E6EFE1" : "#97A893"
                            font.family: racine.police
                            font.pixelSize: 15 * racine.s
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: zonePuce
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (racine.connexion) return
                            racine.indexUtilisateur = puce.index
                            racine.erreur = false
                            champ.vider()
                            champ.prendreFocus()
                        }
                    }
                }
            }
        }

        // ---- barre du bas : session + clavier à gauche, alimentation à droite ----
        Row {
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.margins: 32 * racine.s
            spacing: 12 * racine.s

            Rectangle {
                id: boutonSession
                height: 46 * racine.s
                width: rangeeSession.implicitWidth + 32 * racine.s
                radius: height / 2
                color: zoneSession.containsMouse ? Qt.rgba(0.66, 0.83, 0.47, 0.18) : Qt.rgba(0.11, 0.15, 0.13, 0.62)
                border.width: 1
                border.color: zoneSession.containsMouse || menuSessions.opened ? racine.accent : "#2A362E"
                Row {
                    id: rangeeSession
                    anchors.centerIn: parent
                    spacing: 10 * racine.s
                    Image {
                        source: "images/icones/session.png"
                        width: 20 * racine.s; height: width
                        smooth: true; mipmap: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: listeSessions.count > racine.indexSession && listeSessions.itemAt(racine.indexSession)
                              ? listeSessions.itemAt(racine.indexSession).nom : "Session"
                        color: "#E6EFE1"
                        font.family: racine.police
                        font.pixelSize: 15 * racine.s
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "▾"
                        color: "#97A893"
                        font.pixelSize: 13 * racine.s
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: zoneSession
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: menuSessions.opened ? menuSessions.close() : menuSessions.open()
                }

                Popup {
                    id: menuSessions
                    y: -height - 10 * racine.s
                    width: Math.max(260 * racine.s, boutonSession.width)
                    padding: 6 * racine.s
                    modal: false
                    focus: true
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                    onClosed: champ.prendreFocus()
                    background: Rectangle {
                        radius: 10 * racine.s
                        color: "#141C17"
                        border.color: "#2A362E"
                        border.width: 1
                    }
                    contentItem: ListView {
                        implicitHeight: contentHeight
                        clip: true
                        model: sessionModel
                        delegate: Rectangle {
                            id: ligne
                            required property int index
                            required property var model
                            width: ListView.view.width
                            height: 40 * racine.s
                            radius: 6 * racine.s
                            color: zoneLigne.containsMouse ? "#1C2620" : "transparent"
                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 12 * racine.s
                                anchors.verticalCenter: parent.verticalCenter
                                text: ligne.model.name
                                color: ligne.index === racine.indexSession ? racine.accent : "#E6EFE1"
                                font.family: racine.police
                                font.pixelSize: 15 * racine.s
                            }
                            Image {
                                visible: ligne.index === racine.indexSession
                                source: "images/icones/coche.png"
                                width: 16 * racine.s; height: width
                                anchors.right: parent.right
                                anchors.rightMargin: 12 * racine.s
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            MouseArea {
                                id: zoneLigne
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: { racine.indexSession = ligne.index; menuSessions.close() }
                            }
                        }
                    }
                }
            }

            // disposition du clavier (AZERTY = fr)
            Rectangle {
                height: 46 * racine.s
                width: rangeeClavier.implicitWidth + 28 * racine.s
                radius: height / 2
                color: Qt.rgba(0.11, 0.15, 0.13, 0.62)
                border.width: 1
                border.color: zoneClavier.containsMouse ? racine.accent : "#2A362E"
                Row {
                    id: rangeeClavier
                    anchors.centerIn: parent
                    spacing: 8 * racine.s
                    Image {
                        source: "images/icones/clavier.png"
                        width: 20 * racine.s; height: width
                        smooth: true; mipmap: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        id: texteClavier
                        text: {
                            try {
                                var l = keyboard.layouts[keyboard.currentLayout]
                                if (l && l.shortName) return l.shortName.toUpperCase()
                            } catch (e) {}
                            return "FR"
                        }
                        color: "#E6EFE1"
                        font.family: racine.police
                        font.weight: Font.Medium
                        font.pixelSize: 15 * racine.s
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    id: zoneClavier
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        try {
                            if (keyboard.layouts.length > 1)
                                keyboard.currentLayout = (keyboard.currentLayout + 1) % keyboard.layouts.length
                        } catch (e) {}
                        champ.prendreFocus()
                    }
                }
            }
        }

        Row {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 32 * racine.s
            spacing: 18 * racine.s
            BoutonAction {
                s: racine.s
                icone: Qt.resolvedUrl("images/icones/veille.png")
                libelle: "Veille"
                actif: sddm ? sddm.canSuspend : false
                onClique: sddm.suspend()
            }
            BoutonAction {
                s: racine.s
                icone: Qt.resolvedUrl("images/icones/redemarrer.png")
                libelle: "Redémarrer"
                actif: sddm ? sddm.canReboot : false
                onClique: sddm.reboot()
            }
            BoutonAction {
                s: racine.s
                icone: Qt.resolvedUrl("images/icones/eteindre.png")
                libelle: "Éteindre"
                actif: sddm ? sddm.canPowerOff : false
                onClique: sddm.powerOff()
            }
        }
    }

    // ================= CLAVIER =================
    focus: true
    Keys.onPressed: function(evenement) {
        if (!racine.actif) {
            racine.activer(evenement.text)
            evenement.accepted = true
        } else if (evenement.key === Qt.Key_Escape) {
            racine.reposer()
            evenement.accepted = true
        }
    }
    Component.onCompleted: racine.forceActiveFocus()
}
