"""
Weapon Attack Power Scaling by Character
=========================================
Source: "Nightreign Weapon Scaling - Weapon Attack Power.pdf"
Data: Attack Power at lv12, no relics equipped
Characters (column order): Wylder, Guardian, Ironeye, Duchess, Raider, Revenant, Recluse, Executor
Note: Scholar and Undertaker are not in this dataset (added in later content).

NOTES FROM SOURCE:
- Tables show weapon AP at lv12 with no relics.
- Intention is to illustrate good vs bad users of each weapon.
- Only base status buildup is listed next to weapon name.
- During exploration, random weapons with elemental infusion have altered scaling
  (e.g. sacred changes scaling to lean towards faith). But elemental damage added
  via relic (converts ~40-50% AP to elemental) does NOT change scaling.
- Starting weapon performs similarly to unique purple once upgraded to purple rarity.
  (Starting bow at lv15 is 104 AP. Starting katana is 149 AP.)
- Adding status via Relic reduces ~20% AP.
- All unique AoWs scale off 1-handed AP.
- Game shows a single attack power, but most weapons still do split damage
  between physical and elemental.
- Crossbows have identical AP across all characters (no stat scaling).

For Staves and Sacred Seals, only 3 columns are shown (relevant caster characters).
Staves: Recluse (1st), (2nd), (3rd) — exact character order TBD
Seals: (1st), (2nd), (3rd) — exact character order TBD
"""

# Character column order for main weapons (8 characters)
CHARACTERS = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider", "Revenant", "Recluse", "Executor"]

# ─────────────────────────────────────────────────────────────────────────────
# DAGGERS
# ─────────────────────────────────────────────────────────────────────────────

DAGGERS = {
    "Duchess Dagger":                {"ap": [70, 61, 77, 65, 56, 53, 49, 82]},
    "Dagger":                        {"ap": [74, 64, 81, 68, 59, 56, 52, 86]},
    "Parrying Dagger":               {"ap": [76, 67, 84, 71, 61, 58, 54, 89]},
    "Great Knife":                   {"ap": [71, 62, 78, 66, 57, 54, 50, 83], "status": "30 bleed"},
    "Misericorde":                   {"ap": [92, 80, 101, 85, 74, 69, 65, 107]},
    "Bloodstained Dagger":           {"ap": [84, 73, 91, 78, 67, 64, 59, 98], "status": "34 bleed"},
    "Erdsteel Dagger":               {"ap": [95, 87, 102, 94, 78, 87, 83, 105]},
    "Wakizashi":                     {"ap": [85, 74, 94, 79, 68, 65, 60, 100], "status": "34 bleed"},
    "Celebrant's Sickle":            {"ap": [93, 81, 102, 86, 75, 70, 66, 109]},
    "Ivory Sickle":                  {"ap": [89, 77, 95, 92, 70, 76, 78, 103]},
    "Crystal Knife":                 {"ap": [93, 81, 98, 97, 73, 80, 82, 105]},
    "Scorpion Stinger":              {"ap": [90, 79, 99, 84, 72, 68, 64, 106], "status": "56 rot"},
    "Cinquedea":                     {"ap": [111, 97, 122, 103, 89, 84, 79, 130]},
    "Glintstone Kris":               {"ap": [106, 91, 113, 109, 83, 90, 93, 122]},
    "Reduvia":                       {"ap": [91, 81, 100, 86, 76, 73, 68, 115], "status": "56 bleed"},
    "Blade of Calling":              {"ap": [112, 102, 121, 111, 92, 103, 98, 127]},
    "Black Knife":                   {"ap": [111, 101, 120, 110, 92, 102, 97, 127]},
}

# ─────────────────────────────────────────────────────────────────────────────
# STRAIGHT SWORDS
# ─────────────────────────────────────────────────────────────────────────────

STRAIGHT_SWORDS = {
    "Short Sword":                   {"ap": [101, 88, 92, 76, 95, 72, 63, 100]},
    "Longsword":                     {"ap": [101, 88, 92, 76, 95, 72, 63, 100]},
    "Broadsword":                    {"ap": [101, 88, 92, 76, 95, 72, 63, 100]},
    "Weathered Straight Sword":      {"ap": [103, 90, 95, 78, 97, 74, 64, 103]},
    "Noble's Slender Sword":         {"ap": [105, 92, 96, 79, 99, 75, 65, 104]},
    "Lordsworn's Straight Sword":    {"ap": [125, 109, 114, 94, 118, 89, 78, 124]},
    "Cane Sword":                    {"ap": [127, 111, 116, 96, 119, 90, 79, 125]},
    "Warhawk's Talon":               {"ap": [129, 113, 118, 98, 122, 92, 81, 128]},
    "Lazuli Glintstone Sword":       {"ap": [118, 102, 107, 105, 109, 96, 96, 116]},
    "Carian Knight's Sword":         {"ap": [123, 106, 110, 109, 112, 100, 99, 120]},
    "Crystal Sword":                 {"ap": [116, 100, 105, 103, 107, 94, 94, 114]},
    "Rotten Crystal Sword":          {"ap": [109, 94, 98, 97, 101, 89, 88, 107], "status": "34 rot"},
    "Miquellan Knight's Sword":      {"ap": [148, 135, 136, 125, 142, 131, 120, 144]},
    "Ornamental Straight Sword":     {"ap": [151, 132, 138, 114, 142, 108, 94, 150]},
    "Golden Epitaph":                {"ap": [142, 129, 131, 120, 136, 126, 115, 138]},
    "Sword of St. Trina":            {"ap": [119, 102, 106, 105, 108, 97, 96, 116], "status": "56 sleep"},
    "Regalia of Eochaid":            {"ap": [154, 136, 146, 122, 147, 117, 103, 173]},
    "Coded Sword":                   {"ap": [83, 93, 80, 102, 80, 135, 135, 72]},
    "Sword of Night and Flame":      {"ap": [163, 148, 147, 159, 148, 161, 161, 154]},
}

# ─────────────────────────────────────────────────────────────────────────────
# GREATSWORDS
# ─────────────────────────────────────────────────────────────────────────────

GREATSWORDS = {
    "Wylder's Greatsword":           {"ap": [114, 100, 101, 84, 110, 81, 70, 110]},
    "Bastard Sword":                 {"ap": [121, 106, 108, 89, 117, 86, 75, 117]},
    "Iron Greatsword":               {"ap": [126, 110, 112, 92, 121, 90, 77, 121]},
    "Lordsworn's Greatsword":        {"ap": [121, 106, 108, 89, 117, 86, 75, 117]},
    "Claymore":                      {"ap": [153, 134, 136, 112, 147, 109, 94, 148]},
    "Knight's Greatsword":           {"ap": [153, 134, 136, 112, 147, 109, 94, 148]},
    "Banished Knight's Greatsword":  {"ap": [153, 134, 136, 112, 147, 109, 94, 148]},
    "Forked Greatsword":             {"ap": [136, 119, 121, 100, 131, 97, 84, 131], "status": "42 bleed"},
    "Flameberge":                    {"ap": [136, 119, 121, 100, 131, 97, 84, 131], "status": "42 bleed"},
    "Inseparable Sword":             {"ap": [148, 135, 132, 122, 143, 131, 119, 139]},
    "Gargoyle's Greatsword":         {"ap": [156, 137, 138, 114, 150, 111, 96, 150]},
    "Gargoyle's Black Blade":        {"ap": [169, 154, 152, 140, 165, 149, 136, 161]},
    "Sword of Milos":                {"ap": [164, 144, 146, 121, 158, 117, 101, 159], "status": "47 bleed"},
    "Ordovis's Greatsword":          {"ap": [179, 163, 160, 148, 174, 158, 144, 169]},
    "Alabaster Lord's Sword":        {"ap": [176, 152, 155, 154, 165, 143, 142, 169]},
    "Death Poker":                   {"ap": [160, 138, 140, 140, 148, 130, 129, 152], "status": "47 frostbite"},
    "Helphen's Steeple":             {"ap": [179, 155, 157, 156, 167, 145, 144, 171]},
    "Marais Executioner's Sword":    {"ap": [198, 176, 184, 154, 194, 151, 133, 218]},
    "Blasphemous Blade":             {"ap": [195, 178, 175, 161, 190, 172, 157, 185]},
    "Golden Order Greatsword":       {"ap": [191, 174, 172, 158, 188, 169, 154, 182]},
    "Dark Moon Greatsword":          {"ap": [175, 151, 153, 152, 164, 141, 141, 167], "status": "52 frostbite"},
    "Sacred Relic Sword":            {"ap": [197, 180, 176, 163, 190, 174, 158, 185]},
}

# ─────────────────────────────────────────────────────────────────────────────
# COLOSSAL SWORDS
# ─────────────────────────────────────────────────────────────────────────────

COLOSSAL_SWORDS = {
    "Zweihander":                    {"ap": [147, 129, 123, 102, 147, 104, 89, 134]},
    "Greatsword":                    {"ap": [154, 135, 129, 107, 154, 109, 93, 141]},
    "Watchdog's Greatsword":         {"ap": [181, 159, 152, 126, 181, 128, 109, 165]},
    "Troll's Golden Sword":          {"ap": [185, 163, 155, 128, 185, 131, 112, 169]},
    "Troll Knight's Sword":          {"ap": [180, 156, 150, 150, 173, 145, 142, 163]},
    "Royal Greatsword":              {"ap": [209, 182, 175, 176, 205, 169, 166, 191]},
    "Godslayer's Greatsword":        {"ap": [220, 202, 188, 174, 221, 193, 174, 198]},
    "Grafted Blade Greatsword":      {"ap": [250, 220, 210, 174, 251, 178, 151, 229]},
    "Ruins Greatsword":              {"ap": [242, 211, 201, 203, 232, 197, 191, 219]},
    "Starscourge Greatsword":        {"ap": [239, 208, 199, 200, 230, 193, 189, 217]},
    "Maliketh's Black Blade":        {"ap": [239, 219, 204, 189, 240, 210, 189, 215]},
}

# ─────────────────────────────────────────────────────────────────────────────
# THRUSTING SWORDS
# ─────────────────────────────────────────────────────────────────────────────

THRUSTING_SWORDS = {
    "Rapier":                        {"ap": [91, 80, 103, 87, 71, 70, 66, 109]},
    "Estoc":                         {"ap": [87, 76, 99, 83, 68, 67, 63, 105]},
    "Noble's Estoc":                 {"ap": [91, 80, 103, 87, 71, 70, 66, 109]},
    "Cleanrot Knight's Sword":       {"ap": [109, 95, 123, 104, 85, 83, 79, 130]},
    "Rogier's Rapier":               {"ap": [113, 98, 127, 107, 88, 86, 81, 135]},
    "Antspur Rapier":                {"ap": [110, 96, 124, 105, 86, 84, 80, 132], "status": "56 rot"},
    "Frozen Needle":                 {"ap": [105, 92, 118, 100, 82, 80, 76, 126], "status": "56 frostbite"},
    "Great Epee":                    {"ap": [114, 99, 110, 92, 102, 83, 74, 119]},
    "Godskin Stitcher":              {"ap": [146, 127, 142, 118, 131, 106, 95, 153]},
    "Bloody Helice":                 {"ap": [140, 125, 140, 118, 128, 109, 97, 164], "status": "70 bleed"},
    "Dragon King's Cragblade":       {"ap": [188, 163, 183, 152, 171, 136, 122, 200]},
}

# ─────────────────────────────────────────────────────────────────────────────
# CURVED SWORDS
# ─────────────────────────────────────────────────────────────────────────────

CURVED_SWORDS = {
    "Scimitar":                      {"ap": [97, 84, 98, 82, 83, 71, 65, 106]},
    "Falchion":                      {"ap": [94, 82, 96, 80, 81, 69, 63, 103]},
    "Bandit's Curved Sword":         {"ap": [98, 86, 100, 84, 84, 72, 66, 107]},
    "Shotel":                        {"ap": [94, 82, 96, 80, 81, 69, 63, 103]},
    "Shamshir":                      {"ap": [117, 102, 119, 100, 101, 86, 78, 128]},
    "Grossmesser":                   {"ap": [117, 102, 119, 100, 101, 86, 78, 128]},
    "Scavenger's Curved Sword":      {"ap": [107, 94, 109, 92, 93, 79, 72, 117], "status": "34 bleed"},
    "Mantis Blade":                  {"ap": [121, 106, 123, 103, 104, 89, 81, 132]},
    "Beastman Curved Sword":         {"ap": [118, 103, 120, 101, 102, 87, 79, 129]},
    "Serpent God's Curved Sword":    {"ap": [121, 106, 123, 103, 104, 89, 81, 132]},
    "Flowing Curved Sword":          {"ap": [141, 123, 144, 120, 122, 104, 95, 154]},
    "Magma Blade":                   {"ap": [137, 125, 139, 128, 121, 125, 117, 146]},
    "Nox Flowing Sword":             {"ap": [145, 127, 148, 124, 125, 107, 97, 159]},
    "Wing of Astel":                 {"ap": [137, 118, 137, 134, 116, 114, 117, 149]},
    "Eclipse Shotel":                {"ap": [151, 137, 154, 140, 133, 137, 129, 162]},
}

# ─────────────────────────────────────────────────────────────────────────────
# CURVED GREATSWORDS
# ─────────────────────────────────────────────────────────────────────────────

CURVED_GREATSWORDS = {
    "Dismounter":                    {"ap": [124, 108, 113, 93, 116, 88, 77, 123]},
    "Omen Cleaver":                  {"ap": [155, 136, 142, 117, 146, 111, 97, 154]},
    "Monk's Flameblade":             {"ap": [153, 133, 139, 115, 144, 109, 95, 151]},
    "Beastman's Cleaver":            {"ap": [155, 136, 142, 117, 146, 111, 97, 154]},
    "Bloodhound's Fang":             {"ap": [144, 126, 131, 109, 135, 103, 90, 143], "status": "42 bleed"},
    "Onyx Lord's Greatsword":        {"ap": [184, 159, 165, 164, 168, 150, 149, 180]},
    "Zamor Curved Sword":            {"ap": [150, 131, 137, 113, 141, 107, 93, 148], "status": "70 frostbite"},
    "Magma Wyrm's Scalesword":       {"ap": [180, 164, 165, 152, 171, 159, 145, 174]},
    "Morgott's Cursed Sword":        {"ap": [189, 168, 179, 150, 179, 145, 127, 211], "status": "41 bleed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# KATANAS
# ─────────────────────────────────────────────────────────────────────────────

KATANAS = {
    "Executor's Blade":              {"ap": [79, 69, 87, 73, 63, 60, 56, 92], "status": "30 bleed"},
    "Uchigatana":                    {"ap": [84, 73, 92, 78, 67, 64, 59, 98], "status": "30 bleed"},
    "Nagakiba":                      {"ap": [106, 92, 116, 98, 85, 80, 75, 124], "status": "34 bleed"},
    "Serpentbone Blade":             {"ap": [92, 80, 101, 85, 74, 69, 65, 107], "status": "51 poison"},
    "Meteoric Ore Blade":            {"ap": [104, 89, 110, 107, 81, 88, 91, 119], "status": "34 bleed"},
    "Moonveil":                      {"ap": [124, 107, 132, 128, 98, 106, 109, 142], "status": "38 bleed"},
    "Rivers of Blood":               {"ap": [112, 99, 125, 106, 94, 90, 84, 145], "status": "56 bleed"},
    "Dragonscale Blade":             {"ap": [140, 122, 154, 130, 113, 106, 99, 164]},
    "Hand of Malenia":               {"ap": [143, 125, 157, 132, 115, 108, 101, 167], "status": "41 bleed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# TWINBLADES
# ─────────────────────────────────────────────────────────────────────────────

TWINBLADES = {
    "Twinblade":                     {"ap": [102, 89, 96, 79, 94, 73, 64, 104]},
    "Twinned Knight Swords":         {"ap": [126, 110, 118, 98, 116, 91, 80, 128]},
    "Godskin Peeler":                {"ap": [131, 115, 124, 103, 121, 95, 83, 134]},
    "Gargoyle's Twinblade":          {"ap": [129, 112, 121, 100, 118, 93, 82, 131]},
    "Gargoyle's Black Blades":       {"ap": [146, 134, 138, 127, 136, 131, 120, 145]},
    "Eleonora's Poleblade":          {"ap": [121, 106, 117, 98, 114, 92, 83, 139], "status": "56 bleed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# AXES
# ─────────────────────────────────────────────────────────────────────────────

AXES = {
    "Hand Axe":                      {"ap": [110, 96, 98, 81, 106, 78, 68, 106]},
    "Forked Hatchet":                {"ap": [104, 91, 93, 76, 100, 74, 64, 101], "status": "30 bleed"},
    "Battle Axe":                    {"ap": [110, 96, 98, 81, 106, 78, 68, 106]},
    "Jawbone Axe":                   {"ap": [113, 99, 100, 83, 109, 80, 69, 109]},
    "Warped Axe":                    {"ap": [142, 124, 126, 104, 136, 101, 87, 137]},
    "Iron Cleaver":                  {"ap": [136, 119, 121, 100, 131, 97, 84, 131]},
    "Highland Axe":                  {"ap": [136, 119, 121, 100, 131, 97, 84, 131]},
    "Celebrant's Cleaver":           {"ap": [139, 122, 123, 102, 134, 99, 85, 134]},
    "Ripple Blade":                  {"ap": [98, 98, 105, 100, 98, 102, 98, 138]},
    "Icerind Hatchet":               {"ap": [136, 119, 121, 100, 131, 97, 84, 131], "status": "56 frostbite"},
    "Sacrificial Axe":               {"ap": [166, 145, 147, 122, 160, 118, 102, 160]},
    "Stormhawk Axe":                 {"ap": [173, 152, 154, 127, 167, 123, 107, 167]},
    "Rosus' Axe":                    {"ap": [156, 135, 148, 146, 137, 129, 130, 161]},
}

# ─────────────────────────────────────────────────────────────────────────────
# GREATAXES
# ─────────────────────────────────────────────────────────────────────────────

GREATAXES = {
    "Greataxe":                      {"ap": [124, 111, 93, 78, 158, 88, 73, 103]},
    "Crescent Moon Axe":             {"ap": [124, 111, 93, 78, 158, 88, 73, 103]},
    "Longhaft Axe":                  {"ap": [124, 111, 93, 78, 158, 88, 73, 103]},
    "Executioner's Greataxe":        {"ap": [153, 136, 115, 96, 195, 108, 90, 126]},
    "Great Omenkiller Cleaver":      {"ap": [144, 128, 108, 90, 183, 102, 84, 118], "status": "42 bleed"},
    "Rusted Anchor":                 {"ap": [157, 140, 118, 98, 200, 111, 92, 130]},
    "Gargoyle's Great Axe":          {"ap": [160, 142, 120, 100, 204, 113, 94, 132]},
    "Gargoyle's Black Axe":          {"ap": [183, 169, 142, 133, 235, 158, 140, 149]},
    "Butchering Knife":              {"ap": [188, 167, 141, 117, 238, 133, 110, 155]},
    "Winged Greathorn":              {"ap": [212, 189, 159, 132, 270, 150, 125, 175]},
    "Axe of Godrick":                {"ap": [212, 189, 159, 132, 270, 150, 125, 175]},
}

# ─────────────────────────────────────────────────────────────────────────────
# HAMMERS
# ─────────────────────────────────────────────────────────────────────────────

HAMMERS = {
    "Club":                          {"ap": [96, 86, 66, 55, 108, 68, 55, 73]},
    "Curved Club":                   {"ap": [103, 91, 85, 70, 106, 73, 62, 92]},
    "Stone Club":                    {"ap": [105, 93, 86, 71, 107, 74, 63, 94]},
    "Mace":                          {"ap": [103, 91, 85, 70, 106, 73, 62, 92]},
    "Spiked Club":                   {"ap": [115, 101, 94, 78, 117, 81, 69, 102], "status": "34 bleed"},
    "Morning Star":                  {"ap": [116, 102, 95, 79, 119, 82, 70, 104], "status": "34 bleed"},
    "Warwick":                       {"ap": [124, 110, 102, 84, 127, 88, 75, 111]},
    "Hammer":                        {"ap": [124, 110, 102, 84, 127, 88, 75, 111]},
    "Monk's Flamemace":              {"ap": [127, 112, 104, 86, 130, 90, 76, 114]},
    "Varre's Bouquet":               {"ap": [102, 92, 89, 75, 104, 78, 67, 106], "status": "51 bleed"},
    "Envoy's Horn":                  {"ap": [144, 132, 119, 111, 147, 126, 113, 126]},
    "Nox Flowing Hammer":            {"ap": [151, 133, 124, 102, 154, 107, 91, 135]},
    "Ringed Finger":                 {"ap": [155, 137, 127, 105, 159, 110, 93, 139]},
    "Scepter of All Knowing":        {"ap": [150, 131, 122, 123, 149, 121, 118, 133]},
    "Marika's Hammer":               {"ap": [162, 149, 135, 126, 167, 142, 127, 142]},
}

# ─────────────────────────────────────────────────────────────────────────────
# FLAILS
# ─────────────────────────────────────────────────────────────────────────────

FLAILS = {
    "Flail":                         {"ap": [93, 81, 90, 75, 84, 67, 60, 97], "status": "30 bleed"},
    "Nightrider Flail":              {"ap": [114, 99, 110, 92, 102, 83, 74, 119], "status": "34 bleed"},
    "Chainlink Flail":               {"ap": [123, 108, 109, 90, 118, 88, 76, 119], "status": "34 bleed"},
    "Family Heads":                  {"ap": [150, 129, 142, 140, 131, 124, 124, 155]},
    "Bastard's Stars":               {"ap": [164, 141, 156, 153, 144, 135, 136, 170]},
}

# ─────────────────────────────────────────────────────────────────────────────
# GREAT HAMMERS (also includes Colossal Weapons in this data set)
# ─────────────────────────────────────────────────────────────────────────────

GREAT_HAMMERS = {
    "Large Club":                    {"ap": [117, 105, 81, 68, 156, 83, 68, 89]},
    "Curved Great Club":             {"ap": [119, 106, 87, 72, 155, 84, 69, 96]},
    "Great Mace":                    {"ap": [119, 106, 87, 72, 155, 84, 69, 96]},
    "Pickaxe":                       {"ap": [119, 106, 87, 72, 155, 84, 69, 96]},
    "Brick Hammer":                  {"ap": [148, 132, 108, 89, 192, 104, 86, 119]},
    "Battle Hammer":                 {"ap": [148, 132, 108, 89, 192, 104, 86, 119]},
    "Rotten Battle Hammer":          {"ap": [138, 123, 101, 84, 179, 98, 81, 111], "status": "42 rot"},
    "Celebrant's Skull":             {"ap": [151, 134, 110, 91, 195, 106, 88, 121]},
    "Great Stars":                   {"ap": [138, 123, 101, 84, 179, 98, 81, 111], "status": "42 bleed"},
    "Greathorn Hammer":              {"ap": [151, 134, 110, 91, 195, 106, 88, 121]},
    "Envoy's Long Horn":             {"ap": [170, 158, 128, 121, 220, 147, 130, 135]},
    "Cranial Vessel Candlestand":    {"ap": [173, 160, 130, 122, 224, 149, 132, 136]},
    "Beast-Claw Greathammer":        {"ap": [177, 164, 133, 125, 229, 153, 135, 140]},
    "Devourer's Scepter":            {"ap": [193, 178, 145, 137, 249, 167, 147, 152]},
}

# ─────────────────────────────────────────────────────────────────────────────
# COLOSSAL WEAPONS
# ─────────────────────────────────────────────────────────────────────────────

COLOSSAL_WEAPONS = {
    "Raider's Greataxe":             {"ap": [133, 119, 92, 77, 150, 94, 77, 102]},
    "Duelist Greataxe":              {"ap": [141, 127, 98, 81, 159, 100, 81, 108]},
    "Rotten Greataxe":               {"ap": [164, 147, 113, 95, 185, 116, 95, 125], "status": "76 rot"},
    "Golden Halberd":                {"ap": [177, 159, 123, 102, 200, 125, 102, 135]},
    "Giant Crusher":                 {"ap": [181, 163, 125, 105, 205, 128, 105, 139]},
    "Great Club":                    {"ap": [169, 158, 122, 115, 187, 146, 127, 129]},
    "Troll's Hammer":                {"ap": [166, 155, 120, 113, 185, 143, 125, 126]},
    "Prelate's Inferno Crozier":     {"ap": [217, 195, 151, 125, 245, 154, 125, 166]},
    "Dragon Great Claw":             {"ap": [211, 188, 145, 123, 243, 148, 123, 159]},
    "Watchdog's Staff":              {"ap": [212, 190, 147, 122, 239, 150, 122, 162]},
    "Staff of the Avatar":           {"ap": [200, 186, 144, 137, 225, 172, 151, 152]},
    "Rotten Staff":                  {"ap": [199, 178, 138, 115, 224, 140, 115, 152], "status": "84 rot"},
    "Envoy's Greathorn":             {"ap": [200, 186, 144, 137, 225, 172, 151, 152]},
    "Ghiza's Wheel":                 {"ap": [199, 178, 138, 115, 224, 140, 115, 152], "status": "56 bleed"},
    "Falling Star Beast Jaw":        {"ap": [209, 186, 147, 151, 228, 167, 158, 160]},
    "Axe of Godfrey":                {"ap": [242, 217, 167, 139, 272, 171, 139, 185]},
}

# ─────────────────────────────────────────────────────────────────────────────
# SPEARS
# ─────────────────────────────────────────────────────────────────────────────

SPEARS = {
    "Short Spear":                   {"ap": [102, 89, 96, 79, 94, 73, 64, 104]},
    "Iron Spear":                    {"ap": [106, 93, 100, 83, 97, 76, 67, 108]},
    "Spear":                         {"ap": [105, 91, 98, 82, 96, 75, 66, 106]},
    "Partisan":                      {"ap": [126, 110, 118, 98, 116, 91, 80, 128]},
    "Pike":                          {"ap": [131, 115, 124, 103, 121, 95, 83, 134]},
    "Spiked Spear":                  {"ap": [116, 101, 109, 90, 107, 83, 73, 118], "status": "34 bleed"},
    "Cross-Naginata":                {"ap": [117, 102, 110, 92, 108, 84, 74, 119], "status": "34 bleed"},
    "Clayman's Harpoon":             {"ap": [120, 104, 111, 109, 107, 98, 99, 120]},
    "Celebrant's Rib-Rake":          {"ap": [126, 110, 118, 98, 116, 91, 80, 128]},
    "Torchpole":                     {"ap": [127, 110, 120, 99, 119, 91, 81, 131]},
    "Crystal Spear":                 {"ap": [123, 107, 113, 112, 109, 101, 101, 123]},
    "Rotten Crystal Spear":          {"ap": [114, 98, 104, 104, 101, 94, 93, 113], "status": "34 rot"},
    "Inquisitor's Girandole":        {"ap": [133, 122, 126, 115, 124, 119, 110, 132], "status": "38 bleed"},
    "Cleanrot Spear":                {"ap": [145, 133, 137, 126, 136, 130, 119, 144]},
    "Death Ritual Spear":            {"ap": [151, 130, 139, 138, 135, 124, 124, 151]},
    "Bolt of Gransax":               {"ap": [168, 146, 159, 131, 157, 120, 107, 173]},
}

# ─────────────────────────────────────────────────────────────────────────────
# GREAT SPEARS
# ─────────────────────────────────────────────────────────────────────────────

GREAT_SPEARS = {
    "Lance":                         {"ap": [135, 119, 116, 96, 133, 96, 82, 127]},
    "Treespear":                     {"ap": [155, 141, 150, 138, 142, 139, 129, 159]},
    "Serpent Hunter":                {"ap": [173, 152, 149, 123, 171, 123, 106, 163]},
    "Siluria's Tree":                {"ap": [200, 182, 174, 160, 199, 175, 159, 184]},
    "Vyke's War Spear":              {"ap": [192, 176, 167, 155, 191, 169, 153, 177], "status": "70 madness"},
    "Mohgwyn's Sacred Spear":        {"ap": [177, 158, 160, 135, 177, 135, 118, 190], "status": "77 bleed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# HALBERDS
# ─────────────────────────────────────────────────────────────────────────────

HALBERDS = {
    "Guardian's Halberd":            {"ap": [111, 98, 99, 82, 107, 79, 69, 107]},
    "Halberd":                       {"ap": [117, 103, 104, 86, 113, 83, 72, 113]},
    "Banished Knight's Halberd":     {"ap": [123, 108, 109, 90, 118, 88, 76, 119]},
    "Lucerne":                       {"ap": [117, 103, 104, 86, 113, 83, 72, 113]},
    "Glaive":                        {"ap": [123, 108, 109, 90, 118, 88, 76, 119]},
    "Vulgar Militia Shotel":         {"ap": [124, 109, 110, 91, 120, 89, 77, 120]},
    "Vulgar Militia Saw":            {"ap": [113, 99, 100, 83, 109, 80, 69, 109], "status": "38 bleed"},
    "Guardian's Sword-Spear":        {"ap": [131, 115, 144, 122, 105, 100, 93, 154]},
    "Nightrider Glaive":             {"ap": [147, 129, 131, 108, 142, 105, 91, 142]},
    "Pest Glaive":                   {"ap": [144, 127, 128, 106, 139, 103, 89, 139]},
    "Ripple Crescent Halberd":       {"ap": [104, 104, 112, 107, 104, 109, 104, 147]},
    "Gargoyle's Halberd":            {"ap": [150, 132, 133, 110, 145, 107, 92, 145]},
    "Gargoyle's Black Halberd":      {"ap": [173, 160, 155, 144, 166, 154, 139, 162]},
    "Golden Halberd (Halberd type)": {"ap": [171, 156, 153, 141, 166, 151, 138, 162]},
    "Dragon Halberd":                {"ap": [176, 154, 156, 129, 169, 125, 108, 170]},
    "Loretta's War Sickle":          {"ap": [171, 148, 150, 149, 159, 139, 138, 163]},
    "Commander's Standard":          {"ap": [183, 160, 163, 134, 176, 130, 113, 177]},
}

# ─────────────────────────────────────────────────────────────────────────────
# REAPERS (Scythes)
# ─────────────────────────────────────────────────────────────────────────────

REAPERS = {
    "Scythe":                        {"ap": [92, 80, 97, 81, 77, 69, 63, 104], "status": "38 bleed"},
    "Grave Scythe":                  {"ap": [115, 100, 121, 101, 96, 86, 79, 129], "status": "42 bleed"},
    "Halo Scythe":                   {"ap": [136, 124, 141, 129, 116, 124, 117, 149], "status": "38 bleed"},
    "Winged Scythe":                 {"ap": [129, 117, 135, 123, 111, 117, 111, 142], "status": "38 bleed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# WHIPS
# ─────────────────────────────────────────────────────────────────────────────

WHIPS = {
    "Whip":                          {"ap": [93, 81, 100, 84, 77, 70, 65, 107]},
    "Thorned Whip":                  {"ap": [106, 93, 114, 96, 87, 80, 74, 122], "status": "34 bleed"},
    "Urumi":                         {"ap": [121, 105, 129, 109, 99, 91, 84, 138]},
    "Hoslow's Petal Whip":           {"ap": [132, 116, 142, 119, 109, 99, 92, 151], "status": "38 bleed"},
    "Magma Whip Candlestick":        {"ap": [137, 124, 145, 133, 116, 126, 119, 153]},
    "Giant's Red Braid":             {"ap": [152, 138, 161, 147, 128, 139, 132, 169]},
}

# ─────────────────────────────────────────────────────────────────────────────
# FISTS
# ─────────────────────────────────────────────────────────────────────────────

FISTS = {
    "Revenant's Cursed Claws":       {"ap": [50, 54, 45, 55, 51, 83, 71, 42]},
    "Katar":                         {"ap": [91, 80, 81, 67, 88, 65, 56, 88]},
    "Cestus":                        {"ap": [87, 76, 77, 64, 84, 62, 54, 84]},
    "Spiked Cestus":                 {"ap": [97, 85, 86, 71, 93, 69, 60, 94], "status": "34 bleed"},
    "Iron Ball":                     {"ap": [110, 96, 98, 81, 106, 78, 68, 106]},
    "Star Fist":                     {"ap": [101, 89, 90, 74, 98, 72, 62, 98], "status": "34 bleed"},
    "Clinging Bone":                 {"ap": [130, 116, 121, 101, 127, 99, 87, 143]},
    "Veteran's Prosthesis":          {"ap": [133, 114, 118, 97, 130, 94, 82, 129]},
    "Cipher Pata":                   {"ap": [71, 79, 68, 87, 68, 115, 115, 61]},
    "Grafted Dragon":                {"ap": [141, 129, 127, 117, 137, 125, 114, 134]},
}

# ─────────────────────────────────────────────────────────────────────────────
# CLAWS
# ─────────────────────────────────────────────────────────────────────────────

CLAWS = {
    "Hookclaws":                     {"ap": [75, 65, 76, 64, 65, 55, 50, 82], "status": "30 bleed"},
    "Bloodhound Claws":              {"ap": [97, 84, 98, 82, 83, 71, 65, 106], "status": "34 bleed"},
    "Venomous Fang":                 {"ap": [84, 74, 86, 72, 73, 62, 57, 92], "status": "51 poison"},
    "Raptor Talons":                 {"ap": [115, 101, 118, 98, 100, 85, 77, 126], "status": "38 bleed"},
}

# ─────────────────────────────────────────────────────────────────────────────
# BOWS
# ─────────────────────────────────────────────────────────────────────────────

BOWS = {
    "Ironeye's Bow":                 {"ap": [56, 49, 63, 53, 44, 43, 40, 67]},
    "Short Bow":                     {"ap": [57, 50, 65, 55, 45, 44, 41, 69]},
    "Misbegotten Short Bow":         {"ap": [62, 54, 70, 59, 49, 48, 45, 75]},
    "Longbow":                       {"ap": [60, 52, 67, 57, 47, 46, 43, 72]},
    "Composite Bow":                 {"ap": [74, 64, 83, 70, 57, 56, 53, 88]},
    "Red Branch Short Bow":          {"ap": [71, 62, 80, 68, 56, 54, 51, 85]},
    "Harp Bow":                      {"ap": [74, 64, 83, 70, 57, 56, 53, 88]},
    "Albinauric Bow":                {"ap": [76, 66, 86, 73, 59, 58, 55, 91]},
    "Horn Bow":                      {"ap": [77, 67, 84, 82, 59, 67, 69, 89]},
    "Black Bow":                     {"ap": [91, 80, 103, 87, 71, 70, 66, 109]},
    "Pulley Bow":                    {"ap": [90, 79, 101, 86, 70, 69, 65, 108]},
    "Serpent Bow":                   {"ap": [73, 65, 83, 71, 60, 60, 56, 95], "status": "30 poison"},
    "Erdtree Bow":                   {"ap": [89, 82, 98, 90, 71, 83, 79, 101]},
}

# ─────────────────────────────────────────────────────────────────────────────
# GREATBOWS
# ─────────────────────────────────────────────────────────────────────────────

GREATBOWS = {
    "Greatbow":                      {"ap": [165, 145, 142, 117, 162, 117, 101, 155]},
    "Golem Greatbow":                {"ap": [208, 182, 179, 148, 204, 148, 127, 195]},
    "Erdtree Greatbow":              {"ap": [229, 215, 204, 194, 222, 211, 193, 212]},
    "Lion Greatbow":                 {"ap": [259, 228, 223, 184, 255, 184, 158, 243]},
}

# ─────────────────────────────────────────────────────────────────────────────
# CROSSBOWS (stat-independent — same AP for all characters)
# ─────────────────────────────────────────────────────────────────────────────

CROSSBOWS = {
    "Soldier's Crossbow":            {"ap": [88]},  # All characters equal
    "Light Crossbow":                {"ap": [89]},
    "Heavy Crossbow":                {"ap": [90]},
    "Arbalest":                      {"ap": [92]},
    "Crepus's Black-Key Crossbow":   {"ap": [111]},
    "Full Moon Crossbow":            {"ap": [111]},
    "Pulley Crossbow":               {"ap": [63]},
    "Hand Ballista":                 {"ap": [258]},
    "Jar Cannon":                    {"ap": [350]},
}

# ─────────────────────────────────────────────────────────────────────────────
# STAVES (Glintstone Staves — only relevant caster characters shown)
# Column order for staves: [Recluse, ?, ?] — exact characters TBD from source
# Note: Scholar and Undertaker not in this dataset; columns likely Wylder/Recluse/other
# ─────────────────────────────────────────────────────────────────────────────

STAVES = {
    "Recluse Staff":                 {"ap": [118, 107, 128]},
    "Astrologer's Staff":            {"ap": [141, 129, 154]},
    "Glintstone Staff":              {"ap": [139, 126, 151]},
    "Academy Glintstone Staff":      {"ap": [144, 131, 157]},
    "Digger's Staff":                {"ap": [147, 134, 160]},
    "Demi-Human Queen's Staff":      {"ap": [140, 128, 152]},
    "Carian Glintstone Staff":       {"ap": [166, 151, 180]},
    "Carian Glintblade Staff":       {"ap": [170, 155, 185]},
    "Albinauric Staff":              {"ap": [163, 149, 178]},
    "Staff of Loss":                 {"ap": [159, 145, 173]},
    "Gelmir Glintstone Staff":       {"ap": [162, 147, 176]},
    "Crystal Staff":                 {"ap": [169, 154, 183]},
    "Rotten Crystal Staff":          {"ap": [167, 152, 182]},
    "Staff of Guilty":               {"ap": [171, 156, 186]},
    "Azur Glintstone Staff":         {"ap": [192, 175, 209]},
    "Lusat Glintstone Staff":        {"ap": [194, 177, 212]},
    "Meteorite Staff":               {"ap": [188, 171, 204]},
    "Prince of Death's Staff":       {"ap": [184, 168, 200]},
    "Carian Regal Scepter":          {"ap": [218, 198, 237]},
}

# ─────────────────────────────────────────────────────────────────────────────
# SACRED SEALS — only relevant caster characters shown
# Column order for seals: [Revenant?, ?, ?] — exact characters TBD
# ─────────────────────────────────────────────────────────────────────────────

SACRED_SEALS = {
    "Finger Seal":                   {"ap": [122, 151, 151]},
    "Gravel Stone Seal":             {"ap": [144, 178, 178]},
    "Giants' Seal":                  {"ap": [147, 182, 182]},
    "Godslayer Seal":                {"ap": [140, 173, 173]},
    "Clawmark Seal":                 {"ap": [151, 186, 186]},
    "Erdtree Seal":                  {"ap": [166, 204, 204]},
    "Golden Order Seal":             {"ap": [162, 200, 200]},
    "Frenzied Flame Seal":           {"ap": [172, 212, 212]},
    "Dragon Communion Seal":         {"ap": [169, 209, 209]},
}

# ─────────────────────────────────────────────────────────────────────────────
# ALL WEAPONS by class (for lookup)
# ─────────────────────────────────────────────────────────────────────────────

ALL_WEAPONS_BY_CLASS = {
    "Dagger":              DAGGERS,
    "Straight Sword":      STRAIGHT_SWORDS,
    "Greatsword":          GREATSWORDS,
    "Colossal Sword":      COLOSSAL_SWORDS,
    "Thrusting Sword":     THRUSTING_SWORDS,
    "Curved Sword":        CURVED_SWORDS,
    "Curved Greatsword":   CURVED_GREATSWORDS,
    "Katana":              KATANAS,
    "Twinblade":           TWINBLADES,
    "Axe":                 AXES,
    "Greataxe":            GREATAXES,
    "Hammer":              HAMMERS,
    "Flail":               FLAILS,
    "Great Hammer":        GREAT_HAMMERS,
    "Colossal Weapon":     COLOSSAL_WEAPONS,
    "Spear":               SPEARS,
    "Great Spear":         GREAT_SPEARS,
    "Halberd":             HALBERDS,
    "Reaper":              REAPERS,
    "Whip":                WHIPS,
    "Fist":                FISTS,
    "Claw":                CLAWS,
    "Bow":                 BOWS,
    "Greatbow":            GREATBOWS,
    "Crossbow":            CROSSBOWS,
    "Glintstone Staff":    STAVES,
    "Sacred Seal":         SACRED_SEALS,
}


def get_weapon_ap(weapon_name: str) -> dict | None:
    """Look up a weapon's AP data by name. Returns None if not found."""
    for weapons in ALL_WEAPONS_BY_CLASS.values():
        if weapon_name in weapons:
            return weapons[weapon_name]
    return None


def get_best_character_for_weapon(weapon_name: str) -> str | None:
    """Return the character with the highest AP for this weapon."""
    data = get_weapon_ap(weapon_name)
    if data is None or "ap" not in data:
        return None
    ap = data["ap"]
    if len(ap) == 8:
        best_idx = ap.index(max(ap))
        return CHARACTERS[best_idx]
    return None


def get_weapons_best_for_character(character: str, weapon_class: str | None = None) -> list[tuple[str, int]]:
    """
    Returns a sorted list of (weapon_name, ap) for the given character.
    Optionally filtered by weapon class.
    """
    if character not in CHARACTERS:
        return []
    char_idx = CHARACTERS.index(character)

    results = []
    classes_to_search = {weapon_class: ALL_WEAPONS_BY_CLASS[weapon_class]} \
        if weapon_class and weapon_class in ALL_WEAPONS_BY_CLASS \
        else ALL_WEAPONS_BY_CLASS

    for weapons in classes_to_search.values():
        for name, data in weapons.items():
            ap = data.get("ap", [])
            if len(ap) > char_idx:
                results.append((name, ap[char_idx]))

    return sorted(results, key=lambda x: x[1], reverse=True)
