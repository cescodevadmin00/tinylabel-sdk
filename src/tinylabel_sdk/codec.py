"""Small Tiny packet codec; no transport or completion assumptions."""
from dataclasses import dataclass


def crc8(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value << 1) ^ 7) & 255 if value & 128 else (value << 1) & 255
    return value


def packet(opcode: int, data: bytes, *, response: bool = False) -> bytes:
    if not 0 <= opcode <= 255 or len(data) > 65535:
        raise ValueError("Invalid Tiny frame")
    return b"\x51\x78" + bytes([opcode, int(response)]) + len(data).to_bytes(2, "little") + data + bytes([crc8(data), 255])


@dataclass(frozen=True)
class Frame:
    opcode: int
    response: bool
    data: bytes


class Decoder:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[Frame]:
        self.buffer.extend(data)
        result = []
        while self.buffer:
            at = self.buffer.find(b"\x51\x78")
            if at < 0:
                self.buffer[:] = self.buffer[-1:] if self.buffer[-1:] == b"\x51" else b""
                break
            del self.buffer[:at]
            if len(self.buffer) < 6:
                break
            length = int.from_bytes(self.buffer[4:6], "little")
            if length > 4096:  # U1 replies are short; reject an impossible receive frame.
                del self.buffer[0]
                continue
            if len(self.buffer) < length + 8:
                break
            frame = bytes(self.buffer[:length+8])
            if frame[-1] != 255 or crc8(frame[6:-2]) != frame[-2]:
                del self.buffer[0]
                continue
            result.append(Frame(frame[2], frame[3] == 1, frame[6:-2]))
            del self.buffer[:length+8]
        return result
