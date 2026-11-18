#!/usr/bin/env python3
"""Draw one captured `map/get_map` answer as a PNG. Standard library only.

It follows the reading in docs/MAP-FORMAT.md, which was observed on ONE robot (Freo Z Ultra,
CX7, firmware v01.13.11.02). Other models may pack the map differently; treat a wrong picture
as a finding and report it.

Usage::

    python3 tools/map_render.py tools/samples/cx7-get-map.hex out.png
    python3 tools/map_render.py tools/samples/cx7-get-map.hex --info
    python3 tools/map_render.py answer.bin out.png --scale 6
    python3 tools/map_render.py --fetch HOST --device-id ID --product-key KEY out.png --save my.hex

With `--fetch` the tool asks the robot itself: ONE read-only `map/get_map` request over the
local WebSocket (port 9002), nothing else and no keep-alive. Without it, the input file holds
one answer, as hex text or as raw bytes (detected). The cloud envelope (byte 0x01, a length,
a small protobuf) and the outer `{1: 1, 2: <map>}` wrapper may each be present or absent.

The picture: x to the right and y up, as the app shows the map. Rooms are coloured by room id
(cell value >> 8) with the id as a small number, walls are dark, carpet cells (flag 4) are
dotted, cells with flag 16 are shaded, no-go zones (field 9) are red outlines and the dock
(field 8) is a green square. The track of the current or last job (field 13), when the answer
holds one, is a thin blue line; `--no-path` leaves it out.
"""

from __future__ import annotations

import argparse
import base64
import os
import socket
import struct
import sys
import time
import zlib
from collections.abc import Callable
from pathlib import Path

ROOM_TYPES = (
    "Custom", "Master bedroom", "Secondary bedroom", "Living room", "Kitchen", "Bathroom",
    "Toilet", "Balcony", "Dining room", "Closet", "Hallway", "Study", "Kids' room",
    "Entertainment room", "Storage room", "Others",
)  # fmt: skip
ZONE_TYPES = {1: "no vacuum", 2: "no mop", 3: "no vacuum and no mop"}
PALETTE = (
    (214, 232, 250), (250, 226, 205), (215, 240, 214), (240, 214, 236),
    (250, 244, 200), (210, 238, 238), (226, 220, 250), (240, 228, 214),
)  # fmt: skip
BACKGROUND, WALL, CARPET = (238, 238, 238), (60, 60, 60), (150, 110, 70)
ZONE, DOCK, INK, PATH = (215, 30, 30), (0, 150, 0), (0, 0, 0), (30, 80, 220)
# Digits 0 to 9, five rows each, a row being three pixels as one number (4 = left, 1 = right).
DIGITS = ("75557", "26227", "71747", "71717", "55711", "74717", "74757", "71111", "75757", "75717")
Fields = dict[int, list]
Colour = tuple[int, ...]
EPILOG = """\
Ask the robot: --fetch HOST --device-id ID --product-key KEY sends ONE read-only map/get_map
request to ws://HOST:9002, topic /<product key>/<device id>/map/get_map, reads the answer and
closes. It sends nothing else and no keep-alive. Use YOUR device id and your model's product
key. The robot accepts one connection per IP address: disable the Home Assistant config entry
first if you run this on the same host. --save FILE keeps the answer as hex for later.

Or draw a saved answer: the answer to one map/get_map request, whole, as it came off the wire,
as hex text or raw bytes. A leading envelope (byte 0x01, a length byte, that many bytes) is
removed for you: that covers the local answer frame (01 02 2a 00, then the body) and the cloud
form. WebSocket framing is not removed from a file. See docs/MAP-FORMAT.md, "Rendering a map
yourself".

The picture also shows the track of the current or last job when the answer holds one (most
points right after a job; --no-path leaves it out).

On the one unit this was written against the answer is about 16 KB when idle and up to 64 KB
during a long job. Anything else gives: "not a map/get_map answer".
"""


def varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read one varint; return (value, next position)."""
    value = shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, pos


def fields(data: bytes) -> Fields:
    """Decode one protobuf message without a schema: {field number: [values]}."""
    out: Fields = {}
    pos = 0
    while pos < len(data):
        key, pos = varint(data, pos)
        number, wire = key >> 3, key & 7
        if number == 0 or wire not in (0, 1, 2, 5):
            raise ValueError("not a protobuf message")
        if wire == 0:
            value, pos = varint(data, pos)
        elif wire == 2:
            size, pos = varint(data, pos)
            value, pos = data[pos : pos + size], pos + size
        else:
            size = 4 if wire == 5 else 8
            (value,) = struct.unpack("<f" if wire == 5 else "<d", data[pos : pos + size])
            pos += size
        if pos > len(data):
            raise ValueError("truncated protobuf message")
        out.setdefault(number, []).append(value)
    return out


def signed(value: int) -> int:
    """Negative whole numbers travel as 64-bit two's complement."""
    return value - (1 << 64) if value >= 1 << 63 else value


def point(data: bytes) -> tuple[float, float]:
    """A {1: x, 2: y} pair; a coordinate of exactly 0 has no field."""
    msg = fields(data)
    x_val, y_val = msg.get(1, [0])[0], msg.get(2, [0])[0]
    return (
        signed(x_val) if isinstance(x_val, int) else x_val,
        signed(y_val) if isinstance(y_val, int) else y_val,
    )


def request_frame(product_key: str, device_id: str, short_topic: str = "map/get_map") -> bytes:
    """The robot's request frame: 01, len(topic) + 2, 22, len(topic), topic, empty body."""
    topic = f"/{product_key.strip('/')}/{device_id}/{short_topic}".encode()
    return bytes([0x01, len(topic) + 2, 0x22, len(topic)]) + topic


def ws_frame(data: bytes, mask: bytes) -> bytes:
    """One masked binary WebSocket frame, as a client must send it (RFC 6455)."""
    size = len(data)
    if size < 126:
        head = bytes([0x82, 0x80 | size])
    elif size < 1 << 16:
        head = bytes([0x82, 0x80 | 126]) + struct.pack(">H", size)
    else:
        head = bytes([0x82, 0x80 | 127]) + struct.pack(">Q", size)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def ws_message(read: Callable[[int], bytes]) -> bytes:
    """Read one whole WebSocket message: 7, 16 or 64-bit lengths, continuation frames."""

    def exact(count: int) -> bytes:
        data = read(count)
        if len(data) != count:
            raise ConnectionError("the robot closed the connection")
        return data

    message, done = b"", False
    while not done:
        first, second = exact(2)
        size = second & 0x7F
        if size == 126:
            (size,) = struct.unpack(">H", exact(2))
        elif size == 127:
            (size,) = struct.unpack(">Q", exact(8))
        mask = exact(4) if second & 0x80 else b""
        data = exact(size)
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        opcode = first & 0x0F
        if opcode == 8:
            reason = data[2:].decode(errors="replace")
            raise ConnectionError(f"the robot closed the connection: {reason}")
        if opcode in (0, 1, 2):  # continuation, text, binary; pings and pongs are skipped
            message, done = message + data, bool(first & 0x80)
    return message


def fetch(host: str, device_id: str, product_key: str, timeout: float) -> bytes:
    """Send one map/get_map request to the robot and return its answer frame."""
    try:
        with socket.create_connection((host, 9002), timeout=timeout) as sock:
            key = base64.b64encode(os.urandom(16)).decode()
            sock.sendall(
                f"GET / HTTP/1.1\r\nHost: {host}:9002\r\nUpgrade: websocket\r\n"
                f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n".encode()
            )
            stream = sock.makefile("rb")
            status = stream.readline()
            if b" 101 " not in status:
                sys.exit(f"{host}: no WebSocket here, the answer began {status[:60]!r}")
            while stream.readline() not in (b"\r\n", b"\n", b""):
                pass  # the rest of the handshake's headers
            sock.sendall(ws_frame(request_frame(product_key, device_id), os.urandom(4)))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:  # a broadcast may come first (tag 0x22)
                answer = ws_message(stream.read)
                if answer[:1] == b"\x01" and answer[2:3] == b"\x2a":  # the answer frame
                    return answer
            raise TimeoutError
    except ConnectionRefusedError:
        sys.exit(f"{host}: connection refused on port 9002 (wrong address, or robot offline?)")
    except TimeoutError:
        sys.exit(
            f"{host}: no answer within {timeout:g} s. Check the device id and the product key; "
            "the robot answers only to its own topic, and a sleeping robot may not answer."
        )
    except OSError as err:
        sys.exit(f"{host}: {err}")


def unhex(data: bytes) -> bytes:
    """A file may hold the answer as hex text (whitespace allowed) or as raw bytes."""
    try:
        return bytes.fromhex(data.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return data


def load_map(data: bytes, source: str) -> Fields:
    """Return the fields of the map message itself from an answer in any accepted form."""
    try:
        if data[:1] == b"\x01":  # cloud envelope: 0x01, length, header
            size, pos = varint(data, 1)
            data = data[pos + size :]
        msg = fields(data)
        if 17 not in msg and isinstance(msg.get(2, [0])[0], bytes):
            msg = fields(msg[2][0])  # outer {1: 1, 2: <map>}
    except (ValueError, IndexError, struct.error):
        msg = {}
    if not all(key in msg for key in (4, 5, 6, 17)):
        sys.exit(f"{source}: not a map/get_map answer (no grid, size or extent found)")
    return msg


def grid(msg: Fields) -> list[int]:
    """Field 17: zlib around {1: packed varints}, one value per cell, rows from y min."""
    packed = fields(zlib.decompress(msg[17][0]))[1][0]
    cells, pos = [], 0
    while pos < len(packed):
        value, pos = varint(packed, pos)
        cells.append(value)
    if len(cells) != msg[4][0] * msg[5][0]:
        sys.exit(f"grid holds {len(cells)} cells, expected {msg[4][0]} x {msg[5][0]}")
    return cells


def zones(msg: Fields) -> list[tuple[int, int, list[tuple[float, float]]]]:
    """Field 9: (id, type, corners) per no-go zone."""
    out = []
    for raw in msg.get(9, []):
        zone = fields(raw)
        out.append((zone.get(3, [0])[0], zone.get(2, [0])[0], [point(p) for p in zone[1]]))
    return out


def track(msg: Fields) -> list[tuple[float, float]]:
    """Field 13: {1: packed float32 x, 2: packed float32 y}, the job's track, in cells."""
    if not msg.get(13):
        return []
    packed = fields(msg[13][0])
    raw_x, raw_y = (packed.get(k, [b""])[0] for k in (1, 2))
    count = min(len(raw_x), len(raw_y)) // 4
    xs = struct.unpack(f"<{count}f", raw_x[: count * 4])
    ys = struct.unpack(f"<{count}f", raw_y[: count * 4])
    return list(zip(xs, ys, strict=True))


def info(msg: Fields) -> None:
    extent = fields(msg[6][0])
    y_min, y_max, x_min, x_max = (signed(extent[k][0]) for k in (1, 2, 3, 4))
    print(f"map id {msg.get(1, [0])[0]}, edit version {msg.get(33, ['?'])[0]}")
    print(f"{msg[4][0]} x {msg[5][0]} cells of {msg.get(3, ['?'])[0]} mm")
    print(f"x {x_min}..{x_max}, y {y_min}..{y_max}; dock at {point(fields(msg[8][0])[1][0])}")
    for raw in msg.get(12, []):
        room = fields(raw)
        kind = room.get(2, [0])[0]
        name = room[3][0].decode("utf-8", "replace") if room.get(3) else ""
        label = ROOM_TYPES[kind] if kind < len(ROOM_TYPES) else "?"
        print(f"room {room[1][0]}: type {kind} ({label})" + (f', named "{name}"' if name else ""))
    for zone_id, kind, corners in zones(msg):
        text = " ".join(f"({x:g}, {y:g})" for x, y in corners)
        print(f"no-go zone {zone_id}: type {kind} ({ZONE_TYPES.get(kind, '?')}), corners {text}")
    print(f"track: {len(track(msg))} points")


def write_png(path: Path, rows: list[bytearray], width: int) -> None:
    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    head = struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0)
    png = chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + png)


def render(msg: Fields, scale: int, with_path: bool = True) -> tuple[list[bytearray], int]:
    width, height = msg[4][0], msg[5][0]
    extent = fields(msg[6][0])
    y_max, x_min = signed(extent[2][0]), signed(extent[3][0])
    cells = grid(msg)
    rows = [bytearray(BACKGROUND * (width * scale)) for _ in range(height * scale)]

    def put(px: int, py: int, colour: Colour) -> None:
        if 0 <= px < width * scale and 0 <= py < height * scale:
            rows[py][px * 3 : px * 3 + 3] = bytes(colour)

    def to_px(x: float, y: float) -> tuple[int, int]:  # the centre of cell (x, y); y grows upward
        return round((x - x_min + 0.5) * scale), round((y_max - y + 0.5) * scale)

    sums: dict[int, list[int]] = {}
    for index, value in enumerate(cells):
        room, flags = value >> 8 & 0xFF, value & 0xFF
        if not value:
            continue
        col, row = index % width, height - 1 - index // width
        colour = PALETTE[(room - 1) % len(PALETTE)] if room else WALL
        if room and flags & 16:
            colour = tuple(c * 85 // 100 for c in colour)
        if room:
            total = sums.setdefault(room, [0, 0, 0])
            total[0], total[1], total[2] = total[0] + col, total[1] + row, total[2] + 1
        for dy in range(scale):
            for dx in range(scale):
                dotted = room and flags & 4 and (dx + dy) % 2 == 0 and dx % 2 == 0
                put(col * scale + dx, row * scale + dy, CARPET if dotted else colour)
    def line(start: tuple[float, float], end: tuple[float, float], colour: Colour) -> None:
        (ax, ay), (bx, by) = to_px(*start), to_px(*end)
        steps = max(abs(bx - ax), abs(by - ay), 1)
        for i in range(steps + 1):
            put(ax + (bx - ax) * i // steps, ay + (by - ay) * i // steps, colour)

    for _, _, corners in zones(msg):
        for start, end in zip(corners, corners[1:] + corners[:1], strict=True):
            line(start, end, ZONE)
    points = track(msg) if with_path else []
    for start, end in zip(points, points[1:], strict=False):
        line(start, end, PATH)
    dock_x, dock_y = to_px(*point(fields(msg[8][0])[1][0]))
    for dy in range(-scale, scale + 1):
        for dx in range(-scale, scale + 1):
            put(dock_x + dx, dock_y + dy, DOCK)
    size = max(1, scale // 2)  # room ids, 3 x 5 blocks per digit, at each room's centre of mass
    for room, (col_sum, row_sum, count) in sums.items():
        left = col_sum * scale // count - len(str(room)) * 2 * size
        top = row_sum * scale // count - 2 * size
        for n, digit in enumerate(str(room)):
            for r, code in enumerate(DIGITS[int(digit)]):
                for c in range(3):
                    if int(code) >> (2 - c) & 1:
                        x0, y0 = left + (n * 4 + c) * size, top + r * size
                        for k in range(size * size):
                            put(x0 + k % size, y0 + k // size, INK)
    return rows, width * scale


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Draw a captured map/get_map answer as a PNG.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths", type=Path, nargs="*", metavar="FILE", help="ANSWER [PNG]; with --fetch only [PNG]"
    )
    parser.add_argument("--scale", type=int, default=4, help="pixels per cell (default 4)")
    parser.add_argument("--info", action="store_true", help="print what the map holds and exit")
    parser.add_argument("--no-path", action="store_true", help="do not draw the job's track")
    parser.add_argument("--fetch", metavar="HOST", help="ask the robot at HOST (port 9002)")
    parser.add_argument("--device-id", help="your robot's device id (with --fetch)")
    parser.add_argument("--product-key", help="your model's product key (with --fetch)")
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds to wait (default 10)")
    parser.add_argument("--save", type=Path, metavar="FILE", help="also keep the answer, as hex")
    args = parser.parse_args()
    paths = list(args.paths)
    if args.fetch:
        if not args.device_id or not args.product_key:
            parser.error("--fetch needs --device-id and --product-key")
        data, source = fetch(args.fetch, args.device_id, args.product_key, args.timeout), args.fetch
    elif not paths:
        parser.error("give a file with a map/get_map answer, or --fetch HOST")
    else:
        source = str(paths[0])
        data = unhex(paths.pop(0).read_bytes())
    msg = load_map(data, source)
    if args.save:
        args.save.write_text(data.hex() + "\n")
        print(f"saved the answer to {args.save}")
    png_path = paths[0] if paths else None
    if args.info:
        info(msg)
        return
    if png_path is None or args.scale < 1:
        parser.error("give a PNG path to write (or --info), and a scale of 1 or more")
    rows, width = render(msg, args.scale, not args.no_path)
    write_png(png_path, rows, width)
    print(f"wrote {png_path}: {width} x {len(rows)} px")


if __name__ == "__main__":
    main()
