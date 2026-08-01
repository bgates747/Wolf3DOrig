"""Stable Wolf3D shareware logical-sound and Agon fallback catalog."""

from __future__ import annotations

from dataclasses import dataclass


NATIVE_SAMPLE_RATE = 7000
SAMPLE_BUFFER_BASE = 0x5000
COMMAND_BUFFER_BASE = 0x6000
CHANNEL_COUNT = 3


def sample_buffer_id(logical_id: int) -> int:
    return SAMPLE_BUFFER_BASE + logical_id


def command_buffer_ids(logical_id: int) -> tuple[int, ...]:
    return tuple(
        COMMAND_BUFFER_BASE + logical_id * CHANNEL_COUNT + channel
        for channel in range(CHANNEL_COUNT)
    )


# The exact ``#define UPLOAD`` branch of WL_MAIN.C's wolfdigimap table.
# DEATHSCREAM2SND and DEATHSCREAM3SND intentionally share digitized sound 13.
UPLOAD_DIGI_MAP = {
    "HALTSND": 0,
    "DOGBARKSND": 1,
    "CLOSEDOORSND": 2,
    "OPENDOORSND": 3,
    "ATKMACHINEGUNSND": 4,
    "ATKPISTOLSND": 5,
    "ATKGATLINGSND": 6,
    "SCHUTZADSND": 7,
    "GUTENTAGSND": 8,
    "MUTTISND": 9,
    "BOSSFIRESND": 10,
    "SSFIRESND": 11,
    "DEATHSCREAM1SND": 12,
    "DEATHSCREAM2SND": 13,
    "DEATHSCREAM3SND": 13,
    "TAKEDAMAGESND": 14,
    "PUSHWALLSND": 15,
    "LEBENSND": 20,
    "NAZIFIRESND": 21,
    "SLURPIESND": 22,
}


# Current gameplay producers, including the settled next audio integration
# slice.  Tags describe semantic producers rather than assembly label names so
# the manifest remains stable if code is reorganized.
CURRENT_PRODUCERS = {
    "NOWAYSND": ("environment.no_way",),
    "PLAYERDEATHSND": ("player.death",),
    "DOGDEATHSND": ("actor.dog.death",),
    "ATKGATLINGSND": ("player.chaingun",),
    "GETKEYSND": ("pickup.key",),
    "TAKEDAMAGESND": ("player.damage",),
    "OPENDOORSND": ("environment.door_open",),
    "CLOSEDOORSND": ("environment.door_close",),
    "HALTSND": ("actor.guard.alert",),
    "DEATHSCREAM2SND": ("actor.guard.death",),
    "ATKKNIFESND": ("player.knife",),
    "ATKPISTOLSND": ("player.pistol",),
    "ATKMACHINEGUNSND": ("player.machinegun",),
    "DEATHSCREAM1SND": ("actor.guard.death",),
    "GETMACHINESND": ("pickup.machinegun",),
    "GETAMMOSND": ("pickup.ammunition",),
    "HEALTH1SND": ("pickup.food_or_alpo",),
    "HEALTH2SND": ("pickup.first_aid",),
    "BONUS1SND": ("pickup.cross",),
    "BONUS2SND": ("pickup.chalice",),
    "BONUS3SND": ("pickup.bible",),
    "GETGATLINGSND": ("pickup.chaingun",),
    "DOGBARKSND": ("actor.dog.alert",),
    "BONUS1UPSND": ("pickup.extra_life",),
    "BONUS4SND": ("pickup.crown",),
    "PUSHWALLSND": ("environment.pushwall",),
    "SCHUTZADSND": ("actor.ss.alert",),
    "AHHHGSND": ("actor.mutant.death",),
    "LEBENSND": ("actor.ss.death",),
    "NAZIFIRESND": ("actor.guard_officer_mutant.fire",),
    "SSFIRESND": ("actor.ss.fire",),
    "SLURPIESND": ("pickup.gibs",),
    "SPIONSND": ("actor.officer.alert",),
    "NEINSOVASSND": ("actor.officer.death",),
    "DOGATTACKSND": ("actor.dog.attack",),
}


@dataclass(frozen=True)
class FallbackSpec:
    filename: str
    note: str


# The canonical 22-effect collection is transport-test material, not native
# Wolf3D fidelity.  These mappings are deliberately explicit so none can be
# mistaken for an original VSWAP digitized effect.  Wilhelm is intentionally
# absent; it remains reserved for a later easter egg.
FALLBACKS = {
    "NOWAYSND": FallbackSpec(
        "gun_empty.wav", "dry mechanical refusal used for the no-way response"
    ),
    "PLAYERDEATHSND": FallbackSpec(
        "scream.wav", "generic player-death scream"
    ),
    "DOGDEATHSND": FallbackSpec("dog_yelp.wav", "dog death yelp"),
    "GETKEYSND": FallbackSpec(
        "got_treasure.wav", "generic pickup chime used for keys"
    ),
    "ATKKNIFESND": FallbackSpec("knife.wav", "knife attack"),
    "GETMACHINESND": FallbackSpec(
        "gun_reload.wav", "generic firearm-acquisition sound"
    ),
    "GETAMMOSND": FallbackSpec(
        "gun_reload.wav", "generic ammunition pickup sound"
    ),
    "HEALTH1SND": FallbackSpec(
        "got_treasure.wav", "generic pickup chime used for food and dog food"
    ),
    "HEALTH2SND": FallbackSpec(
        "got_treasure.wav", "generic pickup chime used for first aid"
    ),
    "BONUS1SND": FallbackSpec(
        "got_treasure.wav", "generic treasure pickup chime"
    ),
    "BONUS2SND": FallbackSpec(
        "got_treasure.wav", "generic treasure pickup chime"
    ),
    "BONUS3SND": FallbackSpec(
        "got_treasure.wav", "generic treasure pickup chime"
    ),
    "GETGATLINGSND": FallbackSpec(
        "gun_reload.wav", "generic firearm-acquisition sound"
    ),
    "BONUS1UPSND": FallbackSpec(
        "got_treasure.wav", "generic pickup chime used for extra life"
    ),
    "BONUS4SND": FallbackSpec(
        "got_treasure.wav", "generic treasure pickup chime"
    ),
    "AHHHGSND": FallbackSpec("ahh.wav", "generic mutant death cry"),
    "SPIONSND": FallbackSpec(
        "achtung.wav", "generic German alert used for officer first sighting"
    ),
    "NEINSOVASSND": FallbackSpec("ugh.wav", "generic officer death grunt"),
    "DOGATTACKSND": FallbackSpec(
        "dog_woof_single.wav", "single dog vocalization used for the bite attack"
    ),
}
