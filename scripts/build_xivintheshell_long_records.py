import json
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_LINE = REPO_ROOT / "examples/skill_lines"


def skill(name, targets=None):
    return {"type": "Skill", "skillName": name, "targetList": targets or [1]}


def jump(time_value):
    return {"type": "JumpToTimestamp", "targetTime": time_value}


def wait(duration):
    return {"type": "Wait", "waitDuration": duration}


WINDOWS = {
    "MNK": [
        jump(45),
        skill("Dragon Kick"), skill("Twin Snakes"), skill("Demolish"),
        skill("Leaping Opo"), skill("Rising Raptor"), skill("Pouncing Coeurl"),
        skill("Dragon Kick"), skill("Twin Snakes"), skill("Demolish"),
        skill("Perfect Balance"), skill("Leaping Opo"), skill("Dragon Kick"),
        skill("Leaping Opo"), skill("Elixir Burst"), skill("The Forbidden Chakra"),
        jump(90),
        skill("Riddle of Fire"), skill("Brotherhood"), skill("Dragon Kick"),
        skill("Twin Snakes"), skill("Demolish"), skill("Leaping Opo"),
        skill("Rising Raptor"), skill("Pouncing Coeurl"), skill("Riddle of Wind"),
        skill("Wind's Reply"), skill("Fire's Reply"), skill("The Forbidden Chakra"),
        jump(135),
        skill("Perfect Balance"), skill("Dragon Kick"), skill("Leaping Opo"),
        skill("Dragon Kick"), skill("Rising Phoenix"), skill("Dragon Kick"),
        skill("Twin Snakes"), skill("Demolish"), skill("Leaping Opo"),
        skill("Rising Raptor"), skill("Pouncing Coeurl"), skill("Phantom Rush"),
    ],
    "DRG": [
        jump(45),
        skill("Raiden Thrust"), skill("Spiral Blow"), skill("Chaotic Spring"),
        skill("Wheeling Thrust"), skill("Fang and Claw"), skill("Drakesbane"),
        skill("High Jump"), skill("Mirage Dive"), skill("Geirskogul"), skill("Nastrond"),
        skill("Raiden Thrust"), skill("Spiral Blow"), skill("Heavens' Thrust"),
        skill("Fang and Claw"), skill("Wheeling Thrust"), skill("Drakesbane"),
        jump(90),
        skill("Lance Charge"), skill("Life Surge"), skill("Raiden Thrust"),
        skill("Spiral Blow"), skill("Chaotic Spring"), skill("High Jump"),
        skill("Mirage Dive"), skill("Geirskogul"), skill("Nastrond"),
        skill("Stardiver"), skill("Starcross"), skill("Wyrmwind Thrust"),
        jump(135),
        skill("Raiden Thrust"), skill("Spiral Blow"), skill("Heavens' Thrust"),
        skill("Fang and Claw"), skill("Wheeling Thrust"), skill("Drakesbane"),
        skill("High Jump"), skill("Mirage Dive"), skill("Geirskogul"),
        skill("Nastrond"), skill("Dragonfire Dive"), skill("Rise of the Dragon"),
    ],
    "VPR": [
        jump(55),
        skill("Steel Fangs"), skill("Hunter's Sting"), skill("Flanksting Strike"),
        skill("Death Rattle"), skill("Reaving Fangs"), skill("Swiftskin's Sting"),
        skill("Hindsting Strike"), skill("Death Rattle"), skill("Vicewinder"),
        skill("Hunter's Coil"), skill("Twinfang Bite"), skill("Twinblood Bite"),
        skill("Swiftskin's Coil"), skill("Twinblood Bite"), skill("Twinfang Bite"),
        jump(110),
        skill("Serpent's Ire"), skill("Reawaken"), skill("First Generation"),
        skill("First Legacy"), skill("Second Generation"), skill("Second Legacy"),
        skill("Third Generation"), skill("Third Legacy"), skill("Fourth Generation"),
        skill("Fourth Legacy"), skill("Ouroboros"), skill("Uncoiled Fury"),
        skill("Uncoiled Twinfang"), skill("Uncoiled Twinblood"),
        jump(165),
        skill("Steel Fangs"), skill("Hunter's Sting"), skill("Flanksting Strike"),
        skill("Death Rattle"), skill("Reaving Fangs"), skill("Swiftskin's Sting"),
        skill("Hindsting Strike"), skill("Death Rattle"), skill("Vicewinder"),
        skill("Hunter's Coil"), skill("Twinfang Bite"), skill("Twinblood Bite"),
    ],
    "BRD": [
        jump(45),
        skill("Mage's Ballad"), skill("Burst Shot"), skill("Empyreal Arrow"),
        skill("Bloodletter"), skill("Burst Shot"), skill("Refulgent Arrow"),
        skill("Iron Jaws"), skill("Heartbreak Shot"), skill("Burst Shot"),
        skill("Sidewinder"), skill("Burst Shot"), skill("Apex Arrow"),
        skill("Blast Arrow"), skill("Radiant Encore"),
        jump(90),
        skill("Army's Paeon"), skill("Burst Shot"), skill("Empyreal Arrow"),
        skill("Bloodletter"), skill("Burst Shot"), skill("Refulgent Arrow"),
        skill("Iron Jaws"), skill("Barrage"), skill("Refulgent Arrow"),
        skill("Resonant Arrow"), skill("Burst Shot"), skill("Heartbreak Shot"),
        jump(135),
        skill("The Wanderer's Minuet"), skill("Raging Strikes"),
        skill("Battle Voice"), skill("Radiant Finale"), skill("Burst Shot"),
        skill("Empyreal Arrow"), skill("Pitch Perfect"), skill("Iron Jaws"),
        skill("Barrage"), skill("Refulgent Arrow"), skill("Sidewinder"),
        skill("Apex Arrow"), skill("Blast Arrow"), skill("Radiant Encore"),
    ],
    "MCH": [
        jump(45),
        skill("Heated Split Shot"), skill("Heated Slug Shot"), skill("Heated Clean Shot"),
        skill("Drill"), skill("Gauss Round"), skill("Heated Split Shot"),
        skill("Heated Slug Shot"), skill("Heated Clean Shot"), skill("Air Anchor"),
        skill("Double Check"), skill("Checkmate"), skill("Chain Saw"), skill("Excavator"),
        jump(90),
        skill("Reassemble"), skill("Drill"), skill("Barrel Stabilizer"),
        skill("Hypercharge"), skill("Heat Blast"), skill("Heat Blast"),
        skill("Heat Blast"), skill("Heat Blast"), skill("Heat Blast"),
        skill("Wildfire"), skill("Detonator"), skill("Automaton Queen"),
        skill("Full Metal Field"), skill("Double Check"), skill("Checkmate"),
        jump(135),
        skill("Heated Split Shot"), skill("Heated Slug Shot"), skill("Heated Clean Shot"),
        skill("Drill"), skill("Air Anchor"), skill("Chain Saw"),
        skill("Excavator"), skill("Gauss Round"), skill("Double Check"),
        skill("Checkmate"), skill("Heated Split Shot"), skill("Heated Slug Shot"),
        skill("Heated Clean Shot"),
    ],
    "DNC": [
        jump(45),
        skill("Cascade"), skill("Fountain"), skill("Reverse Cascade"),
        skill("Fountainfall"), skill("Standard Step"), skill("Emboite"),
        skill("Entrechat"), skill("Standard Finish"), skill("Last Dance"),
        skill("Flourish"), skill("Fan Dance III"), skill("Fan Dance IV"),
        skill("Saber Dance"), skill("Starfall Dance"),
        jump(90),
        skill("Cascade"), skill("Fountain"), skill("Reverse Cascade"),
        skill("Fountainfall"), skill("Saber Dance"), skill("Dance of the Dawn"),
        skill("Standard Step"), skill("Jete"), skill("Pirouette"),
        skill("Standard Finish"), skill("Last Dance"),
        jump(135),
        skill("Technical Step", []), skill("Emboite"), skill("Entrechat"),
        skill("Jete"), skill("Pirouette"), skill("Technical Finish"),
        skill("Devilment"), skill("Tillana"), skill("Finishing Move"),
        skill("Dance of the Dawn"), skill("Fan Dance III"), skill("Fan Dance IV"),
        skill("Starfall Dance"), skill("Saber Dance"),
    ],
    "SMN": [
        jump(45),
        skill("Summon Titan II"), skill("Topaz Rite"), skill("Mountain Buster"),
        skill("Topaz Rite"), skill("Mountain Buster"), skill("Summon Garuda II"),
        skill("Slipstream"), skill("Emerald Rite"), skill("Emerald Rite"),
        skill("Summon Ifrit II"), skill("Ruby Rite"), skill("Crimson Cyclone"),
        skill("Crimson Strike"), skill("Ruby Rite"), skill("Ruin III"),
        jump(90),
        skill("Searing Light"), skill("Summon Bahamut"), skill("Astral Impulse"),
        skill("Deathflare"), skill("Akh Morn"), skill("Astral Impulse"),
        skill("Energy Drain"), skill("Necrotize"), skill("Necrotize"),
        skill("Summon Titan II"), skill("Topaz Rite"), skill("Mountain Buster"),
        jump(135),
        skill("Summon Phoenix"), skill("Fountain of Fire"), skill("Brand of Purgatory"),
        skill("Enkindle Phoenix"), skill("Fountain of Fire"), skill("Brand of Purgatory"),
        skill("Summon Garuda II"), skill("Slipstream"), skill("Emerald Rite"),
        skill("Summon Ifrit II"), skill("Ruby Rite"), skill("Crimson Cyclone"),
        skill("Crimson Strike"),
    ],
    "RDM": [
        jump(45),
        skill("Jolt III"), skill("Verthunder III"), skill("Fleche"),
        skill("Jolt III"), skill("Veraero III"), skill("Contre Sixte"),
        skill("Acceleration"), skill("Grand Impact"), skill("Verthunder III"),
        skill("Jolt III"), skill("Veraero III"),
        jump(90),
        skill("Manafication"), skill("Embolden"), skill("Enchanted Riposte"),
        skill("Enchanted Zwerchhau"), skill("Enchanted Redoublement"),
        skill("Verholy"), skill("Scorch"), skill("Resolution"),
        skill("Vice of Thorns"), skill("Prefulgence"), skill("Fleche"),
        skill("Contre Sixte"),
        jump(135),
        skill("Jolt III"), skill("Verthunder III"), skill("Jolt III"),
        skill("Veraero III"), skill("Acceleration"), skill("Grand Impact"),
        skill("Verthunder III"), skill("Jolt III"), skill("Veraero III"),
        skill("Fleche"), skill("Contre Sixte"),
    ],
}


ALWAYS_PROC_JOBS = {"BRD", "DNC", "VPR"}


def load_smoke_record(job):
    path = SKILL_LINE / f"{job}_xivintheshell_smoke" / f"{job}_xivintheshell_smoke.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_record(job):
    record = deepcopy(load_smoke_record(job))
    record["name"] = f"{job} xivintheshell manual long axis candidate"
    record["config"]["procMode"] = "Always" if job in ALWAYS_PROC_JOBS else record["config"].get("procMode", "Never")
    record["actions"] = record["actions"] + WINDOWS[job] + [wait(1.0)]
    return record


def write_note(job, directory):
    note = f"""# {job} xivintheshell Long Axis Candidate

Generated: 2026-05-27

Source:

- Seeded from `examples/skill_lines/{job}_xivintheshell_smoke/{job}_xivintheshell_smoke.json`.
- Extended manually as a longer xivintheshell Record JSON, then exported through `https://xivintheshell.com/` to `time/action/isGCD/castTime` CSV.

Status:

- This is a long-axis import and state-machine regression sample.
- It is not an FFLogs or AMAS numerical validation artifact.
- Keep the JSON with the CSV so the action log can be regenerated from xivintheshell.
"""
    (directory / "source.md").write_text(note, encoding="utf-8")


def main():
    for job in sorted(WINDOWS):
        directory = SKILL_LINE / f"{job}_xivintheshell_long"
        directory.mkdir(parents=True, exist_ok=True)
        out_path = directory / f"{job}_xivintheshell_long.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(build_record(job), f, ensure_ascii=False, separators=(",", ":"))
        write_note(job, directory)
        print(out_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
