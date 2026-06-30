try:
    from .base import JobState
    from .sam import SamJobState
    from .rpr import RprJobState
    from .nin import NinJobState
    from .pct import PctJobState
    from .blm import BlmJobState
    from .mnk import MnkJobState
    from .drg import DrgJobState
    from .vpr import VprJobState
    from .brd import BrdJobState
    from .mch import MchJobState
    from .dnc import DncJobState
    from .smn import SmnJobState
    from .rdm import RdmJobState
except ImportError:
    from base import JobState
    from sam import SamJobState
    from rpr import RprJobState
    from nin import NinJobState
    from pct import PctJobState
    from blm import BlmJobState
    from mnk import MnkJobState
    from drg import DrgJobState
    from vpr import VprJobState
    from brd import BrdJobState
    from mch import MchJobState
    from dnc import DncJobState
    from smn import SmnJobState
    from rdm import RdmJobState


MODELED_JOB_STATE_SKILLS = {
    "SAM": {
        "Gyofu", "Jinpu", "Shifu", "Gekko", "Kasha", "Yukikaze",
        "Fuko", "Mangetsu", "Oka", "Enpi", "Higanbana", "Tenka Goken",
        "Midare Setsugekka", "Tendo Goken", "Tendo Setsugekka",
        "Kaeshi: Goken", "Kaeshi: Setsugekka", "Tendo Kaeshi Goken",
        "Tendo Kaeshi Setsugekka", "Ogi Namikiri", "Kaeshi: Namikiri",
        "Meikyo Shisui", "Meditate", "Toggle buff: Meditate", "Shoha",
        "Hagakure", "Ikishoten", "Zanshin", "Hissatsu: Shinten",
        "Hissatsu: Kyuten", "Hissatsu: Gyoten", "Hissatsu: Yaten",
        "Hissatsu: Senei", "Hissatsu: Guren", "Pop Tengentsu",
    },
    "NIN": {
        "Spinning Edge", "Gust Slash", "Aeolian Edge", "Armor Crush",
        "Throwing Dagger", "Death Blossom", "Hakke Mujinsatsu",
        "Ten", "Chi", "Jin", "Fuma Shuriken", "Fuma Shuriken (Ten)",
        "Fuma Shuriken (Chi)", "Fuma Shuriken (Jin)", "Katon", "Katon (Ten)",
        "Raiton", "Raiton (Chi)", "Hyoton", "Hyoton (Jin)", "Huton",
        "Huton (Ten)", "Doton", "Doton (Chi)", "Suiton", "Suiton (Jin)",
        "Goka Mekkyaku", "Hyosho Ranryu", "Kassatsu", "Bunshin",
        "Ten Chi Jin", "Meisui", "Hide", "Dokumori", "Kunai's Bane",
        "Tenri Jindo", "Bhavacakra", "Hellfrog Medium", "Deathfrog Medium",
        "Zesho Meppo", "Dream Within a Dream", "Phantom Kamaitachi",
        "Forked Raiju", "Fleeting Raiju", "Hollow Nozuchi", "True North",
    },
    "RPR": {
        "Arcane Circle", "Arcane Crest", "Pop Arcane Crest",
        "Blood Stalk", "Unveiled Gibbet", "Unveiled Gallows", "Gluttony",
        "Enshroud", "Void Reaping", "Cross Reaping", "Grim Reaping",
        "Lemure's Slice", "Lemure's Scythe", "Sacrificium", "Communio",
        "Perfectio", "Plentiful Harvest", "Harvest Moon", "Soulsow",
        "Shadow of Death", "Whorl of Death", "Slice", "Waxing Slice",
        "Infernal Slice", "Spinning Scythe", "Nightmare Scythe", "Harpe",
        "Soul Slice", "Soul Scythe", "Gibbet", "Gallows", "Guillotine",
        "Executioner's Gibbet", "Executioner's Gallows",
        "Executioner's Guillotine", "Hell's Ingress", "Hell's Egress",
        "Regress", "+10 Soul Gauge",
    },
    "PCT": {
        "Fire in Red", "Aero in Green", "Water in Blue",
        "Fire II in Red", "Aero II in Green", "Water II in Blue",
        "Blizzard in Cyan", "Stone in Yellow", "Thunder in Magenta",
        "Blizzard II in Cyan", "Stone II in Yellow", "Thunder II in Magenta",
        "Holy in White", "Comet in Black",
        "Creature Motif", "Pom Motif", "Wing Motif", "Claw Motif", "Maw Motif",
        "Weapon Motif", "Hammer Motif", "Landscape Motif", "Starry Sky Motif",
        "Pom Muse", "Winged Muse", "Clawed Muse", "Fanged Muse", "Striking Muse",
        "Starry Muse", "Subtractive Palette", "Hyperphantasia", "Rainbow Drip",
        "Hammer Stamp", "Hammer Brush", "Polishing Hammer", "Mog of the Ages",
        "Retribution of the Madeen", "Star Prism", "Swiftcast",
    },
    "BLM": {
        "Fire", "Fire III", "Fire 3", "Fire IV", "Fire 4",
        "Blizzard", "Blizzard III", "Blizzard 3", "Blizzard IV", "Blizzard 4",
        "Paradox", "Despair", "Flare", "Xenoglossy", "Foul",
        "Thunder III", "Thunder 3", "Thunder IV", "Thunder 4",
        "High Thunder", "High Thunder II", "High Thunder 2",
        "Ley Lines", "Triplecast", "Swiftcast", "Amplifier", "Manafont",
        "Flare Star", "Transpose", "Umbral Soul", "High Fire II",
        "High Blizzard II", "Freeze",
    },
    "MNK": {
        "Dragon Kick", "Bootshine", "Leaping Opo", "Twin Snakes", "True Strike",
        "Rising Raptor", "Demolish", "Snap Punch", "Pouncing Coeurl",
        "Arm of the Destroyer", "Shadow of the Destroyer", "Four-point Fury",
        "Rockbreaker", "Perfect Balance", "Form Shift", "Masterful Blitz",
        "Elixir Field", "Elixir Burst", "Celestial Revolution", "Flint Strike",
        "Rising Phoenix", "Tornado Kick", "Phantom Rush", "Riddle of Fire",
        "Fire's Reply", "Brotherhood", "Riddle of Wind", "Wind's Reply",
        "Steeled Meditation", "Inspirited Meditation", "Forbidden Meditation",
        "Enlightened Meditation", "The Forbidden Chakra", "Enlightenment",
        "Six-sided Star",
    },
    "DRG": {
        "Life Surge", "Lance Charge", "Battle Litany", "Geirskogul", "Nastrond",
        "Stardiver", "Starcross", "High Jump", "Mirage Dive", "Dragonfire Dive",
        "Wyrmwind Thrust", "Rise of the Dragon", "True Thrust", "Raiden Thrust",
        "Draconian Fury", "Doom Spike", "Sonic Thrust", "Chaotic Spring", "Heavens' Thrust",
        "Fang and Claw", "Wheeling Thrust", "Drakesbane", "Coerthan Torment",
    },
    "VPR": {
        "Steel Fangs", "Reaving Fangs", "Dread Fangs", "Writhing Snap",
        "Hunter's Sting", "Swiftskin's Sting", "Flanksting Strike", "Flanksbane Fang",
        "Hindsting Strike", "Hindsbane Fang", "Death Rattle",
        "Steel Maw", "Reaving Maw", "Hunter's Bite", "Swiftskin's Bite",
        "Jagged Maw", "Bloodied Maw", "Last Lash",
        "Vicewinder", "Hunter's Coil", "Swiftskin's Coil",
        "Vicepit", "Hunter's Den", "Swiftskin's Den",
        "Twinfang", "Twinblood", "Twinfang Bite", "Twinblood Bite",
        "Twinfang Thresh", "Twinblood Thresh", "Uncoiled Fury",
        "Uncoiled Twinfang", "Uncoiled Twinblood", "Serpent's Ire",
        "Reawaken", "First Generation", "Second Generation", "Third Generation",
        "Fourth Generation", "Ouroboros", "First Legacy", "Second Legacy",
        "Third Legacy", "Fourth Legacy",
    },
    "BRD": {
        "Caustic Bite", "Stormbite", "Iron Jaws", "Raging Strikes", "Barrage",
        "Mage's Ballad", "Army's Paeon", "The Wanderer's Minuet", "Battle Voice",
        "Radiant Finale", "Pitch Perfect", "Apex Arrow", "Blast Arrow",
        "Resonant Arrow", "Radiant Encore", "Sidewinder", "Empyreal Arrow",
    },
    "MCH": {
        "Reassemble", "Wildfire", "Detonator", "Hypercharge", "Heat Blast",
        "Blazing Shot", "Automaton Queen", "Queen Overdrive", "Drill", "Air Anchor",
        "Chain Saw", "Excavator", "Full Metal Field", "Barrel Stabilizer",
        "Double Check", "Checkmate", "Bioblaster", "Auto Crossbow", "Flamethrower",
    },
    "DNC": {
        "Standard Step", "Technical Step", "Standard Finish", "Technical Finish",
        "Double Standard Finish", "Quadruple Technical Finish", "Finishing Move",
        "Tillana", "Devilment", "Flourish", "Saber Dance", "Last Dance",
        "Dance of the Dawn", "Fan Dance", "Fan Dance II", "Fan Dance III",
        "Fan Dance IV", "Starfall Dance", "Cascade", "Fountain", "Bladeshower",
        "Bloodshower",
    },
    "SMN": {
        "Summon Bahamut", "Summon Phoenix", "Summon Solar Bahamut",
        "Summon Ifrit", "Summon Ifrit II", "Summon Titan", "Summon Titan II",
        "Summon Garuda", "Summon Garuda II",
        "Astral Impulse", "Astral Flare", "Deathflare", "Akh Morn",
        "Fountain of Fire", "Brand of Purgatory", "Rekindle", "Revelation",
        "Umbral Impulse", "Umbral Flare", "Sunflare", "Lux Solaris", "Exodus",
        "Enkindle Bahamut", "Enkindle Phoenix", "Enkindle Solar Bahamut",
        "Ruby Rite", "Ruby Catastrophe", "Topaz Rite", "Topaz Catastrophe",
        "Emerald Rite", "Emerald Catastrophe", "Slipstream",
        "Crimson Cyclone", "Crimson Strike", "Mountain Buster",
        "Searing Light", "Searing Flash", "Energy Drain", "Energy Siphon",
        "Fester", "Necrotize", "Painflare", "Ruin IV", "Astral Flow", "Swiftcast",
    },
    "RDM": {
        "Dualcast", "Swiftcast", "Acceleration", "Embolden", "Manafication",
        "Jolt III", "Verthunder II", "Veraero II", "Verthunder III", "Veraero III",
        "Verfire", "Verstone", "Impact", "Grand Impact",
        "Enchanted Riposte", "Enchanted Zwerchhau", "Enchanted Redoublement",
        "Enchanted Moulinet", "Enchanted Moulinet Deux", "Enchanted Moulinet Trois",
        "Enchanted Reprise", "Verholy", "Verflare", "Scorch", "Resolution",
        "Vice of Thorns", "Prefulgence",
    },
}

MODELED_FOLLOWUP_SKILLS = {
    "NIN": {
        "Bunshin", "Dream Within a Dream", "Phantom Kamaitachi",
        "Hakke Mujinsatsu", "Katon", "Goka Mekkyaku",
    },
    "RPR": {"Gluttony", "Enshroud", "Sacrificium", "Communio", "Perfectio"},
    "PCT": {"Pom Muse", "Winged Muse", "Clawed Muse", "Fanged Muse", "Mog of the Ages", "Retribution of the Madeen"},
    "MCH": {"Automaton Queen", "Queen Overdrive", "Wildfire"},
    "SMN": {
        "Summon Bahamut", "Summon Phoenix", "Summon Solar Bahamut",
        "Summon Ifrit", "Summon Ifrit II", "Summon Titan", "Summon Titan II",
        "Summon Garuda", "Summon Garuda II",
        "Enkindle Bahamut", "Enkindle Phoenix", "Enkindle Solar Bahamut",
    },
}


def create_job_state(job, version="7.5"):
    if job == "SAM":
        return SamJobState()
    if job == "NIN":
        return NinJobState(version=version)
    if job == "RPR":
        return RprJobState()
    if job == "PCT":
        return PctJobState()
    if job == "BLM":
        return BlmJobState()
    if job == "MNK":
        return MnkJobState()
    if job == "DRG":
        return DrgJobState()
    if job == "VPR":
        return VprJobState()
    if job == "BRD":
        return BrdJobState()
    if job == "MCH":
        return MchJobState()
    if job == "DNC":
        return DncJobState()
    if job == "SMN":
        return SmnJobState()
    if job == "RDM":
        return RdmJobState()
    return JobState(job)


__all__ = [
    "JobState",
    "SamJobState",
    "NinJobState",
    "RprJobState",
    "PctJobState",
    "BlmJobState",
    "MnkJobState",
    "DrgJobState",
    "VprJobState",
    "BrdJobState",
    "MchJobState",
    "DncJobState",
    "SmnJobState",
    "RdmJobState",
    "MODELED_JOB_STATE_SKILLS",
    "MODELED_FOLLOWUP_SKILLS",
    "create_job_state",
]
