// SPDX-License-Identifier: GPL-3.0-or-later
// En-tête de page : titre + sous-titre.
import QtQuick

Column {
    property string titre
    property string sousTitre
    readonly property var p: ctrl.palette
    spacing: 6
    Text {
        text: parent.titre
        color: parent.p.texte
        font.family: "Inter"; font.pixelSize: 28; font.weight: Font.Bold
    }
    Text {
        width: parent.width
        visible: text.length > 0
        text: parent.sousTitre
        color: parent.p.texteDoux
        wrapMode: Text.WordWrap
        font.family: "Inter"; font.pixelSize: 15
    }
}
