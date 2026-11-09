#!/usr/bin/env python3
"""Génère les schémas de couleurs KDE ExoLyx (sombre et clair) depuis la palette."""
from pathlib import Path

def rgb(h): h = h.lstrip('#'); return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))

PALETTES = {
  "ExoLyx": dict(nom="ExoLyx", accent="#A8D479", accent2="#BDD479", accentFroid="#8DD479",
      fond="#0D1310", surface="#141C17", haute="#1C2620", vue="#101713", alt="#172019", bord="#2A362E",
      texte="#E6EFE1", doux="#97A893", inactif="#6E7D6B", surAccent="#0D1310",
      erreur="#E5766B", attention="#E8C26A", info="#79C2D4", lien="#A8D479", visite="#C6A8E0"),
  "ExoLyxClair": dict(nom="ExoLyx Clair", accent="#5E9B2E", accent2="#7DB547", accentFroid="#4E8F3A",
      fond="#F4F8F1", surface="#FFFFFF", haute="#E9F0E4", vue="#FFFFFF", alt="#F1F6EE", bord="#D3DECB",
      texte="#16201A", doux="#5B6B57", inactif="#8A9886", surAccent="#FFFFFF",
      erreur="#C2453A", attention="#A87A12", info="#2F7F94", lien="#4E8F3A", visite="#7B4FA8"),
  # Style « Ardoise » des logiciels de base : anthracite dense, accent orange, sélection bleu nuit
  "Ardoise": dict(nom="Ardoise", accent="#E8803A", accent2="#F09A5C", accentFroid="#6AAB73",
      fond="#1E1F22", surface="#2B2D30", haute="#393B40", vue="#1E1F22", alt="#232427", bord="#393B40",
      texte="#DFE1E5", doux="#868A91", inactif="#6F737A", surAccent="#FFFFFF",
      erreur="#F75464", attention="#E0B45C", info="#56A8F5", lien="#56A8F5", visite="#C77DBB",
      selection="#2E436E"),
}

def section(p, fond, alt, texte=None):
    texte = texte or p["texte"]
    return {
        "BackgroundAlternate": alt, "BackgroundNormal": fond,
        "DecorationFocus": p["accent"], "DecorationHover": p["accent2"],
        "ForegroundActive": p["accent"], "ForegroundInactive": p["doux"],
        "ForegroundLink": p["lien"], "ForegroundNegative": p["erreur"],
        "ForegroundNeutral": p["attention"], "ForegroundNormal": texte,
        "ForegroundPositive": p["accentFroid"], "ForegroundVisited": p["visite"],
    }

def schema(cle, p):
    s = {}
    s["ColorEffects:Disabled"] = {"Color": rgb(p["fond"]), "ColorAmount": "0", "ColorEffect": "0",
        "ContrastAmount": "0.65", "ContrastEffect": "1", "IntensityAmount": "0.1", "IntensityEffect": "2"}
    s["ColorEffects:Inactive"] = {"ChangeSelectionColor": "true", "Color": rgb(p["fond"]), "ColorAmount": "0.025",
        "ColorEffect": "2", "ContrastAmount": "0.1", "ContrastEffect": "2", "Enable": "false",
        "IntensityAmount": "0", "IntensityEffect": "0"}
    s["Colors:Button"] = section(p, p["haute"], p["surface"])
    s["Colors:Complementary"] = section(PALETTES["ExoLyx"], "#0D1310", "#141C17")
    s["Colors:Header"] = section(p, p["surface"], p["fond"])
    s["Colors:Header][Inactive"] = section(p, p["fond"], p["surface"])
    fond_sel = p.get("selection", p["accent"])
    sel = section(p, fond_sel, p.get("selection", p["accentFroid"]), p["surAccent"])
    sel.update({"ForegroundActive": p["surAccent"], "ForegroundInactive": p["surAccent"],
                "ForegroundLink": p["surAccent"], "ForegroundVisited": p["surAccent"]})
    s["Colors:Selection"] = sel
    s["Colors:Tooltip"] = section(p, p["haute"], p["surface"])
    s["Colors:View"] = section(p, p["vue"], p["alt"])
    s["Colors:Window"] = section(p, p["fond"], p["surface"])
    s["General"] = {"ColorScheme": cle, "Name": p["nom"], "shadeSortColumn": "true",
                    "AccentColor": rgb(p["accent"]), "TitlebarIsAccentColored": "false"}
    s["KDE"] = {"contrast": "4"}
    s["WM"] = {"activeBackground": rgb(p["surface"]), "activeBlend": rgb(p["accent"]),
               "activeForeground": rgb(p["texte"]), "inactiveBackground": rgb(p["fond"]),
               "inactiveBlend": rgb(p["doux"]), "inactiveForeground": rgb(p["doux"])}
    lignes = []
    for nom, cles in s.items():
        lignes.append(f"[{nom}]")
        for k, v in cles.items():
            lignes.append(f"{k}={rgb(v) if isinstance(v, str) and v.startswith('#') else v}")
        lignes.append("")
    return "\n".join(lignes)

if __name__ == "__main__":
    dest = Path(__file__).parent / "color-schemes"; dest.mkdir(exist_ok=True)
    for cle, p in PALETTES.items():
        (dest / f"{cle}.colors").write_text(schema(cle, p))
        print("écrit", dest / f"{cle}.colors")
