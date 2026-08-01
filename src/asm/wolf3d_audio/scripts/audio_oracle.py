"""Host specification for the Wolf3DOrig three-channel audio service."""

from __future__ import annotations

from dataclasses import dataclass


SOUND_COUNT = 69
CHANNEL_COUNT = 3
SAMPLE_BUFFER_BASE = 0x5000
COMMAND_BUFFER_BASE = 0x6000
FLAG_POSITIONED = 0x01

PRIORITIES = (
    50, 45, 1, 99, 50, 50, 50, 50, 50, 50,
    99, 99, 99, 99, 99, 99, 49, 50, 1, 50,
    50, 10, 1, 1, 1, 60, 50, 99, 50, 50,
    90, 70, 10, 10, 90, 99, 20, 20, 10, 50,
    50, 49, 50, 50, 50, 50, 30, 50, 80, 80,
    20, 85, 85, 70, 70, 70, 87, 10, 99, 50,
    40, 40, 85, 85, 50, 60, 60, 85, 99,
)


def sample_buffer_id(sound: int) -> int:
    if not 0 <= sound < SOUND_COUNT:
        raise ValueError(sound)
    return SAMPLE_BUFFER_BASE + sound


def command_buffer_id(sound: int, channel: int) -> int:
    if not 0 <= sound < SOUND_COUNT or not 0 <= channel < CHANNEL_COUNT:
        raise ValueError((sound, channel))
    return COMMAND_BUFFER_BASE + sound * CHANNEL_COUNT + channel


def reset_command(channel: int) -> bytes:
    return bytes((23, 0, 0x85, channel, 10))


def waveform_command(sound: int, channel: int) -> bytes:
    sample = sample_buffer_id(sound)
    return bytes((23, 0, 0x85, channel, 4, 8, sample & 0xFF, sample >> 8))


def play_command(channel: int, gain: int) -> bytes:
    return bytes((23, 0, 0x85, channel, 0, gain, 0, 0, 0, 0))


def direct_wire(sound: int, channel: int, gain: int) -> bytes:
    return reset_command(channel) + waveform_command(sound, channel) + play_command(channel, gain)


def buffered_procedure(sound: int, channel: int) -> bytes:
    return direct_wire(sound, channel, 127)


def buffered_wire(sound: int, channel: int, gain: int) -> bytes:
    command = command_buffer_id(sound, channel)
    call = bytes((23, 0, 0xA0, command & 0xFF, command >> 8, 1))
    volume = bytes((23, 0, 0x85, channel, 2, gain))
    return call + volume


def upload_wire(sound: int, channel: int) -> bytes:
    command = command_buffer_id(sound, channel)
    procedure = buffered_procedure(sound, channel)
    clear = bytes((23, 0, 0xA0, command & 0xFF, command >> 8, 2))
    header = bytes(
        (23, 0, 0xA0, command & 0xFF, command >> 8, 0,
         len(procedure) & 0xFF, len(procedure) >> 8)
    )
    return clear + header + procedure


@dataclass(frozen=True)
class Request:
    sound: int
    gain: int
    flags: int
    priority: int
    order: int


@dataclass(frozen=True)
class Emission:
    request: Request
    channel: int


class AudioOracle:
    """Reference batching policy independent of eZ80 implementation details."""

    def __init__(self) -> None:
        self.loaded: set[int] = set()
        self.active = False
        self.pending: list[Request] = []
        self.order = 0
        self.next_channel = 0
        self.discarded_quanta = 0
        self.discarded_events = 0
        self.dropped_requests = 0

    def begin_quantum(self) -> None:
        if self.active:
            self.discard_quantum()
        self.active = True
        self.pending.clear()
        self.order = 0

    def request(self, sound: int, gain: int, flags: int = 0) -> bool:
        if not self.active or not 0 <= sound < SOUND_COUNT or sound not in self.loaded:
            return False
        gain = min(gain, 127)
        if gain <= 0:
            return False
        request = Request(sound, gain, flags, PRIORITIES[sound], self.order)
        self.order = (self.order + 1) & 0xFF
        candidates = self.pending + [request]
        # Python's sort is stable, which pins equal priority to request order.
        candidates.sort(key=lambda item: -item.priority)
        if len(candidates) > CHANNEL_COUNT:
            self.dropped_requests += 1
        self.pending = candidates[:CHANNEL_COUNT]
        return True

    def discard_quantum(self) -> None:
        if not self.active:
            return
        self.discarded_quanta += 1
        self.discarded_events += len(self.pending)
        self.pending.clear()
        self.active = False

    def flush_quantum(self) -> list[Emission]:
        if not self.active:
            return []
        emissions: list[Emission] = []
        for request in self.pending:
            if request.sound not in self.loaded:
                continue
            emissions.append(Emission(request, self.next_channel))
            self.next_channel = (self.next_channel + 1) % CHANNEL_COUNT
        self.pending.clear()
        self.active = False
        return emissions
