"""
Complete list of Elden Ring Nightreign relic passives and curses.
Source: verbatim in-game text extracted from game screenshots.
No +1/+2/+3/+4 variants are included — baseline names only.
"""

from collections import OrderedDict

CATEGORIES: "OrderedDict[str, list[str]]" = OrderedDict([

    ("Attributes", [
        "Increased Maximum HP",
        "Increased Maximum FP",
        "Increased Maximum Stamina",
        "Vigor +1",
        "Vigor +2",
        "Vigor +3",
        "Mind +1",
        "Mind +2",
        "Mind +3",
        "Endurance +1",
        "Endurance +2",
        "Endurance +3",
        "Strength +1",
        "Strength +2",
        "Strength +3",
        "Dexterity +1",
        "Dexterity +2",
        "Dexterity +3",
        "Intelligence +1",
        "Intelligence +2",
        "Intelligence +3",
        "Faith +1",
        "Faith +2",
        "Faith +3",
        "Arcane +1",
        "Arcane +2",
        "Arcane +3",
        "Poise +1",
        "Poise +2",
        "Poise +3",
        "Max FP increased for each Sorcerer's Rise unlocked",
        "Runes and Item Discovery increased for each great enemy defeated at a Fort",
        "Max HP increased for each great enemy defeated at a Great Church",
        "Max stamina increased for each great enemy defeated at a Great Encampment",
        "Arcane increased for each great enemy defeated at a Ruin",
    ]),

    ("Attack Power", [
        "Physical Attack Up",
        "Physical Attack Up +1",
        "Physical Attack Up +2",
        "Physical Attack Up +3",
        "Physical Attack Up +4",
        "Improved Affinity Attack Power",
        "Improved Affinity Attack Power +1",
        "Improved Affinity Attack Power +2",
        "Magic Attack Power Up",
        "Magic Attack Power Up +1",
        "Magic Attack Power Up +2",
        "Magic Attack Power Up +3",
        "Magic Attack Power Up +4",
        "Fire Attack Power Up",
        "Fire Attack Power Up +1",
        "Fire Attack Power Up +2",
        "Fire Attack Power Up +3",
        "Fire Attack Power Up +4",
        "Lightning Attack Power Up",
        "Lightning Attack Power Up +1",
        "Lightning Attack Power Up +2",
        "Lightning Attack Power Up +3",
        "Lightning Attack Power Up +4",
        "Holy Attack Power Up",
        "Holy Attack Power Up +1",
        "Holy Attack Power Up +2",
        "Holy Attack Power Up +3",
        "Holy Attack Power Up +4",
        "Improved Melee Attack Power",
        "Improved Skill Attack Power",
        "Improved Initial Standard Attack",
        "Successive Attacks Boost Attack Power",
        "Improved Critical Hits",
        "Improved Sorceries",
        "Improved Sorceries +1",
        "Improved Sorceries +2",
        "Improved Incantations",
        "Improved Incantations +1",
        "Improved Incantations +2",
        "Improved Roar & Breath Attacks",
        "Improved Stance-Breaking when Two-Handing",
        "Improved Stance-Breaking when Wielding Two Armaments",
        "Switching Weapons Boosts Attack Power",
        "Boosts Attack Power of Added Affinity Attacks",
        "Taking attacks improves attack power",
        "Status Ailment Gauges Slowly Increase Attack Power",
        "Attack power increased for each evergaol prisoner defeated",
        "Attack power increased for each Night Invader defeated",
        "Improved Guard Counters",
        "Improved Guard Counters +1",
        "Improved Guard Counters +2",
        "Guard counter is given a boost based on current HP",
        "Physical attack power increases after using grease items",
        "Physical attack power increases after using grease items +1",
        "Physical attack power increases after using grease items +2",
        "Improved Throwing Pot Damage",
        "Improved Throwing Pot Damage +1",
        "Improved Throwing Knife Damage",
        "Improved Throwing Knife Damage +1",
        "Improved Glintstone and Gravity Stone Damage",
        "Improved Glintstone and Gravity Stone Damage +1",
        "Improved Perfuming Arts",
        "Improved Perfuming Arts +1",
    ]),

    ("Character Skills & Art", [
        "Character Skill Cooldown Reduction",
        "Character Skill Cooldown Reduction +1",
        "Character Skill Cooldown Reduction +2",
        "Character Skill Cooldown Reduction +3",
        "Ultimate Art Auto Charge",
        "Ultimate Art Auto Charge +1",
        "Ultimate Art Auto Charge +2",
        "Ultimate Art Auto Charge +3",
        "Defeating enemies fills more of the Art gauge",
        "Defeating enemies fills more of the Art gauge +1",
        "Critical hits fill more of the Art gauge",
        "Critical hits fill more of the Art gauge +1",
        "Successful guarding fills more of the Art gauge",
        "Successful guarding fills more of the Art gauge +1",
    ]),

    ("Sorceries & Incantations", [
        "Extended Spell Duration",
        "Improved Glintblade Sorcery",
        "Improved Stonedigger Sorcery",
        "Improved Carian Sword Sorcery",
        "Improved Invisibility Sorcery",
        "Improved Crystalian Sorcery",
        "Improved Gravity Sorcery",
        "Improved Thorn Sorcery",
        "Improved Fundamentalist Incantations",
        "Improved Dragon Cult Incantations",
        "Improved Giants' Flame Incantations",
        "Improved Godslayer Incantations",
        "Improved Bestial Incantations",
        "Improved Frenzied Flame Incantations",
        "Improved Dragon Communion Incantations",
    ]),

    ("Damage Negation", [
        "Improved Physical Damage Negation",
        "Improved Physical Damage Negation +1",
        "Improved Physical Damage Negation +2",
        "Improved Affinity Damage Negation",
        "Improved Affinity Damage Negation +1",
        "Improved Affinity Damage Negation +2",
        "Improved Magic Damage Negation",
        "Improved Magic Damage Negation +1",
        "Improved Magic Damage Negation +2",
        "Improved Fire Damage Negation",
        "Improved Fire Damage Negation +1",
        "Improved Fire Damage Negation +2",
        "Improved Lightning Damage Negation",
        "Improved Lightning Damage Negation +1",
        "Improved Lightning Damage Negation +2",
        "Improved Holy Damage Negation",
        "Improved Holy Damage Negation +1",
        "Improved Holy Damage Negation +2",
        "Magic Damage Negation Up",
        "Magic Damage Negation Up +1",
        "Magic Damage Negation Up +2",
        "Fire Damage Negation Up",
        "Fire Damage Negation Up +1",
        "Fire Damage Negation Up +2",
        "Lightning Damage Negation Up",
        "Lightning Damage Negation Up +1",
        "Lightning Damage Negation Up +2",
        "Holy Damage Negation Up",
        "Holy Damage Negation Up +1",
        "Holy Damage Negation Up +2",
        "Improved Damage Negation at Low HP",
        "Improved Poise & Damage Negation When Knocked Back by Damage",
    ]),

    ("Status Ailment Resistances", [
        "Improved Poison Resistance",
        "Improved Poison Resistance +1",
        "Improved Poison Resistance +2",
        "Improved Rot Resistance",
        "Improved Rot Resistance +1",
        "Improved Rot Resistance +2",
        "Improved Blood Loss Resistance",
        "Improved Blood Loss Resistance +1",
        "Improved Blood Loss Resistance +2",
        "Improved Frost Resistance",
        "Improved Frost Resistance +1",
        "Improved Frost Resistance +2",
        "Improved Sleep Resistance",
        "Improved Sleep Resistance +1",
        "Improved Sleep Resistance +2",
        "Improved Madness Resistance",
        "Improved Madness Resistance +1",
        "Improved Madness Resistance +2",
        "Improved Death Blight Resistance",
        "Improved Death Blight Resistance +1",
        "Improved Death Blight Resistance +2",
    ]),

    ("Restoration", [
        "Continuous HP Recovery",
        "Slowly restore HP for self and nearby allies when HP is low",
        "HP Recovery From Successful Guarding",
        "HP Restoration upon Thrusting Counterattack",
        "HP Restoration upon Thrusting Counterattack +1",
        "Partial HP Restoration upon Post-Damage Attacks",
        "Partial HP Restoration upon Post-Damage Attacks +1",
        "Partial HP Restoration upon Post-Damage Attacks +2",
        "HP restored when using medicinal boluses, etc.",
        "HP restored when using medicinal boluses, etc. +1",
        "Rot in Vicinity Causes Continuous HP Recovery",
        "Improved Flask HP Restoration",
        "Reduced FP Consumption",
        "Continuous FP Recovery",
        "FP Restoration upon Successive Attacks",
        "Madness Continually Recovers FP",
        "Stamina Recovery upon Landing Attacks",
        "Stamina Recovery upon Landing Attacks +1",
        "Critical Hit Boosts Stamina Recovery Speed",
        "Critical Hit Boosts Stamina Recovery Speed +1",
    ]),

    ("Actions", [
        "Critical Hits Earn Runes",
        "Switching Weapons Adds an Affinity Attack",
        "Attacks Inflict Rot when Damage is Taken",
        "Draw enemy attention while guarding",
        "Gesture \"Crossed Legs\" Builds Up Madness",
        "Occasionally Nullify Attacks When Damage Negation is Lowered",
        "Attack power up when facing poison-afflicted enemy",
        "Attack power up when facing poison-afflicted enemy +1",
        "Attack power up when facing poison-afflicted enemy +2",
        "Attack power up when facing scarlet rot-afflicted enemy",
        "Attack power up when facing scarlet rot-afflicted enemy +1",
        "Attack power up when facing scarlet rot-afflicted enemy +2",
        "Attack power up when facing frostbite-afflicted enemy",
        "Attack power up when facing frostbite-afflicted enemy +1",
        "Attack power up when facing frostbite-afflicted enemy +2",
        "Poison & Rot in Vicinity Increases Attack Power",
        "Frostbite in Vicinity Conceals Self",
        "Sleep in Vicinity Improves Attack Power",
        "Sleep in Vicinity Improves Attack Power +1",
        "Madness in Vicinity Improves Attack Power",
        "Madness in Vicinity Improves Attack Power +1",
    ]),

    ("Environment", [
        "Treasure marked upon map",
        "Rune discount for shop purchases while on expedition",
        "Huge rune discount for shop purchases while on expedition",
    ]),

    ("Team Members", [
        "Increased rune acquisition for self and allies",
        "Raised stamina recovery for nearby allies, but not for self",
        "Flask Also Heals Allies",
        "Defeating enemies restores HP for allies but not for self",
        "Items confer effect to all nearby allies",
    ]),

    ("Character – Wylder", [
        "[Wylder] Art gauge greatly filled when ability is activated",
        "[Wylder] Standard attacks enhanced with fiery follow-ups when using Character Skill (greatsword only)",
        "[Wylder] +1 additional Character Skill use",
        "[Wylder] Art activation spreads fire in area",
        "[Wylder] Improved Mind, Reduced Vigor",
        "[Wylder] Improved Intelligence and Faith, Reduced Strength and Dexterity",
        "[Wylder] Character Skill inflicts Blood Loss",
    ]),

    ("Character – Guardian", [
        "[Guardian] Successful guards send out shockwaves while ability is active",
        "[Guardian] Increased duration for Character Skill",
        "[Guardian] Slowly restores nearby allies' HP while Art is active",
        "[Guardian] Creates whirlwind when charging halberd attacks",
        "[Guardian] Improved Strength and Dexterity, Reduced Vigor",
        "[Guardian] Improved Mind and Faith, Reduced Vigor",
        "[Guardian] Character Skill Boosts Damage Negation of Nearby Allies",
    ]),

    ("Character – Ironeye", [
        "[Ironeye] +1 additional Character Skill use",
        "[Ironeye] Art Charge Activation Adds Poison Effect",
        "[Ironeye] Boosts thrusting counterattacks after executing Art",
        "[Ironeye] Extends duration of weak point",
        "[Ironeye] Improved Vigor and Strength, Reduced Dexterity",
        "[Ironeye] Improved Arcane, Reduced Dexterity",
        "[Ironeye] Character Skill Inflicts Heavy Poison Damage on Poisoned Enemies",
    ]),

    ("Character – Duchess", [
        "[Duchess] Improved Character Skill Attack Power",
        "[Duchess] Defeating enemies while Art is active ups attack power",
        "[Duchess] Reprise events upon nearby enemies by landing the final blow of a chain attack with dagger",
        "[Duchess] Become difficult to spot and silence footsteps after landing critical from behind",
        "[Duchess] Improved Vigor and Strength, Reduced Mind",
        "[Duchess] Improved Mind and Faith, Reduced Intelligence",
        "[Duchess] Use Character Skill for Brief Invulnerability",
    ]),

    ("Character – Raider", [
        "[Raider] Damage taken while using Character Skill",
        "[Raider] Duration of Ultimate Art extended",
        "Defeating enemies near Totem Stela restores HP",
        "Improved Poise Near Totem Stela",
        "[Raider] Improved Mind and Intelligence, Reduced Vigor and Endurance",
        "[Raider] Improved Arcane, Reduced Vigor",
        "[Raider] Hit With Character Skill to Reduce Enemy Attack Power",
    ]),

    ("Character – Revenant", [
        "[Revenant] Trigger ghostflame explosion during Ultimate Art activation",
        "[Revenant] Expend own HP to fully heal nearby allies when activating Art",
        "[Revenant] Strengthens family and allies when Ultimate Art is activated",
        "[Revenant] Power up while fighting alongside family",
        "[Revenant] Improved Vigor and Endurance, Reduced Mind",
        "[Revenant] Improved Strength, Reduced Faith",
        "[Revenant] Increased Max FP upon Ability Activation",
    ]),

    ("Character – Recluse", [
        "[Recluse] Suffer blood loss and increase attack power upon Art activation",
        "[Recluse] Activating Ultimate Art raises Max HP",
        "[Recluse] Collecting affinity residue activates Terra Magica",
        "[Recluse] Improved Vigor, Endurance, and Dexterity, Reduced Intelligence and Faith",
        "[Recluse] Improved Intelligence and Faith, Reduced Mind",
        "[Recluse] Collect Affinity Residues to Negate Affinity",
    ]),

    ("Character – Executor", [
        "[Executor] Character Skill Boosts Attack but Lowers Damage Negation While Attacking",
        "[Executor] While Character Skill is active, unlocking use of cursed sword restores HP",
        "[Executor] Roaring restores HP while Art is active",
        "[Executor] Improved Vigor and Endurance, Reduced Arcane",
        "[Executor] Improved Dexterity and Arcane, Reduced Vigor",
        "[Executor] Slowly Restore HP upon Ability Activation",
    ]),

    ("Character – Scholar", [
        "[Scholar] Prevent slowing of Character Skill progress",
        "[Scholar] Allies targeted by Character Skill gain boosted attack",
        "[Scholar] Earn runes for each additional specimen acquired with Character Skill",
        "[Scholar] Continuous damage inflicted on targets threaded by Ultimate Art",
        "[Scholar] Improved Mind, Reduced Vigor",
        "[Scholar] Improved Endurance and Dexterity, Reduced Intelligence and Arcane",
        "[Scholar] Reduced FP consumption when using Character Skill on self",
    ]),

    ("Character – Undertaker", [
        "[Undertaker] Activating Ultimate Art increases attack power",
        "[Undertaker] Contact with allies restores their HP while Ultimate Art is activated",
        "[Undertaker] Attack power increased by landing the final blow of a chain attack",
        "[Undertaker] Physical attacks boosted while assist effect from incantation is active for self",
        "[Undertaker] Improved Dexterity, Reduced Vigor and Faith",
        "[Undertaker] Improved Mind and Faith, Reduced Strength",
        "[Undertaker] Executing Art readies Character Skill",
    ]),

    ("Weapon – Dagger", [
        "Improved Dagger Attack Power",
        "HP Restoration upon Dagger Attacks",
        "FP Restoration upon Dagger Attacks",
        "Improved Attack Power with 3+ Daggers Equipped",
        "Dormant Power Helps Discover Daggers",
    ]),

    ("Weapon – Thrusting Sword", [
        "Improved Thrusting Sword Attack Power",
        "HP Restoration upon Thrusting Sword Attacks",
        "FP Restoration upon Thrusting Sword Attacks",
        "Improved Attack Power with 3+ Thrusting Swords Equipped",
        "Dormant Power Helps Discover Thrusting Swords",
    ]),

    ("Weapon – Heavy Thrusting Sword", [
        "Improved Heavy Thrusting Sword Attack Power",
        "HP Restoration upon Heavy Thrusting Sword Attacks",
        "FP Restoration upon Heavy Thrusting Sword Attacks",
        "Improved Attack Power with 3+ Heavy Thrusting Swords Equipped",
        "Dormant Power Helps Discover Heavy Thrusting Swords",
    ]),

    ("Weapon – Straight Sword", [
        "Improved Straight Sword Attack Power",
        "HP Restoration upon Straight Sword Attacks",
        "FP Restoration upon Straight Sword Attacks",
        "Improved Attack Power with 3+ Straight Swords Equipped",
        "Dormant Power Helps Discover Straight Swords",
    ]),

    ("Weapon – Greatsword", [
        "Improved Greatsword Attack Power",
        "HP Restoration upon Greatsword Attacks",
        "FP Restoration upon Greatsword Attacks",
        "Improved Attack Power with 3+ Greatswords Equipped",
        "Dormant Power Helps Discover Greatswords",
    ]),

    ("Weapon – Colossal Sword", [
        "Improved Colossal Sword Attack Power",
        "HP Restoration upon Colossal Sword Attacks",
        "FP Restoration upon Colossal Sword Attacks",
        "Improved Attack Power with 3+ Colossal Swords Equipped",
        "Dormant Power Helps Discover Colossal Swords",
    ]),

    ("Weapon – Curved Sword", [
        "Improved Curved Sword Attack Power",
        "HP Restoration upon Curved Sword Attacks",
        "FP Restoration upon Curved Sword Attacks",
        "Improved Attack Power with 3+ Curved Swords Equipped",
        "Dormant Power Helps Discover Curved Swords",
    ]),

    ("Weapon – Curved Greatsword", [
        "Improved Curved Greatsword Attack Power",
        "HP Restoration upon Curved Greatsword Attacks",
        "FP Restoration upon Curved Greatsword Attacks",
        "Improved Attack Power with 3+ Curved Greatswords Equipped",
        "Dormant Power Helps Discover Curved Greatswords",
    ]),

    ("Weapon – Katana", [
        "Improved Katana Attack Power",
        "HP Restoration upon Katana Attacks",
        "FP Restoration upon Katana Attacks",
        "Improved Attack Power with 3+ Katana Equipped",
        "Dormant Power Helps Discover Katana",
    ]),

    ("Weapon – Twinblade", [
        "Improved Twinblade Attack Power",
        "HP Restoration upon Twinblade Attacks",
        "FP Restoration upon Twinblade Attacks",
        "Improved Attack Power with 3+ Twinblades Equipped",
        "Dormant Power Helps Discover Twinblades",
    ]),

    ("Weapon – Axe", [
        "Improved Axe Attack Power",
        "HP Restoration upon Axe Attacks",
        "FP Restoration upon Axe Attacks",
        "Improved Attack Power with 3+ Axes Equipped",
        "Dormant Power Helps Discover Axes",
    ]),

    ("Weapon – Greataxe", [
        "Improved Greataxe Attack Power",
        "HP Restoration upon Greataxe Attacks",
        "FP Restoration upon Greataxe Attacks",
        "Improved Attack Power with 3+ Greataxes Equipped",
        "Dormant Power Helps Discover Greataxes",
    ]),

    ("Weapon – Hammer", [
        "Improved Hammer Attack Power",
        "HP Restoration upon Hammer Attacks",
        "FP Restoration upon Hammer Attacks",
        "Improved Attack Power with 3+ Hammers Equipped",
        "Dormant Power Helps Discover Hammers",
    ]),

    ("Weapon – Flail", [
        "Improved Flail Attack Power",
        "HP Restoration upon Flail Attacks",
        "FP Restoration upon Flail Attacks",
        "Improved Attack Power with 3+ Flails Equipped",
        "Dormant Power Helps Discover Flails",
    ]),

    ("Weapon – Great Hammer", [
        "Improved Great Hammer Attack Power",
        "HP Restoration upon Great Hammer Attacks",
        "FP Restoration upon Great Hammer Attacks",
        "Improved Attack Power with 3+ Great Hammers Equipped",
        "Dormant Power Helps Discover Great Hammers",
    ]),

    ("Weapon – Colossal Weapon", [
        "Improved Colossal Weapon Attack Power",
        "HP Restoration upon Colossal Weapon Attacks",
        "FP Restoration upon Colossal Weapon Attacks",
        "Improved Attack Power with 3+ Colossal Weapons Equipped",
        "Dormant Power Helps Discover Colossal Weapons",
    ]),

    ("Weapon – Spear", [
        "Improved Spear Attack Power",
        "HP Restoration upon Spear Attacks",
        "FP Restoration upon Spear Attacks",
        "Improved Attack Power with 3+ Spears Equipped",
        "Dormant Power Helps Discover Spears",
    ]),

    ("Weapon – Great Spear", [
        "Improved Great Spear Attack Power",
        "HP Restoration upon Great Spear Attacks",
        "FP Restoration upon Great Spear Attacks",
        "Improved Attack Power with 3+ Great Spears Equipped",
        "Dormant Power Helps Discover Great Spears",
    ]),

    ("Weapon – Halberd", [
        "Improved Halberd Attack Power",
        "HP Restoration upon Halberd Attacks",
        "FP Restoration upon Halberd Attacks",
        "Improved Attack Power with 3+ Halberds Equipped",
        "Dormant Power Helps Discover Halberds",
    ]),

    ("Weapon – Reaper", [
        "Improved Reaper Attack Power",
        "HP Restoration upon Reaper Attacks",
        "FP Restoration upon Reaper Attacks",
        "Improved Attack Power with 3+ Reapers Equipped",
        "Dormant Power Helps Discover Reapers",
    ]),

    ("Weapon – Whip", [
        "Improved Whip Attack Power",
        "HP Restoration upon Whip Attacks",
        "FP Restoration upon Whip Attacks",
        "Improved Attack Power with 3+ Whips Equipped",
        "Dormant Power Helps Discover Whips",
    ]),

    ("Weapon – Fist", [
        "Improved Fist Attack Power",
        "HP Restoration upon Fist Attacks",
        "FP Restoration upon Fist Attacks",
        "Improved Attack Power with 3+ Fists Equipped",
        "Dormant Power Helps Discover Fists",
    ]),

    ("Weapon – Claw", [
        "Improved Claw Attack Power",
        "HP Restoration upon Claw Attacks",
        "FP Restoration upon Claw Attacks",
        "Improved Attack Power with 3+ Claws Equipped",
        "Dormant Power Helps Discover Claws",
    ]),

    ("Weapon – Bow", [
        "Improved Bow Attack Power",
        "HP Restoration upon Bow Attacks",
        "FP Restoration upon Bow Attacks",
        "Improved Attack Power with 3+ Bows Equipped",
        "Dormant Power Helps Discover Bows",
    ]),

    ("Weapon – Greatbow", [
        "Dormant Power Helps Discover Greatbows",
    ]),

    ("Weapon – Crossbow", [
        "Dormant Power Helps Discover Crossbows",
    ]),

    ("Weapon – Ballista", [
        "Dormant Power Helps Discover Ballistas",
    ]),

    ("Shield – Small Shield", [
        "Max HP Up with 3+ Small Shields Equipped",
        "Dormant Power Helps Discover Small Shields",
    ]),

    ("Shield – Medium Shield", [
        "Max HP Up with 3+ Medium Shields Equipped",
        "Dormant Power Helps Discover Medium Shields",
    ]),

    ("Shield – Greatshield", [
        "Max HP Up with 3+ Greatshields Equipped",
        "Dormant Power Helps Discover Greatshields",
    ]),

    ("Catalyst – Glintstone Staff", [
        "Max FP Up with 3+ Staves Equipped",
        "Dormant Power Helps Discover Staves",
    ]),

    ("Catalyst – Sacred Seal", [
        "Max FP Up with 3+ Sacred Seals Equipped",
        "Dormant Power Helps Discover Sacred Seals",
    ]),

    ("Starting Item", [
        "Starlight Shards in possession at start of expedition",
        "Fire Pots in possession at start of expedition",
        "Magic Pots in possession at start of expedition",
        "Lightning Pots in possession at start of expedition",
        "Holy Water Pots in possession at start of expedition",
        "Poisonbone Darts in possession at start of expedition",
        "Crystal Darts in possession at start of expedition",
        "Throwing Daggers in possession at start of expedition",
        "Glintstone Scraps in possession at start of expedition",
        "Gravity Stone Chunks in possession at start of expedition",
        "Bewitching Branches in possession at start of expedition",
        "Spark Aromatic in possession at start of expedition",
        "Poison Spraymist in possession at start of expedition",
        "Ironjar Aromatic in possession at start of expedition",
        "Uplifting Aromatic in possession at start of expedition",
        "Acid Spraymist in possession at start of expedition",
        "Bloodboil Aromatic in possession at start of expedition",
        "Wraith Calling Bell in possession at start of expedition",
        "Fire Grease in possession at start of expedition",
        "Magic Grease in possession at start of expedition",
        "Lightning Grease in possession at start of expedition",
        "Holy Grease in possession at start of expedition",
        "Shield Grease in possession at start of expedition",
        "Small Pouch in possession at start of expedition",
        "Stonesword Key in possession at start of expedition",
    ]),

    ("Starting Item (Tear)", [
        "Crimson Crystal Tear in possession at start of expedition",
        "Crimsonspill Crystal Tear in possession at start of expedition",
        "Crimsonburst Crystal Tear in possession at start of expedition",
        "Cerulean Crystal Tear in possession at start of expedition",
        "Greenspill Crystal Tear in possession at start of expedition",
        "Greenburst Crystal Tear in possession at start of expedition",
        "Opaline Hardtear in possession at start of expedition",
        "Speckled Hardtear in possession at start of expedition",
        "Leaden Hardtear in possession at start of expedition",
        "Magic-Shrouding Cracked Tear in possession at start of expedition",
        "Flame-Shrouding Cracked Tear in possession at start of expedition",
        "Lightning-Shrouding Cracked Tear in possession at start of expedition",
        "Holy-Shrouding Cracked Tear in possession at start of expedition",
        "Stonebarb Cracked Tear in possession at start of expedition",
        "Spiked Cracked Tear in possession at start of expedition",
        "Thorny Cracked Tear in possession at start of expedition",
        "Twiggy Cracked Tear in possession at start of expedition",
        "Windy Crystal Tear in possession at start of expedition",
        "Crimson Bubbletear in possession at start of expedition",
        "Crimsonwhorl Bubbletear in possession at start of expedition",
        "Opaline Bubbletear in possession at start of expedition",
        "Cerulean Hidden Tear in possession at start of expedition",
        "Ruptured Crystal Tear in possession at start of expedition",
    ]),

    ("Starting Armaments (Skill)", [
        "Changes compatible armament's skill to Endure at start of expedition",
        "Changes compatible armament's skill to Quickstep at start of expedition",
        "Changes compatible armament's skill to Storm Stomp at start of expedition",
        "Changes compatible armament's skill to Determination at start of expedition",
        "Changes compatible armament's skill to Glintblade Phalanx at start of expedition",
        "Changes compatible armament's skill to Gravitas at start of expedition",
        "Changes compatible armament's skill to Flaming Strike at start of expedition",
        "Changes compatible armament's skill to Eruption at start of expedition",
        "Changes compatible armament's skill to Thunderbolt at start of expedition",
        "Changes compatible armament's skill to Lightning Slash at start of expedition",
        "Changes compatible armament's skill to Sacred Blade at start of expedition",
        "Changes compatible armament's skill to Prayerful Strike at start of expedition",
        "Changes compatible armament's skill to Poisonous Mist at start of expedition",
        "Changes compatible armament's skill to Poison Moth Flight at start of expedition",
        "Changes compatible armament's skill to Blood Blade at start of expedition",
        "Changes compatible armament's skill to Seppuku at start of expedition",
        "Changes compatible armament's skill to Chilling Mist at start of expedition",
        "Changes compatible armament's skill to Hoarfrost Stomp at start of expedition",
        "Changes compatible armament's skill to White Shadow's Lure at start of expedition",
        "Changes compatible armament's skill to Rain of Arrows at start of expedition",
    ]),

    ("Starting Armaments (Imbue)", [
        "Starting armament deals magic damage",
        "Starting armament deals fire damage",
        "Starting armament deals lightning damage",
        "Starting armament deals holy damage",
        "Starting armament inflicts poison",
        "Starting armament inflicts blood loss",
        "Starting armament inflicts frost",
    ]),

    ("Starting Armaments (Spell)", [
        "Changes compatible armament's sorcery to Magic Glintblade at start of expedition",
        "Changes compatible armament's sorcery to Carian Greatsword at start of expedition",
        "Changes compatible armament's sorcery to Night Shard at start of expedition",
        "Changes compatible armament's sorcery to Magma Shot at start of expedition",
        "Changes compatible armament's sorcery to Briars of Punishment at start of expedition",
        "Changes compatible armament's incantation to Wrath of Gold at start of expedition",
        "Changes compatible armament's incantation to Lightning Spear at start of expedition",
        "Changes compatible armament's incantation to O, Flame! at start of expedition",
        "Changes compatible armament's incantation to Beast Claw at start of expedition",
        "Changes compatible armament's incantation to Dragonfire at start of expedition",
    ]),

    ("Demerits (Attributes)", [
        "Reduced Vigor and Arcane",
        "Reduced Strength and Intelligence",
        "Reduced Dexterity and Faith",
        "Reduced Intelligence and Dexterity",
        "Reduced Faith and Strength",
        "Reduced Rune Acquisition",
    ]),

    ("Demerits (Damage Negation)", [
        "Continuous HP Loss",
        "All Resistances Down",
        "Reduced Damage Negation for Flask Usages",
        "Reduced Damage Negation After Evading",
        "Repeated Evasions Lower Damage Negation",
        "Taking Damage Causes Poison Buildup",
        "Taking Damage Causes Rot Buildup",
        "Taking Damage Causes Blood Loss Buildup",
        "Taking Damage Causes Frost Buildup",
        "Taking Damage Causes Sleep Buildup",
        "Taking Damage Causes Madness Buildup",
        "Taking Damage Causes Death Buildup",
    ]),

    ("Demerits (Action)", [
        "Reduced Flask HP Restoration",
        "Ultimate Art Charging Impaired",
        "Lower Attack When Below Max HP",
        "Poison Buildup When Below Max HP",
        "Rot Buildup When Below Max HP",
        "Near Death Reduces Max HP",
    ]),
])


# ── Derived flat lists ────────────────────────────────────────────────────── #

_CURSE_CATS = {"Demerits (Attributes)", "Demerits (Damage Negation)", "Demerits (Action)"}

_seen: set = set()
ALL_PASSIVES: list = []
DEBUFFS: list = []

for _cat, _entries in CATEGORIES.items():
    for _entry in _entries:
        if _entry not in _seen:
            _seen.add(_entry)
            if _cat in _CURSE_CATS:
                DEBUFFS.append(_entry)
            else:
                ALL_PASSIVES.append(_entry)

# Sorted for display (alphabetical)
ALL_PASSIVES_SORTED: list = sorted(ALL_PASSIVES, key=str.casefold)

# Curses only — the Demerit categories that appear as negative effects on relics
ALL_CURSES: list = sorted(
    [p for cat, items in CATEGORIES.items() if "Demerit" in cat for p in items],
    key=str.casefold,
)


# ── Compatibility / Stackability Rules ───────────────────────────────────── #
# Passives in the same exclusive group CANNOT appear on the same relic.
# Passives NOT listed here have no mutual restriction.

_COMPAT_EXCLUSIVE_GROUPS: list[list[str]] = [

    # ── Group 0 – Attack Power (compat 100 — all mutually exclusive) ──────
    # Elemental / affinity attack power
    [
        "Physical Attack Up",
        "Physical Attack Up +1",
        "Physical Attack Up +2",
        "Physical Attack Up +3",
        "Physical Attack Up +4",
        "Improved Affinity Attack Power",
        "Improved Affinity Attack Power +1",
        "Improved Affinity Attack Power +2",
        "Magic Attack Power Up",
        "Magic Attack Power Up +1",
        "Magic Attack Power Up +2",
        "Magic Attack Power Up +3",
        "Magic Attack Power Up +4",
        "Fire Attack Power Up",
        "Fire Attack Power Up +1",
        "Fire Attack Power Up +2",
        "Fire Attack Power Up +3",
        "Fire Attack Power Up +4",
        "Lightning Attack Power Up",
        "Lightning Attack Power Up +1",
        "Lightning Attack Power Up +2",
        "Lightning Attack Power Up +3",
        "Lightning Attack Power Up +4",
        "Holy Attack Power Up",
        "Holy Attack Power Up +1",
        "Holy Attack Power Up +2",
        "Holy Attack Power Up +3",
        "Holy Attack Power Up +4",
        # Broad spell type boosters (NOT school-specific — those are Group 7)
        "Improved Sorceries",
        "Improved Sorceries +1",
        "Improved Sorceries +2",
        "Improved Incantations",
        "Improved Incantations +1",
        "Improved Incantations +2",
        # Melee / combat technique boosters
        "Improved Guard Counters",
        "Improved Guard Counters +1",
        "Improved Guard Counters +2",
        "Improved Initial Standard Attack",
        "Improved Critical Hits",
        "Improved Roar & Breath Attacks",
        "Guard counter is given a boost based on current HP",
        "Improved Stance-Breaking when Two-Handing",
        "Improved Stance-Breaking when Wielding Two Armaments",
        # Conditional attack boosts
        "Madness in Vicinity Improves Attack Power",
        "Madness in Vicinity Improves Attack Power +1",
        "Sleep in Vicinity Improves Attack Power",
        "Sleep in Vicinity Improves Attack Power +1",
        "Physical attack power increases after using grease items",
        "Physical attack power increases after using grease items +1",
        "Physical attack power increases after using grease items +2",
        "Taking attacks improves attack power",
        "Switching Weapons Boosts Attack Power",
        "Attack power increased for each evergaol prisoner defeated",
        "Attack power increased for each Night Invader defeated",
        # Weapon-class specific attack power (one per relic)
        "Improved Dagger Attack Power",
        "Improved Straight Sword Attack Power",
        "Improved Greatsword Attack Power",
        "Improved Colossal Sword Attack Power",
        "Improved Curved Sword Attack Power",
        "Improved Curved Greatsword Attack Power",
        "Improved Katana Attack Power",
        "Improved Twinblade Attack Power",
        "Improved Thrusting Sword Attack Power",
        "Improved Heavy Thrusting Sword Attack Power",
        "Improved Axe Attack Power",
        "Improved Greataxe Attack Power",
        "Improved Hammer Attack Power",
        "Improved Great Hammer Attack Power",
        "Improved Flail Attack Power",
        "Improved Spear Attack Power",
        "Improved Great Spear Attack Power",
        "Improved Halberd Attack Power",
        "Improved Reaper Attack Power",
        "Improved Fist Attack Power",
        "Improved Claw Attack Power",
        "Improved Whip Attack Power",
        "Improved Colossal Weapon Attack Power",
        "Improved Bow Attack Power",
        # Weapon-class 3+ equipped attack power (one per relic)
        "Improved Attack Power with 3+ Daggers Equipped",
        "Improved Attack Power with 3+ Straight Swords Equipped",
        "Improved Attack Power with 3+ Greatswords Equipped",
        "Improved Attack Power with 3+ Colossal Swords Equipped",
        "Improved Attack Power with 3+ Curved Swords Equipped",
        "Improved Attack Power with 3+ Curved Greatswords Equipped",
        "Improved Attack Power with 3+ Katana Equipped",
        "Improved Attack Power with 3+ Twinblades Equipped",
        "Improved Attack Power with 3+ Thrusting Swords Equipped",
        "Improved Attack Power with 3+ Heavy Thrusting Swords Equipped",
        "Improved Attack Power with 3+ Axes Equipped",
        "Improved Attack Power with 3+ Greataxes Equipped",
        "Improved Attack Power with 3+ Hammers Equipped",
        "Improved Attack Power with 3+ Great Hammers Equipped",
        "Improved Attack Power with 3+ Flails Equipped",
        "Improved Attack Power with 3+ Spears Equipped",
        "Improved Attack Power with 3+ Great Spears Equipped",
        "Improved Attack Power with 3+ Halberds Equipped",
        "Improved Attack Power with 3+ Reapers Equipped",
        "Improved Attack Power with 3+ Fists Equipped",
        "Improved Attack Power with 3+ Claws Equipped",
        "Improved Attack Power with 3+ Whips Equipped",
        "Improved Attack Power with 3+ Colossal Weapons Equipped",
        "Improved Attack Power with 3+ Bows Equipped",
    ],

    # ── Group 1 – Character-Specific ─────────────────────────────────────
    [
        p
        for cat, passives in CATEGORIES.items()
        if cat.startswith("Character –")
        for p in passives
    ],

    # ── Group 2 – Aromatics & Spraymists ──────────────────────────────────
    [
        "Spark Aromatic in possession at start of expedition",
        "Ironjar Aromatic in possession at start of expedition",
        "Uplifting Aromatic in possession at start of expedition",
        "Bloodboil Aromatic in possession at start of expedition",
        "Acid Spraymist in possession at start of expedition",
        "Poison Spraymist in possession at start of expedition",
    ],

    # ── Group 3 – Tears ───────────────────────────────────────────────────
    list(CATEGORIES["Starting Item (Tear)"]),

    # ── Group 4 – Dormant Powers ──────────────────────────────────────────
    [p for cat, entries in CATEGORIES.items()
     if cat.startswith("Weapon –") or cat.startswith("Shield –") or cat.startswith("Catalyst –")
     for p in entries if p.startswith("Dormant Power")],

    # ── Group 5 – Starting Armament Skill + Spell Changes (compat 300) ───
    # Skills and spell changes share compat 300 — one per relic.
    [
        *CATEGORIES["Starting Armaments (Skill)"],
        *CATEGORIES["Starting Armaments (Spell)"],
    ],

    # ── Group 6 – Starting Armament Imbue Changes (compat 200) ───────────
    # Imbues (deals X damage / inflicts Y) are separate from skill/spell.
    list(CATEGORIES["Starting Armaments (Imbue)"]),

    # ── Group 7 – School-Specific Spell Boosters (compat 800) ────────────
    # One school booster per relic — sorcery and incantation schools compete.
    # CAN coexist with one Group 0 attack booster (different compat category).
    [p for p in CATEGORIES["Sorceries & Incantations"]
     if p != "Extended Spell Duration"],

    # ── Group 8 – HP Restoration upon [Weapon] Attacks ───────────────────
    [
        "HP Restoration upon Dagger Attacks",
        "HP Restoration upon Straight Sword Attacks",
        "HP Restoration upon Greatsword Attacks",
        "HP Restoration upon Colossal Sword Attacks",
        "HP Restoration upon Curved Sword Attacks",
        "HP Restoration upon Curved Greatsword Attacks",
        "HP Restoration upon Katana Attacks",
        "HP Restoration upon Twinblade Attacks",
        "HP Restoration upon Thrusting Sword Attacks",
        "HP Restoration upon Heavy Thrusting Sword Attacks",
        "HP Restoration upon Axe Attacks",
        "HP Restoration upon Greataxe Attacks",
        "HP Restoration upon Hammer Attacks",
        "HP Restoration upon Great Hammer Attacks",
        "HP Restoration upon Flail Attacks",
        "HP Restoration upon Spear Attacks",
        "HP Restoration upon Great Spear Attacks",
        "HP Restoration upon Halberd Attacks",
        "HP Restoration upon Reaper Attacks",
        "HP Restoration upon Fist Attacks",
        "HP Restoration upon Claw Attacks",
        "HP Restoration upon Whip Attacks",
        "HP Restoration upon Colossal Weapon Attacks",
        "HP Restoration upon Bow Attacks",
    ],

    # ── Group 9 – FP Restoration upon [Weapon] Attacks ───────────────────
    [
        "FP Restoration upon Dagger Attacks",
        "FP Restoration upon Straight Sword Attacks",
        "FP Restoration upon Greatsword Attacks",
        "FP Restoration upon Colossal Sword Attacks",
        "FP Restoration upon Curved Sword Attacks",
        "FP Restoration upon Curved Greatsword Attacks",
        "FP Restoration upon Katana Attacks",
        "FP Restoration upon Twinblade Attacks",
        "FP Restoration upon Thrusting Sword Attacks",
        "FP Restoration upon Heavy Thrusting Sword Attacks",
        "FP Restoration upon Axe Attacks",
        "FP Restoration upon Greataxe Attacks",
        "FP Restoration upon Hammer Attacks",
        "FP Restoration upon Great Hammer Attacks",
        "FP Restoration upon Flail Attacks",
        "FP Restoration upon Spear Attacks",
        "FP Restoration upon Great Spear Attacks",
        "FP Restoration upon Halberd Attacks",
        "FP Restoration upon Reaper Attacks",
        "FP Restoration upon Fist Attacks",
        "FP Restoration upon Claw Attacks",
        "FP Restoration upon Whip Attacks",
        "FP Restoration upon Colossal Weapon Attacks",
        "FP Restoration upon Bow Attacks",
    ],

    # ── Group 10 – Vigor / Max HP ─────────────────────────────────────────
    [
        "Vigor +1",
        "Vigor +2",
        "Vigor +3",
        "Increased Maximum HP",
    ],

    # ── Group 11 – Mind / Max FP ──────────────────────────────────────────
    [
        "Mind +1",
        "Mind +2",
        "Mind +3",
        "Increased Maximum FP",
    ],

    # ── Group 12 – Endurance / Max Stamina ────────────────────────────────
    [
        "Endurance +1",
        "Endurance +2",
        "Endurance +3",
        "Increased Maximum Stamina",
    ],

    # ── Group 13 – Strength ───────────────────────────────────────────────
    ["Strength +1", "Strength +2", "Strength +3"],

    # ── Group 14 – Dexterity ──────────────────────────────────────────────
    ["Dexterity +1", "Dexterity +2", "Dexterity +3"],

    # ── Group 15 – Intelligence ───────────────────────────────────────────
    ["Intelligence +1", "Intelligence +2", "Intelligence +3"],

    # ── Group 16 – Faith ──────────────────────────────────────────────────
    ["Faith +1", "Faith +2", "Faith +3"],

    # ── Group 17 – Arcane ─────────────────────────────────────────────────
    ["Arcane +1", "Arcane +2", "Arcane +3"],

    # ── Group 18 – Poise ──────────────────────────────────────────────────
    ["Poise +1", "Poise +2", "Poise +3"],

    # ── Group 19 – Max HP Up with 3+ Shields Equipped ─────────────────────
    [
        "Max HP Up with 3+ Greatshields Equipped",
        "Max HP Up with 3+ Medium Shields Equipped",
        "Max HP Up with 3+ Small Shields Equipped",
    ],

    # ── Group 20 – Max FP Up with 3+ Catalysts Equipped ──────────────────
    [
        "Max FP Up with 3+ Staves Equipped",
        "Max FP Up with 3+ Sacred Seals Equipped",
    ],

    # ── Group 21 – Skill Cooldown Reduction ───────────────────────────────
    [
        "Character Skill Cooldown Reduction",
        "Character Skill Cooldown Reduction +1",
        "Character Skill Cooldown Reduction +2",
        "Character Skill Cooldown Reduction +3",
    ],

    # ── Group 22 – Ultimate Art Auto Charge ───────────────────────────────
    [
        "Ultimate Art Auto Charge",
        "Ultimate Art Auto Charge +1",
        "Ultimate Art Auto Charge +2",
        "Ultimate Art Auto Charge +3",
    ],

    # ── Group 23 – Improved Affinity Damage Negation ──────────────────────
    [
        "Improved Affinity Damage Negation",
        "Improved Affinity Damage Negation +1",
        "Improved Affinity Damage Negation +2",
    ],
]

# Flat lookup: passive_name → group index
COMPAT_GROUPS: dict[str, int] = {}
for _gid, _group in enumerate(_COMPAT_EXCLUSIVE_GROUPS):
    for _passive in _group:
        COMPAT_GROUPS[_passive] = _gid

# Human-readable names for each group (used in UI warnings)
COMPAT_GROUP_NAMES: dict[int, str] = {
    0: "Attack Power",
    1: "Character-Specific",
    2: "Aromatics",
    3: "Tears",
    4: "Dormant Power",
    5: "Starting Armament Skill/Spell",
    6: "Starting Armament Imbue",
    7: "School-Specific Spell Booster",
    8: "HP on Weapon Attack",
    9: "FP on Weapon Attack",
    10: "Vigor / Max HP",
    11: "Mind / Max FP",
    12: "Endurance / Max Stamina",
    13: "Strength",
    14: "Dexterity",
    15: "Intelligence",
    16: "Faith",
    17: "Arcane",
    18: "Poise",
    19: "Max HP (Shields)",
    20: "Max FP (Catalysts)",
    21: "Skill Cooldown",
    22: "Art Auto Charge",
    23: "Affinity Damage Negation",
}


def get_compat_violations(passives: list) -> list[tuple[int, int, str]]:
    """
    Check a list of passives (str or None) for compatibility violations.
    Returns list of (slot_i, slot_j, group_name) for each conflicting pair.
    """
    filled = [(i, p) for i, p in enumerate(passives) if p]
    violations = []
    for a, (i, pi) in enumerate(filled):
        for j, pj in filled[a + 1:]:
            gi = COMPAT_GROUPS.get(pi)
            gj = COMPAT_GROUPS.get(pj)
            if gi is not None and gi == gj:
                name = COMPAT_GROUP_NAMES.get(gi, f"Group {gi}")
                violations.append((i, j, name))
    return violations


# ── Passive probability estimation ─────────────────────────────────────────── #
# Rough estimates based on category pool sizes and equal-weight assumptions.
# Actual probabilities require pool weight data mined from AttachEffectTableParam.
# Use as relative comparisons; absolute values are approximate.

# Passives only available on Deep of Night relics (not normal shop buys)
_DEEP_ONLY_PASSIVES: frozenset = frozenset([
    "Physical Attack Up +3", "Physical Attack Up +4",
    "Magic Attack Power Up +3", "Magic Attack Power Up +4",
    "Fire Attack Power Up +3", "Fire Attack Power Up +4",
    "Lightning Attack Power Up +3", "Lightning Attack Power Up +4",
    "Holy Attack Power Up +3", "Holy Attack Power Up +4",
    "Improved Affinity Attack Power",
    "Improved Affinity Attack Power +1",
    "Improved Affinity Attack Power +2",
    "Improved Sorceries", "Improved Sorceries +1", "Improved Sorceries +2",
    "Improved Incantations", "Improved Incantations +1", "Improved Incantations +2",
    "Increased Maximum HP", "Increased Maximum FP", "Increased Maximum Stamina",
    "Reduced FP Consumption", "Improved Flask HP Restoration",
])

# School-specific spell boosters (Cat 4 / compat 800, 14 passives total)
_SCHOOL_BOOSTERS: frozenset = frozenset(
    p for p in CATEGORIES.get("Sorceries & Incantations", [])
    if p != "Extended Spell Duration"
)

_STAT_BASES: tuple = (
    "Vigor", "Mind", "Endurance", "Strength",
    "Dexterity", "Intelligence", "Faith", "Arcane", "Poise",
)


def estimate_passive_prob(passive: str | None) -> float | None:
    """
    P(passive appears on a Grand normal relic) — best estimate for 3-passive hunters.
    Returns float in (0,1) or None if passive is None.

    Uses actual pool weight data from database/pool_weights.py (AttachEffectTableParam).
    Grand probability: 1 - P(absent from all 3 slots), averaged over group A/B (50/50).
    Deep-only passives use the deep relic probability instead.
    Falls back to category-based estimates for passives not found in pool data.
    """
    if passive is None:
        return None
    try:
        from database.pool_weights import grand_prob, deep_prob
        # Try normal relic tables first (Grand = best estimate)
        p = grand_prob(passive)
        if p is not None:
            return p
        # Try deep relic tables (deep-only passives)
        p = deep_prob(passive)
        if p is not None:
            return p
    except ImportError:
        pass

    # Fallback: category-based rough estimates (used if pool_weights not available)
    if passive in _DEEP_ONLY_PASSIVES:
        return 0.003
    if passive.startswith("Dormant Power"):
        return 0.002
    if passive in _SCHOOL_BOOSTERS:
        return 0.010
    for base in _STAT_BASES:
        if passive.startswith(base + " +"):
            return 0.015
    if passive.startswith("["):
        return 0.005
    _EL = ("Physical Attack Up", "Magic Attack Power Up", "Fire Attack Power Up",
           "Lightning Attack Power Up", "Holy Attack Power Up")
    if any(passive == e or passive.startswith(e + " +") for e in _EL):
        return 0.004
    if ("Attack Power" in passive and ("Improved " in passive or "3+" in passive)
            and "Sorceries" not in passive and "Incantations" not in passive
            and "Affinity" not in passive):
        return 0.003
    return 0.005


def estimate_passive_prob_by_size(passive: str | None) -> dict[str, float | None]:
    """
    Return per-size probabilities for a passive on normal relics.
    Keys: "delicate", "polished", "grand".  Values: float or None if not in that pool.
    """
    if passive is None:
        return {"delicate": None, "polished": None, "grand": None}
    try:
        from database.pool_weights import delicate_prob, polished_prob, grand_prob
        return {
            "delicate": delicate_prob(passive),
            "polished": polished_prob(passive),
            "grand":    grand_prob(passive),
        }
    except ImportError:
        p = estimate_passive_prob(passive)
        return {"delicate": p, "polished": p, "grand": p}


# ── UI category groupings (displayed in the criteria builder) ─────────────── #

from collections import OrderedDict as _OD

_UI_CAT_MAP = {
    "Attributes":              "Attributes",
    "Attack Power":            "Offensive",
    "Character Skills & Art":  "Offensive",
    "Damage Negation":         "Defensive",
    "Status Ailment Resistances": "Defensive",
    "Restoration":             "Defensive",
    "Actions":                 "Utility",
    "Environment":             "Utility",
    "Team Members":            "Utility",
    "Sorceries & Incantations": None,   # split below
    "Starting Item":           "Starting Items",
    "Starting Item (Tear)":    "Starting Items",
    "Starting Armaments (Skill)": "Armament Skills",
    "Starting Armaments (Imbue)": "Armament Skills",
    "Starting Armaments (Spell)": "Armament Skills",
    "Demerits (Attributes)":   None,    # skip (curses, not passives)
    "Demerits (Damage Negation)": None,
    "Demerits (Action)":       None,
}

# Character and Weapon categories are handled by prefix matching below.

_UI_ORDER = [
    "Offensive", "Defensive", "Attributes", "Utility",
    "Sorceries", "Incantations",
    "Armament Skills", "Starting Items",
    "Character Specific", "Dormant Powers", "Weapon Specific", "Others",
]

UI_CATEGORIES: "OrderedDict[str, list[str]]" = _OD((k, []) for k in _UI_ORDER)

_placed: set = set()

for _cat, _entries in CATEGORIES.items():
    # Skip curse categories (they are not passives)
    if _cat in _CURSE_CATS:
        continue

    # Character-specific
    if _cat.startswith("Character –"):
        for _p in _entries:
            if _p not in _placed and _p in ALL_PASSIVES:
                UI_CATEGORIES["Character Specific"].append(_p)
                _placed.add(_p)
        continue

    # Weapon / Shield / Catalyst → split into Dormant Powers vs Weapon Specific
    if _cat.startswith(("Weapon –", "Shield –", "Catalyst –")):
        for _p in _entries:
            if _p not in _placed and _p in ALL_PASSIVES:
                if _p.startswith("Dormant Power"):
                    UI_CATEGORIES["Dormant Powers"].append(_p)
                else:
                    UI_CATEGORIES["Weapon Specific"].append(_p)
                _placed.add(_p)
        continue

    # Sorceries & Incantations — split on keyword
    if _cat == "Sorceries & Incantations":
        for _p in _entries:
            if _p not in _placed and _p in ALL_PASSIVES:
                if "Incantation" in _p:
                    UI_CATEGORIES["Incantations"].append(_p)
                else:
                    UI_CATEGORIES["Sorceries"].append(_p)
                _placed.add(_p)
        continue

    # Mapped categories
    _ui = _UI_CAT_MAP.get(_cat)
    if _ui is None:
        continue
    for _p in _entries:
        if _p not in _placed and _p in ALL_PASSIVES:
            UI_CATEGORIES[_ui].append(_p)
            _placed.add(_p)

# Everything not placed → Others
for _p in ALL_PASSIVES:
    if _p not in _placed:
        UI_CATEGORIES["Others"].append(_p)

# Remove empty UI categories
UI_CATEGORIES = _OD((k, v) for k, v in UI_CATEGORIES.items() if v)


def build_mode_categories(pool: "frozenset[str]") -> "OrderedDict[str, list[str]]":
    """Build UI category dict containing only passives present in the given pool.

    Categories are organized by compat groups (exclusive = picking one blocks the
    rest) and sub-divided independent passives for easy browsing.

    Each category name indicates whether it's exclusive or stackable.
    """
    _CURSE = frozenset({"Demerits (Attributes)", "Demerits (Damage Negation)", "Demerits (Action)"})

    # Step 1: separate pooled passives into compat-grouped vs independent
    grouped = {}     # compat_group_id -> list of passives
    independent = [] # passives with no compat group

    for cat, entries in CATEGORIES.items():
        if cat in _CURSE:
            continue
        for p in entries:
            if p not in pool:
                continue
            g = COMPAT_GROUPS.get(p)
            if g is not None:
                if g not in grouped:
                    grouped[g] = []
                grouped[g].append(p)
            else:
                independent.append(p)

    # Deduplicate (a passive can appear in multiple CATEGORIES entries)
    for g in grouped:
        grouped[g] = sorted(set(grouped[g]), key=str.casefold)
    independent = sorted(set(independent), key=str.casefold)

    # Step 2: name the compat groups
    _GROUP_NAMES = {
        0: "Attack Power & Combat Arts (exclusive)",
        1: "Character Skills (exclusive)",
        2: "Aromatics & Consumables (exclusive)",
        3: "Crystal Tears (exclusive)",
        4: "Dormant Powers (exclusive)",
        5: "Starting Armament Skills (exclusive)",
        6: "Starting Armament Spells & Imbues (exclusive)",
        7: "Sorcery & Incantation Schools (exclusive)",
    }

    result = _OD()

    # Add exclusive groups in a fixed order
    for gid in sorted(_GROUP_NAMES.keys()):
        if gid in grouped:
            result[_GROUP_NAMES[gid]] = grouped[gid]

    # Step 3: sub-divide independent passives by their CATEGORIES category
    # Build passive -> internal category map
    _cat_map = {}
    for cat, entries in CATEGORIES.items():
        if cat in _CURSE:
            continue
        for p in entries:
            if p not in _cat_map:
                _cat_map[p] = cat

    # Sub-category mapping for independent passives
    _INDEP_NAMES = {
        "Attributes":               "Attributes & Stats (stackable)",
        "Attack Power":             "Attack Power Bonuses (stackable)",
        "Character Skills & Art":   "Art Gauge & Skills (stackable)",
        "Damage Negation":          "Damage Negation (stackable)",
        "Status Ailment Resistances": "Status Resistances (stackable)",
        "Restoration":              "HP / FP / Stamina Restoration (stackable)",
        "Actions":                  "Conditional Boosts (stackable)",
        "Environment":              "Exploration & Runes (stackable)",
        "Team Members":             "Team Support (stackable)",
        "Starting Item":            "Starting Items (stackable)",
    }

    indep_buckets = _OD()
    weapon_bucket = []
    uncategorized = []

    for p in independent:
        cat = _cat_map.get(p, "")
        if cat.startswith(("Weapon", "Shield", "Catalyst")):
            weapon_bucket.append(p)
        elif cat in _INDEP_NAMES:
            key = _INDEP_NAMES[cat]
            if key not in indep_buckets:
                indep_buckets[key] = []
            indep_buckets[key].append(p)
        else:
            uncategorized.append(p)

    # Add independent sub-categories
    for key, passives in indep_buckets.items():
        if passives:
            result[key] = sorted(passives, key=str.casefold)

    if weapon_bucket:
        result["Weapon HP/FP/Atk Bonuses (stackable)"] = sorted(weapon_bucket, key=str.casefold)

    if uncategorized:
        result["Other (stackable)"] = sorted(uncategorized, key=str.casefold)

    return result
