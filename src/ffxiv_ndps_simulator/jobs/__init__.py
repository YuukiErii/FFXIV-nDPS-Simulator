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
        "Arcane Circle", "Enshroud", "Soulsow", "Gluttony", "Plentiful Harvest",
        "Sacrificium", "Communio", "Perfectio", "Harvest Moon", "+10 Soul Gauge",
        "Shadow of Death", "Whorl of Death",
    },
    "PCT": {
        "Creature Motif", "Pom Motif", "Wing Motif", "Claw Motif", "Maw Motif",
        "Weapon Motif", "Hammer Motif", "Landscape Motif", "Starry Sky Motif",
        "Pom Muse", "Winged Muse", "Clawed Muse", "Fanged Muse", "Striking Muse",
        "Starry Muse", "Subtractive Palette", "Hyperphantasia", "Rainbow Drip",
        "Hammer Stamp", "Hammer Brush", "Polishing Hammer", "Mog of the Ages",
        "Retribution of the Madeen", "Star Prism",
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
        "Dragon Kick", "Bootshine", "Leaping Opo", "Twin Snakes", "Rising Raptor",
        "Demolish", "Pouncing Coeurl", "Perfect Balance", "Masterful Blitz",
        "Elixir Field", "Flint Strike", "Rising Phoenix", "Phantom Rush",
        "Riddle of Fire", "Brotherhood", "Riddle of Wind", "Form Shift",
        "The Forbidden Chakra", "Enlightenment", "Six-sided Star",
    },
    "DRG": {
        "Life Surge", "Lance Charge", "Battle Litany", "Geirskogul", "Nastrond",
        "Stardiver", "Starcross", "High Jump", "Mirage Dive", "Dragonfire Dive",
        "Wyrmwind Thrust", "Rise of the Dragon", "Chaotic Spring", "Heavens' Thrust",
        "Fang and Claw", "Wheeling Thrust", "Drakesbane", "Coerthan Torment",
    },
    "VPR": {
        "Steel Fangs", "Dread Fangs", "Hunter's Sting", "Swiftskin's Sting",
        "Hunter's Coil", "Swiftskin's Coil", "Reawaken", "First Generation",
        "Second Generation", "Third Generation", "Fourth Generation", "First Legacy",
        "Second Legacy", "Third Legacy", "Fourth Legacy", "Uncoiled Fury",
        "Twinfang", "Twinblood", "Serpent's Ire", "Vicewinder", "Vicepit",
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
        "Summon Garuda", "Summon Garuda II", "Deathflare", "Akh Morn",
        "Enkindle Bahamut", "Enkindle Phoenix", "Enkindle Solar Bahamut",
        "Searing Light", "Energy Drain", "Energy Siphon", "Fester", "Painflare",
        "Slipstream", "Crimson Cyclone", "Crimson Strike", "Mountain Buster",
        "Ruin IV", "Astral Flow",
    },
    "RDM": {
        "Dualcast", "Acceleration", "Embolden", "Manafication",
        "Jolt III", "Verthunder III", "Veraero III", "Verfire", "Verstone",
        "Enchanted Riposte", "Enchanted Zwerchhau", "Enchanted Redoublement",
        "Enchanted Moulinet", "Verholy", "Verflare", "Scorch", "Resolution",
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


def create_job_state(job, version="7.2"):
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
