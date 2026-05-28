import math
import random
from dataclasses import dataclass

try:
    from xiv_job_data import JOB_PROFILES
except ImportError:
    from .xiv_job_data import JOB_PROFILES


DH_DAMAGE_MULT_BONUS = 0.25
MAX_MAINSTAT_FRACTION = 0.10
DEFAULT_VARIANCE_RANGE = 0.10


def clamp(value, low=0.0, high=1.0):
    return min(high, max(low, value))


@dataclass(frozen=True)
class FormulaStats:
    job: str
    main_stat: int
    crit: int
    det: int
    dh: int
    speed: int
    wd: int
    weapon_delay: float
    party_bonus: float = 1.05
    level: int = 100
    tenacity: int | None = None
    healer_or_caster_strength: int | None = None

    @classmethod
    def from_job(cls, job, main_stat, crit, det, dh, speed, wd, weapon_delay, party_bonus=1.05):
        return cls(
            job=job,
            main_stat=int(main_stat),
            crit=int(crit),
            det=int(det),
            dh=int(dh),
            speed=int(speed),
            wd=int(wd),
            weapon_delay=float(weapon_delay),
            party_bonus=float(party_bonus),
        )


@dataclass(frozen=True)
class DamageModifiers:
    damage_mult: float = 1.0
    single_damage_mult: float = 1.0
    crit_rate_add: float = 0.0
    dh_rate_add: float = 0.0
    main_stat_add: float = 0.0
    main_stat_mult: float = 1.0
    forced_crit: bool = False
    forced_dh: bool = False
    forced_no_crit: bool = False
    forced_no_dh: bool = False
    trait_damage_mult: float | None = None


@dataclass(frozen=True)
class DamageBreakdown:
    base_damage: float
    crit_rate: float
    direct_hit_rate: float
    crit_bonus: float
    normal: float
    crit: float
    direct_hit: float
    crit_direct_hit: float
    expected: float
    low_roll: float
    high_roll: float


class XivDamageFormula:
    def __init__(self, stats: FormulaStats):
        self.stats = stats
        self.profile = JOB_PROFILES.get(stats.job, JOB_PROFILES.get("SAM"))
        if self.profile is None:
            raise ValueError(f"Unsupported job: {stats.job}")
        if stats.level != 100:
            raise ValueError("Current local formula data is wired for level 100.")
        self.level_mods = self.profile.level_modifiers

    @property
    def is_caster(self):
        return self.profile.main_stat in {"INT", "MND"}

    @property
    def is_tank(self):
        return self.profile.main_stat == "VIT"

    def crit_rate(self):
        return math.floor(200 * (self.stats.crit - self.level_mods.sub) / self.level_mods.div + 50) / 1000

    def crit_bonus(self):
        return math.floor(200 * (self.stats.crit - self.level_mods.sub) / self.level_mods.div + 400) / 1000

    def crit_multiplier(self):
        return 1.0 + self.crit_bonus()

    def direct_hit_rate(self):
        return math.floor(550 * (self.stats.dh - self.level_mods.sub) / self.level_mods.div) / 1000

    def f_wd(self, job_mod=None):
        job_mod = self.profile.job_mod if job_mod is None else job_mod
        return math.floor(self.level_mods.main * job_mod / 1000 + self.stats.wd)

    def f_auto(self, job_mod=None):
        return math.floor(self.f_wd(job_mod) * (self.stats.weapon_delay / 3.0))

    def f_spd(self):
        return math.floor(130 * (self.stats.speed - self.level_mods.sub) / self.level_mods.div + 1000)

    def f_det(self):
        return math.floor(140 * (self.stats.det - self.level_mods.main) / self.level_mods.det + 1000)

    def f_det_dh(self):
        return self.f_det() + math.floor(140 * (self.stats.dh - self.level_mods.sub) / self.level_mods.div)

    def f_tenacity(self):
        tenacity = self.stats.tenacity if self.stats.tenacity is not None else self.level_mods.sub
        return math.floor(112 * (tenacity - self.level_mods.sub) / self.level_mods.div + 1000)

    def f_ap(self, main_stat):
        ap_const = self.level_mods.ap_tank if self.is_tank else self.level_mods.ap
        return math.floor(ap_const * (main_stat - self.level_mods.main) / self.level_mods.main + 100)

    def final_main_stat(self, modifiers=DamageModifiers(), apply_party_bonus=True):
        main_stat = math.floor(self.stats.main_stat * modifiers.main_stat_mult)
        if apply_party_bonus:
            main_stat = math.floor(main_stat * self.stats.party_bonus)
        main_stat += min(modifiers.main_stat_add, MAX_MAINSTAT_FRACTION * main_stat)
        return main_stat

    def gcd_seconds(self, base_ms=2500):
        speed_reduction = math.floor(130 * (self.stats.speed - self.level_mods.sub) / self.level_mods.div)
        base = math.floor((1000 - speed_reduction) * base_ms / 1000)
        job_adjusted = math.floor(base * self.profile.gcd_modifier)
        return base / 1000.0, job_adjusted / 1000.0

    def time_using_speed_stat_ms(self, time_ms):
        speed_term = math.ceil(130 * (self.level_mods.sub - self.stats.speed) / self.level_mods.div)
        return int(1000 * (math.floor(time_ms * (1000 + speed_term) / 10000) / 100))

    def _det_or_det_dh(self, modifiers):
        return self.f_det_dh() if modifiers.forced_dh else self.f_det()

    def _guaranteed_bonus(self, base_damage, modifiers):
        extra = 0
        if modifiers.forced_dh:
            extra += math.floor(base_damage * DH_DAMAGE_MULT_BONUS * modifiers.dh_rate_add)
        if modifiers.forced_crit:
            extra += math.floor(base_damage * self.crit_bonus() * modifiers.crit_rate_add)
        return base_damage + extra

    def base_direct_damage(self, potency, modifiers=DamageModifiers()):
        main_stat = self.final_main_stat(modifiers)
        ap = self.f_ap(main_stat)
        wd = self.f_wd()
        det = self._det_or_det_dh(modifiers)

        if self.is_caster:
            base_damage = math.floor(ap * det / 1000) / 100
            base_damage = math.floor(base_damage * math.floor(wd * potency / 100))
        else:
            base_damage = math.floor(math.floor(potency * ap / 100) / 100 * det / 10) / 100
            if self.is_tank:
                base_damage = math.floor(base_damage * self.f_tenacity() / 10) / 100
            base_damage = math.floor(math.floor(base_damage * wd))

        return max(self._guaranteed_bonus(base_damage, modifiers), 1.0)

    def base_physical_dot_damage(self, potency, modifiers=DamageModifiers()):
        main_stat = self.final_main_stat(modifiers)
        ap = self.f_ap(main_stat)
        wd = self.f_wd()
        det = self._det_or_det_dh(modifiers)
        spd = self.f_spd()

        base_damage = math.floor(potency * ap * det / 100) / 1000
        if self.is_tank:
            base_damage = math.floor(base_damage * self.f_tenacity() / 1000)
        base_damage = math.floor(math.floor(base_damage * spd) / 1000)
        base_damage = math.floor(math.floor(base_damage * wd) / 100)
        return max(self._guaranteed_bonus(base_damage, modifiers), 1.0)

    def base_magical_dot_damage(self, potency, modifiers=DamageModifiers()):
        main_stat = self.final_main_stat(modifiers)
        ap = self.f_ap(main_stat)
        wd = self.f_wd()
        det = self._det_or_det_dh(modifiers)
        spd = self.f_spd()

        base_damage = math.floor(math.floor(potency * wd) / 100)
        base_damage = math.floor(math.floor(math.floor(base_damage * ap) * spd))
        base_damage = math.floor(math.floor(base_damage * det) / 1000)
        if self.is_tank:
            base_damage = math.floor(base_damage * self.f_tenacity() / 1000)
        base_damage = math.floor(math.floor(base_damage / 1000) / 100)
        return max(self._guaranteed_bonus(base_damage, modifiers), 1.0)

    def base_auto_damage(self, potency=90, modifiers=DamageModifiers()):
        if self.is_caster:
            if self.stats.healer_or_caster_strength is None:
                raise ValueError("Caster auto damage needs healer_or_caster_strength.")
            main_stat = math.floor(self.stats.healer_or_caster_strength * self.stats.party_bonus)
        else:
            main_stat = self.final_main_stat(modifiers)

        ap = self.f_ap(main_stat)
        det = self._det_or_det_dh(modifiers)
        spd = self.f_spd() if not self.is_caster else 1000
        auto = self.f_auto()

        base_damage = math.floor(math.floor(potency * ap / 100) / 100 * det / 10) / 100
        if self.is_tank:
            base_damage = math.floor(base_damage * self.f_tenacity() / 10) / 100
        base_damage = math.floor(base_damage * spd) / 10
        base_damage = math.floor(math.floor(base_damage * auto) / 100)
        return max(self._guaranteed_bonus(base_damage, modifiers), 1.0)

    def hit_rates(self, modifiers=DamageModifiers()):
        if modifiers.forced_dh and modifiers.forced_no_dh:
            raise ValueError("forced_dh and forced_no_dh cannot both be true.")
        if modifiers.forced_crit and modifiers.forced_no_crit:
            raise ValueError("forced_crit and forced_no_crit cannot both be true.")

        dh_rate = 1.0 if modifiers.forced_dh else 0.0 if modifiers.forced_no_dh else self.direct_hit_rate() + modifiers.dh_rate_add
        crit_rate = 1.0 if modifiers.forced_crit else 0.0 if modifiers.forced_no_crit else self.crit_rate() + modifiers.crit_rate_add
        return clamp(crit_rate), clamp(dh_rate), self.crit_bonus()

    def finalize_hit(self, base_damage, is_crit=False, is_direct_hit=False, modifiers=DamageModifiers(), variance=1.0):
        trait_mult = self.profile.trait_damage_multiplier if modifiers.trait_damage_mult is None else modifiers.trait_damage_mult
        damage = float(base_damage)
        if is_crit:
            damage += math.floor(damage * self.crit_bonus())
        if is_direct_hit:
            damage += math.floor(damage * DH_DAMAGE_MULT_BONUS)
        damage = math.floor(damage * trait_mult)
        damage = math.floor(damage * modifiers.single_damage_mult)
        damage = math.floor(damage * variance)
        damage = math.floor(damage * modifiers.damage_mult)
        return damage

    def damage_breakdown(self, base_damage, modifiers=DamageModifiers()):
        crit_rate, dh_rate, crit_bonus = self.hit_rates(modifiers)
        normal = self.finalize_hit(base_damage, False, False, modifiers)
        crit = self.finalize_hit(base_damage, True, False, modifiers)
        direct_hit = self.finalize_hit(base_damage, False, True, modifiers)
        crit_direct_hit = self.finalize_hit(base_damage, True, True, modifiers)
        expected = (
            normal * (1 - crit_rate) * (1 - dh_rate)
            + crit * crit_rate * (1 - dh_rate)
            + direct_hit * (1 - crit_rate) * dh_rate
            + crit_direct_hit * crit_rate * dh_rate
        )
        low_roll = self.finalize_hit(base_damage, False, False, modifiers, variance=0.95)
        high_roll = self.finalize_hit(base_damage, True, True, modifiers, variance=1.05)
        return DamageBreakdown(
            base_damage=base_damage,
            crit_rate=crit_rate,
            direct_hit_rate=dh_rate,
            crit_bonus=crit_bonus,
            normal=normal,
            crit=crit,
            direct_hit=direct_hit,
            crit_direct_hit=crit_direct_hit,
            expected=expected,
            low_roll=low_roll,
            high_roll=high_roll,
        )

    def roll_damage(self, base_damage, modifiers=DamageModifiers(), rng=None, variance_range=DEFAULT_VARIANCE_RANGE):
        rng = rng or random
        crit_rate, dh_rate, _ = self.hit_rates(modifiers)
        is_crit = rng.random() < crit_rate
        is_direct_hit = rng.random() < dh_rate
        variance = 1.0 - variance_range / 2 + variance_range * rng.random()
        return self.finalize_hit(base_damage, is_crit, is_direct_hit, modifiers, variance), is_crit, is_direct_hit


def build_formula_from_sim_stats(stats):
    job = stats.get("job", "SAM")
    return XivDamageFormula(
        FormulaStats.from_job(
            job=job,
            main_stat=stats.get("main_stat", stats.get("str")),
            crit=stats["crt"],
            det=stats["det"],
            dh=stats["dh"],
            speed=stats["sks"],
            wd=stats["wd"],
            weapon_delay=stats["delay"],
            party_bonus=stats.get("party_bonus", 1.05),
        )
    )
