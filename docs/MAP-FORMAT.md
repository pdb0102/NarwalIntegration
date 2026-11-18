# Map format and map editing, as seen on one Freo Z Ultra

> **Scope: one unit.** Everything here was observed on ONE robot: a Narwal Freo Z Ultra
> (hardware CX7, product key `hEA7OEshlx`, firmware v01.13.11.02), ONE account in the US
> region, the iOS app 2.10.90, between 2026-11-13 and 2026-11-17. Three vantage points were
> recorded at once: a read-only listener on Narwal's cloud MQTT broker (the app's commands and
> the robot's answers), the robot's local WebSocket on port 9002, and the phone's web traffic
> through an intercepting proxy. **Nothing was tested on any other model or firmware.** This is
> evidence, not a specification. Where it differs from [PROTOCOL.md](PROTOCOL.md), both
> observations stand side by side; this document does not replace anything there.
> (CX7 v01.13.11.02; @pdb0102, 2026-11)

Confidence marks used below:

- **P**: confirmed by an app action. The owner did one thing in the app and that message was
  captured, or the same number was seen on both sides of a comparison.
- **L**: likely. Matched by value or by position, not by a controlled change.
- **G**: a guess.

Field numbers are protobuf field numbers, decoded without a schema. Bodies are shown without
the cloud envelope (`0x01`, length, sender ids): what remains is the command's own protobuf,
the same bytes the local WebSocket carries. Times are the capture's local wall clock. The map
contains no device or account id (checked); none appears in this document.

Room ids in the examples: **the rooms were renumbered on 2026-11-16 at 21:15:28** by a merge
(see [Split/merge](#splitmerge-operation-fields-1-and-2)). Examples before that moment use the
old numbering (1 Living Room, 2 Master bedroom, 3 Bathroom, 4 Closet, 5 Hallway, 6 Toilet);
examples after 21:26 use the new one (1 Master bedroom, 2 Bathroom, 3 Closet, 4 Hallway,
5 Toilet, 6 Living Room, 7 Kitchen).

Contents: [1. The map message](#1-the-map-message) ·
[2. The grid](#2-the-grid-field-217) · [3. Units](#3-units-positions-are-in-cells-of-60-mm) ·
[4. Rooms](#4-rooms-field-212) ·
[5. Zones, carpets, doors, furniture, objects](#5-no-go-zones-carpets-doors-furniture-objects) ·
[6. Editing: `map/operation`](#6-editing-mapoperation) ·
[7. Live position and planned route](#7-live-position-and-planned-route) ·
[8. The map-update viewer](#8-the-map-update-viewer-mapcheck_map_update_info) ·
[9. Evidence](#9-evidence)


---

## 1. The map message

Five answers on this unit carry the same map message; they differ in the wrapper and in which
fields are filled.

| Topic | Request body | Answer | Size here |
|---|---|---|---|
| `map/get_map` | `08001000` = `{1: 0, 2: 0}` (as the app sends it) | `{1: 1, 2: <map>, 3: 1}` | 14 to 64 KB; by day below |
| `map/get_editable_map` | `080110001800` = `{1: 1, 2: 0, 3: 0}` | `{1: 1, 2: <map>, 3: <edit version>, 4: {1: 50}}` | 12.5 to 14.5 KB (86 answers) |
| `map/get_all_reduced_maps` | empty | `{1: 1, 2: <map>}`; one map is saved on this unit | 36 to 43 KB (147 answers) |
| `map/check_map_update_info` | empty | `{2: <map>}` (see [section 8](#8-the-map-update-viewer-mapcheck_map_update_info)) | 15.9 KB (seen once) |
| `map/operation` | see [section 6](#6-editing-mapoperation) | `{1: 1, 2: <map>, 3: <new edit version>}` | 12.5 to 13.9 KB (68 answers) |

PROTOCOL.md §5 gives ~80 KB for `map/get_map` and ~169 KB for `map/get_all_reduced_maps`.
On this unit both were smaller; the map covers one floor, about 70 m² of mapped room cells,
and it is the only saved map. **`map/get_map` grows during a long job:**

| Capture | `map/get_map` answers | Smallest | Largest |
|---|---|---|---|
| 2026-11-13, a whole-house job of several hours | 33 | 13,981 bytes (09:27:40) | 63,917 bytes (14:24:00) |
| 2026-11-13, afternoon, short jobs | 68 | 15,632 | 20,542 |
| 2026-11-16, one short job, then map editing | 11 | 15,682 | 16,500 |
| 2026-11-17, short jobs | 22 | 15,864 | 17,597 |

In the 63,917-byte answer the track (field 2.13) is 37,776 bytes, the grid (2.17) 7,194
against 4,482 at the start, the carpets (2.26) 10,465, and a field 2.31 that was not read
holds 6,109. The field table below was read from the maps of 2026-11-16 and 2026-11-17.

`map/get_editable_map` also answers over the local socket with no account (2026-11-16, P).
`map/get_map` was read over the broker only.

### Fields of the map (all inside field 2 of the answer)

"Narwal's name" is the JSON key that holds the same value in the app's cleaning report
(`GET …/clean-record-app-server/v1/clean-record/detail`, see [CLOUD-API.md](CLOUD-API.md)),
read on 2026-11-17 for one job. **Every name is matched by content only (L)**: the same
numbers stand in the protobuf field and under the JSON key. Two matches are exact to the byte
and noted as such.

| Field | Holds (this unit's value) | Mark | Narwal's name (L, by content) | PROTOCOL.md §8 |
|---|---|---|---|---|
| 2.1 | Map id (1) | L | `map_id` | agrees |
| 2.2 | Map version (120; 121 from 2026-11-17 15:02) | L | `map_version` | not listed |
| 2.3 | Cell size in mm (60) | P | `resolution` | agrees ("Resolution") |
| 2.4, 2.5 | Width, height in cells (155, 344) | P | `width`, `height` | agrees |
| 2.6 | The grid's extent `{1: y min, 2: y max, 3: x min, 4: x max}` = (−224, 119, −90, 64) | P (119 − (−224) + 1 = 344; 64 − (−90) + 1 = 155) | `border {bottom, top, left, right}` | agrees on 6.1 and 6.3 as the origin; 6.2 and 6.4 are the far edges |
| 2.7 | `{1: {1: x, 2: y}, 2: angle}` = (−7.69, −9.11), −0.0054 rad. What it denotes: not read | L for the name only | `origin {location {x, y}, theta}` | not listed |
| 2.8 | The dock `{1: {1: x, 2: y}, 2: heading}` = (−8.33, 0), heading absent | P | `station {location, theta}` | agrees on the field; the unit differs ([section 3](#3-units-positions-are-in-cells-of-60-mm)) |
| 2.9 | No-go zones, one entry each | P | `forbiddens` | not listed |
| 2.11 | Doors and room dividers, one entry each (6 here) | L | `doors` | agrees |
| 2.12 | Rooms, one entry each (7 here) | P | `room_infos` | agrees, except sub-field 4 ([section 4](#4-rooms-field-212)) |
| 2.13 | The track of the current or last job: `{1: packed float32 x, 2: packed float32 y}` | L; byte-identical to the report's field for the same job | `robot_trajectory` (`robot_trajectory_format: 2`) | agrees |
| 2.15 | 1. Not read | | | |
| 2.17 | The grid, compressed ([section 2](#2-the-grid-field-217)) | P | `map_data`; byte-identical to the report's field (base64 there) | agrees on the field; here it is a zlib stream, not gzip |
| 2.18 | 3 in the full and editable map, 4 in the reduced map | L | `map_data_format` (3 in the report) | not listed |
| 2.20 | 63. Not read | L for the name only | `map_valid_bit` | not listed |
| 2.21 | `{1: −9, 2: −52, 3: 115, 4: 286}`: centre and size of the occupied part of the grid | L | `map_center_align_data {x, y, width, height}` | not listed |
| 2.22 | A counter. It grew by about 0.7 per second through 2026-11-16 (336,029 at 20:09:26, 341,136 at 22:01:12) and started again from a few hundred on 2026-11-17, twice. Not read | | | |
| 2.23 | 1. Not read | | | |
| 2.24 | The same bytes as 2.8 (the dock again). Not read | | | |
| 2.26 | **Carpet areas**, one entry each (8 here) | P | `carpets` | differs: "room boundary polygons, one per room" |
| 2.27 | Sometimes present, one entry: four corners (10, −66) (8, −133) (45, −134) (47, −68), `2: 1`, and one point (48, −98). Present in 14 of the 30 `get_map` answers of the evening of 2026-11-16 and of 2026-11-17: all 8 of 2026-11-16 (robot docked throughout), and on 2026-11-17 at 14:38:03, 15:03:11, 15:14:24, 15:42:33, 16:04:06 and 16:11:44, each with the robot on the dock. Absent in the 16 answers taken during a job or a drive or within seconds of its end. Not read | | | |
| 2.29 | Reduced map only: one outline per room, cell by cell, `{1: [{1: room id, 2: {1: [{1: x, 2: y}]}}]}` (29 KB). It takes the place of the grid; 2.17 is absent | L | | not listed |
| 2.30 | 1. Not read | | | |
| 2.32 | Furniture placed in the map editor `{1: [piece, …]}` | P | `vision_data.funitures` (Narwal's spelling) | agrees that it is editor-placed; differs on the types |
| 2.33 | **Edit version**: the robot raises it by one with each accepted `map/operation` (2773 to 2842 over the capture) | P | none found in the report | differs: "Map area" |
| 2.34 | When the map was made, seconds since epoch (constant) | L | `map_generate_time` | agrees |
| 2.35 | 1. Not read | | | |
| 2.36 | A time in ms since epoch, new in every answer | L | | |

Present in `map/get_map` and absent from the editable map and from an operation's answer:
2.13, 2.15, 2.22, 2.24, 2.27, 2.30, 2.35, 2.36.

**Where this unit differs from PROTOCOL.md §8, in one list.** Theirs stays as written for the
models it came from; each line is this unit's observation beside it.

| PROTOCOL.md §8 | This unit (CX7, `hEA7OEshlx`, v01.13.11.02; one unit) | Section |
|---|---|---|
| Positions in decimetres; transform `(value_dm * 10) / (resolution / 10) - origin` | Positions in cells of 60 mm; `value − origin` | 3 |
| 2.17 gzip-compressed | A zlib stream, header `78 01` | 2 |
| 2.26 room boundary polygons, one per room | Carpet areas, eight for seven rooms | 5 |
| 2.32 type 14 doors, 2 furniture, 28 obstacles | Type = furniture type: 14 sofa, 2 double bed; 28 not seen | 5 |
| 2.33 map area | The edit version, raised by each accepted edit | 6 |
| Room sub-field 4: category, 1 room, 2 utility | Floor material, 1 to 5, absent = none | 4 |

Smaller points, not contradictions: 2.6 also holds the far edges (6.2, 6.4); room sub-field
3 is absent, not empty, when no name was typed; type 10 reads "Hallway" and type 0 "Custom"
in this app. Outside §8: the message sizes of §5 (above), the "decimetres" label in §7
(section 3), and the renderer's reading of flag 0x10 (section 2).

Other keys of the report with no counterpart identified here: `virtual_walls` (null),
`thresholds` (null), `sub_room_infos` (empty), `pet_heat_areas` (empty), `rotate_angle` (0),
`show_station_direction` (1), `uncleaned_zones`, `robot_trapped_points`, `update_map_regions`,
`carpet_change_events`.

### Encodings

- **Whole cells are varints.** A negative number travels as 64-bit two's complement, ten
  bytes: `a0feffffffffffffff01` = −224. Seen in 2.6, 2.11, 2.21, 2.26, 2.29 and in the layout
  edit.
- **Fractional positions are float32** (wire type 5): the dock, no-go zone corners, furniture,
  the track, the dividing line of a split.
- **A zero is left out.** The dock here is `0a050d545505c1` = `{1: {1: −8.333}}`: y is exactly
  0 and has no field, and neither has the heading. The same happens in `map/display_map`
  field 5 and to any float coordinate that is 0.0. A parser that needs both x and y present
  will not find this dock. The integration's `MapData.from_response` tests
  `"1" in pos and "2" in pos` for field 2.8; this was read in the code and not run against
  this unit.

---

## 2. The grid (field 2.17)

(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)

**Packing.** Field 2.17 is a zlib stream (first bytes `78 01`). Unpacked, it is a small
protobuf with one field: `1:` a packed list of varints, **one value per cell**. On this unit:
4,652 bytes in, 76,957 out, 53,320 values = 155 × 344. P

**Order.** Rows from y min upward, each row from x min rightward:

```
value(x, y) = values[(y − y_min) × width + (x − x_min)]      y_min = 2.6.1, x_min = 2.6.3
```

**Value.** `room id × 256 + flags`. Room id 0 means no room. P for the layout: drawn this way
with y upward the picture is the house, recognised by its owner wall for wall.

```python
import zlib
def grid(field_2_17: bytes) -> list[int]:
    raw = zlib.decompress(field_2_17)        # starts 0a 99 d9 04: field 1, length 76,953
    # skip the tag and the length varint, then read varints to the end
    i = 1
    while raw[i] & 0x80: i += 1
    i += 1
    out = []
    while i < len(raw):
        v = s = 0
        while True:
            b = raw[i]; i += 1
            v |= (b & 0x7F) << s; s += 7
            if not b & 0x80: break
        out.append(v)
    return out                                # room = v >> 8 & 0xFF, flags = v & 0xFF
```

**Flags.** Counted on the map of 2026-11-17 14:38:03 (53,320 cells; 28,604 are 0).

| Bit | Value | Seen | Reading | Mark |
|---|---|---|---|---|
| 0 | 1 | on every room cell without bit 4 | open floor | L |
| 1 | 2 | on 1,903 cells, only together with bit 0, only in `map/get_map` | not read; possibly "cleaned" | G |
| 2 | 4 | on 5,233 cells | **carpet** | P, below |
| 3 | 8 | only together with bit 4 (values 25, 29) and on 139 wall cells (40) | not read | |
| 4 | 16 | on 8,659 room cells | floor the robot does not drive on: under furniture and fittings | L, below |
| 5 | 32 | 1,119 cells with room id 0 (values 32 and 40) | wall | L (the walls of the picture) |
| 28 | 0x10000000 | 12 cells in one short row at the dining-end wall, (−23…−13, −193) and (−23, −192) | not read | |

- **Bit 2 is carpet, P.** The owner named the carpeted rooms; every cell inside or on one of
  the eight outlines of field 2.26 has bit 2, and no cell outside them has it: 5,233 cells
  both ways (2026-11-17 14:38:03). One outline is a 30 cm square around an HVAC floor vent, so
  the flag means "the floor sensor read this as carpet".
- **Bit 4, L.** The bed's box in 2.32 (32 × 38 cells after its quarter turn) covers 1,147
  cells; all 1,147 have bit 4. A dresser that is not in 2.32 shows the same way. The
  integration's renderer reads `pixel_type & 0x10` as "wall/border edge"; on this unit these
  cells are whole areas inside rooms.
- **The editable map carries fewer bits.** In `map/get_editable_map` and in an operation's
  answer, bit 1 is never set, and bit 0 is clear wherever bit 4 is set (for example 272 where
  `map/get_map` has 272, 273 or 275). Room id, carpet, bit 3, bit 4 and walls are the same.

**Origin and orientation.** x grows to the right and y upward when the grid is drawn as
above; [MAP-CARD.md](MAP-CARD.md) says the same. Cell (0, 0) is inside the dock's room; the
dock is at (−8.33, 0). P for the orientation: a piece of furniture moved "left and up" in the
app went from (−32.0, −166.2) to (−37.0, −141.6).

**The walls can be moved by hand in "Edit Layout", so they need not be measurement.** The
app lets the owner drag each straight wall of a room. Do not read wall positions to the
centimetre.

### Rendering a map yourself

`tools/map_render.py` draws one `map/get_map` answer as a PNG with the reading above and
nothing else (standard library only). Two real answers from this unit are in `tools/samples/`,
envelope removed: `cx7-get-map.hex` (2026-11-17 16:11:44, 16,084 bytes) and
`cx7-get-map-with-path.hex` (2026-11-17 15:14:22, 17,597 bytes, read at the end of a job in
the Hallway and the Toilet).

```
python3 tools/map_render.py tools/samples/cx7-get-map-with-path.hex out.png
python3 tools/map_render.py tools/samples/cx7-get-map-with-path.hex --info
```

The picture has x to the right and y up, 4 pixels per cell (`--scale N`): rooms coloured by
room id with the id as a small number, walls dark, carpet cells (flag 4) dotted, cells with
flag 16 shaded, no-go zones as red outlines, the dock as a green square. The track of the
current or last job (field 2.13) is a thin blue line; `--no-path` leaves it out. `--info`
prints the size, the cell size, the edit version, the rooms with their types, the zones and
the number of track points; for the second sample: 155 × 344 cells of 60 mm, edit version
2841, seven rooms, two zones, 152 track points.

**The track, checked.** Field 2.13 is `{1: packed float32 x, 2: packed float32 y}`, one
point per corner of the route, in cells. In the second sample all 152 points lie on room
cells: 92 in room 4 (Hallway) and 60 in room 5 (Toilet), the two rooms of that job. In the
answer of 16:11:39, the end of a job on a drawn rectangle (7, 3) to (19, −13), 43 of 54 points
lie in the rectangle and the other 11 on the way from the dock. The field holds most right
after a job: 1 point at 16:11:44, five seconds later.

**Asking your own robot.** The tool can make the request itself:

```
python3 tools/map_render.py --fetch <robot address> --device-id <your device id> \
    --product-key <your product key> out.png --save my-map.hex
```

- It opens the local WebSocket (port 9002), sends ONE read-only `map/get_map` request with an
  empty body to `/<product key>/<device id>/map/get_map`, reads the answer and closes. It
  sends nothing else and no keep-alive. `--timeout` is 10 s by default.
- Use **your own** device id and your model's product key ([PROTOCOL.md](PROTOCOL.md) §1 and
  §3; `KNOWN_PRODUCT_KEYS` in `narwal_client/const.py`). The names are those of the
  project's client (`device_id`, and the product key that forms its `topic_prefix`).
- The robot accepts one connection per IP address ([PROTOCOL.md](PROTOCOL.md) §1): disable
  the Home Assistant config entry first if you run this on the same host.
- `--save` keeps the answer as hex, to draw again or to share. On this unit the map answer
  held no id; the request does, so do not post a capture that still contains it.
- Errors are plain: connection refused, no answer in time (wrong device id or product key, or
  a sleeping robot, [PROTOCOL.md](PROTOCOL.md) §4), or
  `not a map/get_map answer (no grid, size or extent found)`.
- The request frame and the answer parsing were tested offline against recorded answers and
  a stand-in on the loopback address, and the fetch was run once against the CX7
  (2026-11-17): the empty request body, which is what the project's client sends, was
  answered with the full map. The app sends `08001000`.

**Drawing a saved answer instead.** Give the tool a file with the answer to one `map/get_map`
request, whole, as it came off the wire, as hex text or as raw bytes. It removes a leading
envelope by itself (byte `0x01`, a length byte, that many bytes, then the body): that covers
the local answer frame, `01 02 2a 00` followed by the body ([PROTOCOL.md](PROTOCOL.md) §2),
and the cloud form. It does not remove WebSocket framing from a file. On this unit the answer
is about 16 KB when idle and up to 64 KB during a long job (section 1). Two other ways to
come by such a file, neither run by us for this purpose:

1. *The project's client.* `NarwalClient.send_command("map/get_map", timeout=15.0)`
   (`narwal_client/client.py`) returns a `CommandResponse` whose `raw_payload` is the
   answer's body; write those bytes to a file.
2. *A capture.* `tools/CAPTURE_GUIDE.md` describes recording the plaintext WebSocket on port
   9002 with Wireshark while the app is open. Save the one binary message that follows the
   `map/get_map` request: it begins `01 02 2a 00`.

---

## 3. Units: positions are in cells of 60 mm

(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)

On this unit **every coordinate read so far is in the grid's own cells, and one cell is
60 mm**: the dock (2.8), no-go zones (2.9), doors (2.11), carpets (2.26), furniture (2.32),
the track (2.13), `map/display_map` positions and trail, `status/point_navi_plan_traj`, the
zones of `clean/start_clean`, and every coordinate in `map/operation`. Grid index =
value − origin, with no scale factor.

### Where this agrees with the project

- 2.3 = 60 is the resolution. Agreed.
- 2.6.1 and 2.6.3 are the origin offsets, and `pixel = value − origin`. This is what the
  integration's code does (`overlay_to_grid` in `narwal_client/models.py` returns
  `value − origin`) and what [MAP-CARD.md](MAP-CARD.md) states ("map grid coordinates, the same
  units the robot reports").

### Where this differs

PROTOCOL.md labels `map/display_map` 1.1 and the dock field 2.8 "decimetres", and its
"Coordinate transform" section gives

```
pixel = (value_dm * 10) / (resolution / 10) - origin
```

With a resolution of 60 that formula multiplies every value by 10/6. On this unit that puts
positions in the wrong place; the values are cells already. That section also says "some
other map fields are centimetres": on this unit no map field in centimetres was found. The
other models that the decimetre reading came from were not tested here, so that statement is
left standing for them.

### The evidence

| What | Result | Mark |
|---|---|---|
| Narwal's own report for a job on this map | `"resolution": 60`, `"width": 155`, `"height": 344`, `"border": {"bottom": -224, "top": 119, "left": -90, "right": 64}`, with zone corners, doors, carpets and furniture as the same numbers the protobuf carries | L for the unit of `resolution` (mm per cell); it is the only reading that fits the rows below |
| Live positions against the grid, first run (2026-11-13), 12,282 non-zero `map/display_map` positions | read as cells: 12,282 of 12,282 lie on a room cell. Scaled by 10/6: 6,148 of 12,282. Method: each position rounded to the nearest cell and looked up in the grid of 2026-11-17 14:38:03; a hit is a cell with a room id. Against the grid of 2026-11-16 20:09:26 the scaled count is 6,185 (the unscaled one stays 12,282); rounding down instead gives 6,132 and 6,155. About half, whichever way | P |
| The same for 2026-11-17, 1,828 positions | read as cells: 1,828 of 1,828. Scaled by 10/6: 1,556 (same method, same grid) | P |
| The app's ruler | a no-go zone the app displayed as "2.5 m × 3.4 m" has corners 42 × 57 cells apart: 2.52 m × 3.42 m at 60 mm | P |
| The app's default sizes | a new no-go zone is 25 × 25 cells (the app: 1.5 m × 1.5 m); a bar chair is 8.333 cells (0.5 m); the dock is at x = −8.333 (0.5 m) | L |
| "Edit Layout" | the app's step of "0.1 m" moved a wall by one cell | L |
| A drawn zone job | a rectangle of about 0.7 × 1 m on the app's screen was sent as (7, 3) to (19, −13): 12 × 16 cells = 0.72 × 0.96 m | P |
| The house, measured with a tape and drawn to scale | see below | P |

**Against the house plan.** The owner's plan of the house (a dimensioned drawing, and later a
true-scale one checked with a tape), turned a quarter turn and scaled to 60 mm per cell, lies
on the grid. Measured on the grid against the dimensioned drawing: whole
length 284 cells = 17.04 m (plan 16.94 m); open space across 113 cells = 6.78 m (6.76 m);
bedroom 70 cells = 4.20 m (4.19 m); closet 53 cells = 3.18 m (3.15 m); a bathroom 25 × 23
cells = 1.50 × 1.38 m (1.45 × 1.37 m); dining end 60 cells = 3.60 m (3.60 m).

So the 60 mm cell holds across the house to about 1 %. A single wall of a map can still be
off by several cells (see "Edit Layout" above); that is the map's doing, not the unit's.


---

## 4. Rooms (field 2.12)

(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)

The seven records on 2026-11-17, whole:

```
080110013801        {1: 1, 2: 1, 7: 1}          Master bedroom, heavily soiled, no floor material
080210052002        {1: 2, 2: 5, 4: 2}          Bathroom, tile
08031009            {1: 3, 2: 9}                Closet
0804100a2002        {1: 4, 2: 10, 4: 2}         Hallway, tile
0805100620023001    {1: 5, 2: 6, 4: 2, 6: 1}    Toilet, tile
080610032002        {1: 6, 2: 3, 4: 2}          Living Room, tile
0807100420023001    {1: 7, 2: 4, 4: 2, 6: 1}    Kitchen, tile
```

| Sub-field | Meaning on this unit | Mark | Narwal's name (L, by content) | PROTOCOL.md §8 |
|---|---|---|---|---|
| 1 | Room id | P | `room_id` | agrees |
| 2 | Room type, 0 to 15. Absent when 0 | P, all sixteen sent by the app and read back | `type` | agrees |
| 3 | A name typed by the owner, UTF-8. **Absent, not empty, unless one was typed** | P | `custom_name` | agrees ("empty if never named") |
| 4 | **Floor material**: 1 wood, 2 tile, 3 cobblestone, 4 tatami, 5 marble; absent = none set | P, all six choices sent and read back | `texture` | differs: "Category: 1 = room, 2 = utility/small space" |
| 5 | Direction of the wood grain in degrees: 0, 90 or 180 | P | `texture_direction_angle` | not listed |
| 6 | Set by the robot, not by the owner: 1 while the room's type is Kitchen (4), Toilet (6), Balcony (7) or Dining room (8) | P for the pattern | `is_default_heavy_dirty_room` (true for exactly the two rooms that carry `6: 1`) | not listed |
| 7 | "Room character": 1 = "Heavily Soiled Room"; absent or 0 = "No character" | P | `is_customize_heavy_dirty_room` (true for the one room with `7: 1`) | not listed |
| 8 | The number the app puts after a name when rooms share a type ("Toilet1", "Toilet2", "Toilet3"). Absent when the room is alone in its type. Set by the robot | P | possibly `room_type_id` (0 for all rooms in the one report read, where no type was shared) | agrees ("instance index") |
| 10 | Sent as 0 by the "Room character" tool only; never seen in the map | not read | | |

**Room types and names.** The app's list in "Room naming", in the app's order, is the type
list 0 to 15. The owner walked one room through the whole list, one save each
(2026-11-16 20:59:24 to 21:02:45), and the robot received 15, 0, then 1, 2, 3 … 14 in that
order. P for all sixteen.

| 0 Custom | 1 Master bedroom | 2 Secondary bedroom | 3 Living Room |
|---|---|---|---|
| **4** Kitchen | **5** Bathroom | **6** Toilet | **7** Balcony |
| **8** Dining room | **9** Closet | **10** Hallway | **11** Study |
| **12** Kids' room | **13** Entertainment room | **14** Storage room | **15** Others |

This is the table PROTOCOL.md §8 gives after the correction recorded in its §10 ("The
room-name table was wrong for everyone"). The numbers agree for all sixteen. The wording
differs in two places only: the iOS app 2.10.90 shows "Hallway" for 10 where the table has
"Corridor", and "Custom" for 0 where the table has "Room".

**For issue [#143](https://github.com/sjmotew/NarwalIntegration/issues/143) (room types),
what this unit shows:**

- The type is 2.12 sub-field 2, a plain varint, on every room of this map.
- **A room that was never given a typed name has no field 3 at all.** All seven rooms above
  are in that state; their names in the app come from the type alone.
- A preset name is sent as the type with an empty field 3
  (`{1: 1, 2: 15, 3: "", 4: 2}`); the map then holds `{1: 1, 2: 15, 4: 2}`.
- A typed name is sent as type 0 with the text in field 3
  (`{1: 1, 2: 0, 3: "Sarah’s room", 4: 2}`); the map then holds
  `{1: 1, 3: "Sarah’s room", 4: 2}`. Field 2 is absent because it is 0. A client that falls
  back to the type when the name is missing, and to the name when the type is missing, covers
  both.
- Two rooms of one type are told apart by field 8, not by the name.

**Room ids are per map and not stable.** A split adds an id. A merge removes one and the
robot then renumbers every room so that the ids run 1 to n without a gap
([Split/merge](#splitmerge-operation-fields-1-and-2)). On this unit five of six rooms changed
their id in one merge. Read the ids from a fresh map before using one.

**Records are not in id order.** After a split the list read 2, 3, 4, 5, 6, 1, 7.

---

## 5. No-go zones, carpets, doors, furniture, objects

(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)

### No-go zones (2.9)

`{1: [four corners {1: x, 2: y}, float32], 2: type, 3: id}`. Narwal's keys:
`forbiddens [{polygon, type, id, room_id, mode}]`; `room_id` and `mode` were 0 and have no
field here.

```
0a0a0d000080c0150000a8c1 0a0a0d0000803f150000a8c1 0a0a0d0000803f1500001cc2 0a0a0d000080c01500001cc2 1003 1801
(−4, −21) (1, −21) (1, −39) (−4, −39), type 3, id 1
```

| Type | The app's label | Mark |
|---|---|---|
| 1 | "No vacuuming" | P |
| 2 | "No mopping" | P |
| 3 | "No Vac & Mop" | P |

Proven by three saves of one zone that differ in that one byte
([No-go zones](#no-go-zones-operation-field-4)). A zone is any four-cornered shape; the robot
keeps whole cells. This app screen offers areas only, **no virtual wall**; none was seen.

### Carpets (2.26)

`{1: id, 2: [outline points {1: x, 2: y}, whole cells], 3: {1: x, 2: y} a point inside, 4: mode}`.
Narwal's keys: `carpets [{id, polygon, center, carpet_clean_option, source,
carpet_modify_polygon}]`; `source` was 0 and `carpet_modify_polygon` empty for all eight.

- The outline walks the carpet's edge cell by cell (16 to 285 points here). The app's "Carpet"
  screen draws exactly these outlines. P
- Eight outlines on a map of seven rooms; they do not follow the rooms. PROTOCOL.md §8 reads
  2.26 as "room boundary polygons, one per room": on this unit that is not what the field
  holds. Per-room outlines are in the reduced map's field 2.29 and in the layout edit.
- **Per-carpet mode (field 4)**, the same numbers as the global setting in
  [SETTINGS.md](SETTINGS.md):

| Mode | The app's name | Mark |
|---|---|---|
| 1 | "Cross" (carpet crossing: drive over it without cleaning) | P, by elimination: the only value and the only name left, and the order of four consecutive saves agrees |
| 2 | "Clean" (vacuum with raised suction) | P: the state before and after |
| 3 | "Vacuum & Mop" | P: a single save |
| 4 | "Avoid" | P: a single save |

- **Carpet ids are not stable either** (seen once, cause not known). The eight outlines,
  compared point for point, are the same in all 30 `map/get_map` answers of the evening of
  2026-11-16 and of 2026-11-17. Their ids were the
  same in the eight answers of 2026-11-16 and at 2026-11-17 14:38:03. In the next reads
  (`map/check_map_update_info` at 15:02:15, `map/get_map` at 15:03:11; map version now 121,
  no job in between) every outline carried another id: 1→5, 2→6, 3→7, 4→8, 5→4, 6→3, 7→2,
  8→1. They stayed so in the remaining 20 answers; at 16:11:39, the end of a job, only the
  order of the entries changed. Identify a carpet by its outline, not by an id kept from
  earlier.

### Doors and dividers (2.11)

`{1: two bytes, the two room ids, 2: [two end points {1: x, 2: y}, whole cells]}`. Narwal's
keys: `doors [{room_ids, door_pts, has_door_sill}]`; `has_door_sill` was false for all six.

```
0a020405 120d080110fcffffffffffffffff01 120408011004        rooms 4 and 5, (1, −4) to (1, 4)
```

The dividing line of a split appears here as one more entry between the two new rooms
(`0607`, (−4, −59) to (−4, −134)), with exactly the end points that were sent. L for "door";
P for the divider.

### Furniture (2.32)

`{1: [ {1: id, 2: type, 3: {1: {1: x, 2: y} centre, 2: width, 3: height}, 4: angle, 5: 0} ]}`,
centre and size float32 in cells, angle float32 in degrees. Narwal's keys:
`vision_data.funitures [{id, furniture_type, box {center, width, height}, angle, is_mirrored}]`. Field 5 is likely `is_mirrored` (L).
These are pieces placed in the map editor, as PROTOCOL.md says.

| Id | Type | Centre | Size | Angle | What it is (the owner) |
|---|---|---|---|---|---|
| 1 | 14 | (21.5, 41.5) | 11 × 19 | 180 | a dog bed shaped like a small sofa |
| 2 | 14 | (12.5, −97.5) | 13 × 33 | 180 | the couch |
| 3 | 2 | (−11, 69) | 38 × 32 | 90 | the bed |
| 5 | 76 | (21.8, 78.3) | 20 × 20 | 0 | placed from the app's list: dog house |
| 6 | 18 | (−21.1, −105.2) | 8.33 × 8.33 | 0 | placed from the app's list: bar chair |

**Types.** Confirmed on this unit, each by the owner naming or placing the piece: 2 double
bed, 4 square dining table, 14 sofa, 18 bar chair, 76 dog house (P for these five).
PROTOCOL.md §8 has "type 14 doors, 2 furniture, 28 obstacles": on this unit type 14 is a
sofa-sized box inside a room, twice.

The full list below is **not ours**. It comes from another owner's published code
(marczukmichal/narwal-freo20-ha, `protocol/enums.py`, a Freo 20; see
[Discussion #163](https://github.com/sjmotew/NarwalIntegration/discussions/163)). The five
values above agree with it; the rest was not checked here.

> 0 unspecified · 1 single bed · 2 double bed · 3 baby bed · 4 dinner table, square ·
> 5 dinner table, round · 6 tea table, square · 7 tea table, round · 8 TV cupboard ·
> 9 bedside table · 10 locker · 11 wardrobe · 12 shoe cupboard · 13 sofa, single ·
> 14 sofa, multi-seat · 15 sofa, L shape · 16 lazy sofa · 17 chair · 18 bar chair ·
> 19 cat toilet · 20 pet eating area · 21 pet house · 22 washing machine · 23 refrigerator ·
> 24 standing air conditioner · 25 standing fan · 26 potted plant · 27 floor mirror ·
> 28 toilet · 29 piano · 30 sofa, U shape · 31 desk · 32 grand piano · 33 washbasin ·
> 34 cooker hood and stove · 74 wine cabinet · 75 cat house · 76 dog house ·
> 77 round placeholder · 78 weighing scale

### Detected objects

Objects the robot finds during a job are not in the map message on this unit. They arrive in
`map/display_map` field 7 (7.5 an object just detected: a running number, a class, a position
in cells; 7.6 the objects so far; L) and their photos through `map/get_vision_image`
(see [PROTOCOL.md](PROTOCOL.md)).

- **Ours:** class 1 = Cable (P: the app labelled it so). Class 12 was seen on a blanket
  hanging to the floor (L).
- **From the other owner's table** (the same repository, a label table; not checked here
  beyond class 1): 1 Cable, 4 Liquid, 5 Shoes, 7 Socks, 10 Obstacle, 12 Fabric, 15 Pet,
  18 Chair legs, 20 Mirror, 34 Toy, 37 Pet toy, and more. Its "12 Fabric" fits the blanket.

---

## 6. Editing: `map/operation`

(CX7, `hEA7OEshlx`, v01.13.11.02; iOS app 2.10.90; one unit)

Every tool of the app's map editor ("Map" › "Map management" › "Map editing") sends one
topic, `map/operation`, and the robot answers on `map/operation/response`. 67 operations were
captured over the broker on 2026-11-16 and one on 2026-11-17; **all 68 were answered with
result 1**. One more was sent by us over the local socket and accepted
([below](#sent-over-the-local-socket-and-accepted)). No refusal was ever seen.

```
MapOperation {
  1: map id                 // 1     = the map's field 2.1
  2: map version            // 120   = the map's field 2.2
  3: edit version           // the map's field 2.33 as last read
  4: Operation              // repeated: one entry per change, several kinds may be mixed
       1: split a room
       2: merge two rooms
       3: a room's record   ("Room naming", "Floor material", "Room character")
       4: a no-go zone
       6: a carpet
       8: a piece of furniture
       9: the layout        ("Edit Layout")
  5: 0                      // always sent; not read
  6: 0                      // 1 in the layout edit, 0 in every other; not read
}
Answer { 1: 1, 2: <the whole map after the edit>, 3: <the new edit version> }
```

Operation numbers 1, 2, 3, 6, 8 and 9 are P (each from an app action). 4 is P and agrees with
the other owner's code named in section 5. That code also lists 13 = virtual wall and an
answer field 4 = error code (1 = versions do not match, 9 = bad no-go region): **neither was
seen here**.

**The edit version.** The app sends the number it last read; the robot answers with that
number plus one, and the map's field 2.33 then holds it. The counter went from 2773 to 2841
on 2026-11-16, one step per accepted message, whatever the number of operations inside.

**What the app sends alongside** (P, every edit):

- `map/get_editable_map` before and after each save, so it always edits from the current
  version. The app's furniture move of 20:18:14 carried 2776, the number our own local edit
  had produced three minutes earlier: edits from two clients do not collide as long as each
  reads first.
- Several changes saved together travel as one message with one operation per change.
- After a "Room character" save only: one `config/set` (below).
- After typing a custom room name only: one web call (below).

### Split/merge: operation fields 1 and 2

The app's warning before both: "When you merge or split the room, the original room name,
materials, and cleaning plan may be changed."

**Split.** `4.1 = {1: {1: x, 2: y} first end of the line, 2: {1: x, 2: y} second end, 3: the
room to split, 4: the id for the new part}`, float32 in cells, followed in the same message
by two `4.3` operations: the new room's record and the old room's record. The app chooses the
new id (the highest id plus one). P

```
21:08:55  08011078188c16221e0a1c0a0a0d000080c01500006cc2120a0d000080c015000006c318012007220a1a080a06080710032002220a1a080a0608011003200228003000
  4.1 = {1: {1: −4.0, 2: −59.0}, 2: {1: −4.0, 2: −134.0}, 3: 1, 4: 7}
  4.3 = {1: {1: 7, 2: 3, 4: 2}}        the new room's record
  4.3 = {1: {1: 1, 2: 3, 4: 2}}        the old room's record
```

In the map afterwards room 1 had 5,924 cells and room 7 had 8,543; together 14,467 of the
former 14,474. Both being "Living Room", the robot set `8: 1` and `8: 2`. A divider `0107`
appeared in 2.11. No-go zones, carpets and furniture were unchanged. A split alone left every
other room's id alone.

**Which part keeps the id** (six splits, 21:08 to 21:26; P for these six, a rule by
observation): **the part on the left of the line, looking from its first point to its second
with x to the right and y up, keeps the room's id; the part on the right gets the new id.**
The order of the two points is the order of the app's two handles; dragging them across each
other reverses the line and the outcome.

| Split | Line as sent, first → second | Kept the old id | Got the new id |
|---|---|---|---|
| 21:08:55, room 1 | (−4, −59) → (−4, −134), downward | the +x side, 5,924 cells | 7: the −x side, 8,543 |
| 21:19:23, room 6 | (−54, −136) → (−12, −136), rightward | the upper side, 10,924 | 7: the lower side, 3,480 |
| 21:20:40, room 6 | (−4, −59) → (−4, −134), downward | the +x side, 5,797 | 8: the −x side, 5,121 |
| 21:22:39, room 6 | (−6, −134) → (−6, −59), upward | the −x side, 4,881 | 8: the +x side, 6,037 |
| 21:24:07, room 7 | (−4, −134) → (−4, −59), upward | the −x side, 5,045 | 8: the +x side, 5,873 |
| 21:26:14, room 6 | (−4, −59) → (−4, −134), downward | the +x side, 5,873 | 7: the −x side, 8,542 |

Checked on each answer's grid: every cell that kept the old id lies left of the line or on
it, every cell of the new id lies right of it. The fourth and fifth splits rule out "the part
nearer the dock" and "the larger part".

**Merge.** `4.2 = {1: the room tapped first, 2: the room tapped second, 3: the id the merged
room is to have}`, followed by one `4.3` with the merged room's record. P

```
21:15:28  08011078188e162208120608071001180722101a0e0a0c08071004200228003000380028003000
  4.2 = {1: 7, 2: 1, 3: 7}
  4.3 = {1: {1: 7, 2: 4, 4: 2, 5: 0, 6: 0, 7: 0}}       the result's record: Kitchen, tile
```

| Merge | Sent `{first, second, result}` | Cells before | Then the robot |
|---|---|---|---|
| 21:15:28 | 7, 1, **7** | 7: 8,543 · 1: 5,924 | closed the gap at 1: 2→1, 3→2, 4→3, 5→4, 6→5, 7→6 |
| 21:21:42 | 8, 6, **6** | 8: 5,121 · 6: 5,797 | no gap (8 was the highest): no room changed its id |
| 21:23:21 | 6, 8, **8** | 6: 4,881 · 8: 6,037 | closed the gap at 6: 7→6, 8→7 |
| 21:24:56 | 8, 7, **8** | 8: 5,873 · 7: 5,045 | closed the gap at 7: 8→7 |
| 21:25:30 | 6, 7, **7** | 6: 3,480 · 7: 10,924 | closed the gap at 6: 7→6 |

- **The app asks for the id of the larger room** (five of five) and sends that room's record;
  the order of tapping does not decide it. P for these five.
- **The robot then renumbers so that the ids run 1 to n without a gap, keeping their order.**
  P (four of five merges left a gap, and each was closed; the fifth left none and nothing
  moved). The door list was rewritten to the new ids each time. No-go zones, carpets and
  furniture kept their ids and positions.
- So a merge leaves the other rooms' ids alone only when the id that disappears is the
  highest.
- Any room id a client stored before a merge may point at another room afterwards.

### Room naming: operation field 3, record fields 2 and 3

`4.3 = {1: <room record>}`, and the record is the map's own room record (2.12), sent whole.

```
20:59:24  0801107818f515220c1a0a0a080801100f1a00200228003000                               {1: 1, 2: 15, 3: "", 4: 2}                  "Others"
20:59:40  0801107818f615221a1a180a16080110001a0e5361726168e280997320726f6f6d200228003000   {1: 1, 2: 0, 3: "Sarah’s room", 4: 2}       "Custom", typed
```

- A preset is the type in field 2 with an empty field 3. A typed name is type 0 with the text
  in field 3 (UTF-8; the phone's curly apostrophe travels as typed). P
- The app sends fields 6 and 8 back as it last read them; the robot works both out again from
  the type (section 4). At 21:26:32 the app sent `{1: 6, 2: 3, 3: "", 4: 2, 6: 1, 8: 1}` and
  the map then held `{1: 6, 2: 3, 4: 2}`.
- **Sent alongside, for a typed name only:** before the edit reached the robot the app posted
  the text to a content check on Narwal's web service
  (`POST /base-api-security-server/v1/textContentDetection`, body `{"text": "…"}`, answer
  `"result": true`); see [CLOUD-API.md](CLOUD-API.md). Presets cause no such call. Seen once.

### Furniture management: operation field 8

`4.8 = {1: 1 set / 2 delete, 2: <piece>}`, the piece as in the map's 2.32:
`{1: id, 2: type, 3: {1: {1: x, 2: y}, 2: width, 3: height}, 4: angle, 5: 0}`. P

```
20:10:41 add     0801107818d6152229422708011223080410041a160a0a0d152d00c215543426c3159c0181411d17cee0412500000000280028003000
                 {1: 1, 2: {1: 4, 2: 4, 3: {1: {1: −32.04, 2: −166.20}, 2: 16.13, 3: 28.10}, 4: 0.0, 5: 0}}      a square dining table
20:18:14 move    0801107818d8152229422708011223080410041a160a0a0d812914c215219f0dc3159c0181411d17cee0412500000000280028003000
20:18:28 delete  0801107818d9152227422508021221080410041a160a0a0d7fd6534215904f8243159c0181411d17cee041250000000028003000
```

- **Add** = "set" with a new id. **Move** = the same "set" with the existing id and the new
  centre; type and size repeated.
- **Delete** = `1: 2` with the piece's id, type and size. The centre in it read (53.0, 260.6),
  the old centre plus (90, 402.2): a value in the app's own screen frame, evidently ignored.
  Field 5 is absent.
- **Furniture ids are not reused** (seen once): after piece 4 was deleted the next two were 5
  and 6.
- Two pieces saved together (20:23:28) went as one message with two `4.8` entries.

### Floor material: operation field 3, record fields 4 and 5

The same operation as naming; this tool sends `{1: id, 2: type, 4: material, 5: grain}` and
the fields 6 and 7 the room had.

```
20:29:58  0801107818dc15220e1a0c0a0a08011003200528003801220c1a0a0a080803100520032800220e1a0c0a0a0806100620022800300128003000
          living {1: 1, 2: 3, 4: 5, 5: 0, 7: 1}   bathroom {1: 3, 2: 5, 4: 3, 5: 0}   toilet {1: 6, 2: 6, 4: 2, 5: 0, 6: 1}
20:31:04  0801107818dd15220c1a0a0a08080410092004280028003000        closet {1: 4, 2: 9, 4: 4, 5: 0}
20:33:11  0801107818de15220e1a0c0a0a08011003200128003801220c1a0a0a08080410092000280028003000
          living {1: 1, 2: 3, 4: 1, 5: 0, 7: 1}   closet {1: 4, 2: 9, 4: 0, 5: 0}
```

| Value | The app's name | Mopping pressure shown | The app's note |
|---|---|---|---|
| 0 → absent | "No material" | | |
| 1 | "Wood Floor" | 7 N | "For gentle cleaning in Freo Mind, the mopping humidity will be adjusted to Low." A rotate button sets the grain's direction |
| 2 | "Tile" | 12 N | "For strong cleaning in Freo Mind, the mopping humidity will be adjusted to Normal" |
| 3 | "Cobblestone" | 7 N | "For strong cleaning in the Freo Mind mode, suction power will be increased" |
| 4 | "Tatami" | 7 N | "… suction power will be increased and mop humidity will be auto changed to low" |
| 5 | "Marble" | 12 N | "… mop humidity will be auto changed to low to prevent the water from soaking into the marble" |

- All six choices were sent by the app and read back from the map. P. "No material" is sent
  as `4: 0`; the record then has no field 4.
- **Grain direction, field 5, in degrees.** One press of the rotate button: 0 → 90
  (`…2001 285a 3801…`). Two presses in one visit: 0 → 180 (`28b401`). One more press from a
  saved 180 gave 90 again. Only 0, 90 and 180 were seen; no 270. P for the field; whether the
  value steps back and forth or jumps from 180 to 90 is not settled.

### Carpet: operation field 6

`4.6 = {1: carpet id, 2: mode, 3: 0, 4: [the whole outline, {1: x, 2: y} per point], 5: [four
corners of the outline's bounding box], 7: 0, 8: 0}`. P for fields 1, 2 and 4; fields 3, 5, 7
and 8 are not read.

Seven saves on one carpet (2026-11-16 20:52:20 to 20:55:30), 2,607 bytes each because the
285-point outline travels along. They differ only in the edit version and in the mode's byte:

```
0801107818ed1522a114 329e14 0804 1004 1800 2204080710092204080810 0a …        id 4, mode 4, 3: 0, outline (7, 9) (8, 10) …
modes sent, in order: 4, 1, 3, 2 (four tabs in a row), then 4, 3, 2 (single saves)
```

After each save the map's 2.26 entry for that carpet had the mode sent, and the other seven
stayed at 2. The mode table is in [section 5](#carpets-226).

- The app's banner: "Automatically recognized carpet cannot be moved or stretched". For the
  robot's own carpets only the mode can be set.

### No-go zones: operation field 4

`4.4 = {1: 1 set / 2 delete, 2: {1: [four corners {1: x, 2: y}, float32], 2: type, 3: id}}`,
the zone as in the map's 2.9. P

| What the owner did | Sent | In the map afterwards |
|---|---|---|
| Added a zone, "No Vac & Mop" (20:38:06) | two "set" entries for id 2 in one message: the zone as first dropped, then as he left it, (4, −62)…(46, −119); type 3 | id 2, the second rectangle, type 3 |
| Changed it to "No mopping" (20:38:58) | the same corners, type 2 | type 2 |
| Changed it to "No vacuuming" (20:39:20) | the same corners, type 1 | type 1 |
| Turned it slightly (20:39:45) | corners (21.09, −55.32) (57.45, −76.34) (28.91, −125.68) (−7.45, −104.66) | cut to whole cells: (21, −55) (57, −76) (28, −125) (−7, −104) |
| Straightened it (20:40:46) | two entries for id 2: a nearly straight one, then (4, −62)…(45, −118); type 3 | id 2, (4, −62)…(45, −118), type 3 |

```
20:38:58  0801107818e515223a2238080112340a0a0d0000804015000078c20a0a0d0000384215000078c20a0a0d00003842150000eec20a0a0d00008040150000eec21002180228003000   type 2
20:39:20  0801107818e615223a2238080112340a0a0d0000804015000078c20a0a0d0000384215000078c20a0a0d00003842150000eec20a0a0d00008040150000eec21001180228003000   type 1
20:43:21  add     0801107818e915223a2238080112340a0a0d00001cc2150000f6c20a0a0d000060c1150000f6c20a0a0d000060c115000014c30a0a0d00001cc215000014c31003180328003000
20:43:32  delete  0801107818ea15223a2238080212340a0a0d00001cc2150000f6c20a0a0d000060c1150000f6c20a0a0d000060c115000014c30a0a0d00001cc215000014c31003180328003000
```

- The app sends each handling of a zone as its own "set" with the same id; the last one
  stands.
- **Delete** = the add with `1: 2` in place of `1: 1`, the corners, type and id repeated. One
  byte differs.
- **Zone ids are reused** (seen once): a throwaway zone got id 3; after its deletion the next
  new zone got id 3 as well. The app takes the highest existing id plus one. Furniture
  behaved differently the same evening (above).
- A new zone starts at 25 × 25 cells.
- A zone may be turned; the robot stores the four corners cut to whole cells.

**An edit made while a job runs is stored, and the running job keeps its map** (seen once,
2026-11-17). During a cruise job the owner redrew zone 2:

```
16:00:44  08011079189916223a2238080112340a0a0d0000e04015000088c20a0a0d0000304215000088c20a0a0d00003042150000dec20a0a0d0000e040150000dec21003180228003000
          {1: 1, 2: 121, 3: 2841, 4: {4: {1: 1, 2: {corners (7, −68) (44, −68) (44, −111) (7, −111), type 3, id 2}}}, 5: 0, 6: 0}
16:00:45  answer {1: 1, 2: <map with the new corners>, 3: 2842}
```

- `map/get_editable_map` had the new corners and 2842 from 16:00:46 on.
- `map/get_map`, read four times until 16:04:06 during and just after that job, still had the
  old corners (4, −62)…(45, −118) and 2.33 = 2841.
- At 16:09:58, the start of the next job, `map/get_map` had the new corners and 2842.
- The app had told the owner the change would apply the next time.

### Room character: operation field 3, record field 7

The owner changed two rooms in one save (20:26:12): Master bedroom from "Heavily Soiled Room"
to "No character", Living Room the other way.

```
0801107818db15220c1a0a0a080802100138005000220e1a0c0a0a0801100320023801500028003000
        bedroom {1: 2, 2: 1, 7: 0, 10: 0}        living room {1: 1, 2: 3, 4: 2, 7: 1, 10: 0}
```

In the answer's map the bedroom's record had lost field 7 and the living room's had gained
`7: 1`. P. This tool sends field 10 = 0, which no other tool sends; not read.

**Sent alongside:** one second after the answer the app sent

```
config/set  ea01160a001204080110022204080110042a00320408011001
            {29: {1: "", 2: {1: 1, 2: 2}, 4: {1: 1, 2: 4}, 5: "", 6: {1: 1, 2: 1}}}        answer 0801
```

It came again, byte for byte, one second after the second character save (20:56:44, when the
characters were put back), and after none of the other 65 operations of that evening. Block 29
is described in [SETTINGS.md](SETTINGS.md); the values were unchanged by it.

### Edit Layout: operation field 9

`4.9 = {1: [ {1: room id, 2: [corner {1: x, 2: y}, whole cells], 3: bytes, one per corner
(0, 1 or 2; not read)} ]}`: **every room's outline, not only the changed one**. Top-level
field 6 is 1 in this edit. P for the layout; captured once from the app (20:10:08, 1,429
bytes, the owner made one room larger by the app's step of "0.1 m").

```
room 1: 16 corners (−66, −197) (−66, −53) (−3, −53) (−3, −21) (4, −21) (5, −20) (5, −20) (19, −20) (20, −21) (20, −21)
                   (21, −21) (21, −21) (48, −21) (48, −137) (−5, −137) (−5, −197)        3: 01010100020202020000000101010101
```

- The step of "0.1 m" is one cell: that wall stood at y = −196 after a first such edit and at
  −197 in this one. L (the first edit was made before the recorder ran).
- The app offered to make a room larger; the owner found no way in it to make one smaller.
- The outlines are simplified polygons (7 to 19 corners per room here), some corners
  repeated.

### Sent over the local socket, and accepted

(2026-11-16 20:15:26; one edit, with the owner watching.) Over port 9002, with no account:
the app's own layout message of 20:10:08 with three bytes changed. The edit version went from
2773 to 2775, as read from the robot a second before (byte 5: `d5` → `d7`), and room 1's two
dining-end corners went from y = −197 back to −195 (bytes 32 and 302: `bb` → `bd`).

- Answer: `{1: 1, 2: <the whole map>, 3: 2776}`.
- Compared cell by cell with the robot's editable map from just before: 184 cells changed,
  all in the strip x −66…−5, y −197…−195. The old wall line became empty, one row of
  room became empty, one row of room became wall again. Room 1 had its 14,474 cells of that
  afternoon.
- So, on this unit: **`map/operation` works over the local socket with no account**; a room
  can be made smaller this way, although the app only offers larger; and a message is
  accepted when its edit version equals the robot's current one. P
- Against the afternoon's map, apart from flag bits, 13 cells still differed, none near that
  strip: 12 that carried the high bit of section 2, and one cell by a door that was wall and
  became room. Probably from the app's own first layout edit, which rewrites every room; not
  looked into.
- This is the only map edit ever sent by us. No other operation kind was sent locally.

---

## 7. Live position and planned route

(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)

Only what concerns coordinates; the rest is in [PROTOCOL.md](PROTOCOL.md) §7.

**`map/display_map`.** All positions are in cells (section 3).

| Field | On this unit | Mark |
|---|---|---|
| 1.1 `{1: x, 2: y}` | The robot, float32, **cells**. A coordinate of exactly 0.0 is absent | P |
| 1.2 | Heading, radians | L |
| 2 `{1: packed float32 x, 2: packed float32 y}` | The recent trail, cells | L |
| 5.1 | The dock, the same value as the map's 2.8: (−8.33, 0) | L |
| 7 | `{1: 732, 2: 738, 3: zlib, 7: zlib}` while docked; both streams were empty (`7801030000000001`). During a job also 7.5, 7.6, 7.8, 7.9 (detected objects and soiled spots, positions in cells) | L |
| 10 | Time, ms | P |

PROTOCOL.md labels 1.1 "decimetres"; see section 3 for why that does not hold here.

**`status/point_navi_plan_traj`.** `{1: [{1: x, 2: y}, …]}`, float32, in cells: the points of
the route the robot is about to drive, shrinking as it advances. L. PROTOCOL.md §9 lists the
topic under "Silent on CX7" (requested and never answered). As a broadcast, with the app open
and sending its keep-alive, it was seen 409 times on 2026-11-17:

| When | Messages | What the robot was doing |
|---|---|---|
| 15:10:35 to 15:13:59 | 117 | a room job (short bursts) |
| 15:41:23 to 15:41:45 | 25 | a return to the dock |
| 15:59:22 to 16:03:53 | 222 | a cruise job, once a second, 120 to 180 points each |
| 16:10:14 to 16:11:26 | 45 | a drawn-zone job |

An empty list (`0a00`) is sent between routes. The first route of the day began
`(0.0, 1.0) (0.5, 0.5) (1.0, 0.0) (2.0, 0.0) (3.0, 0.0) …`: steps of one cell away from the
dock.

---

## 8. The map-update viewer: `map/check_map_update_info`

(CX7, `hEA7OEshlx`, v01.13.11.02; seen once, 2026-11-17 15:02:15)

In the app: "Settings" › "Experimental Functions" › "Furniture/Floor Material Updates". The
page says such functions "are rolled out to users in batches and may vary between users". On
this account it showed the map and a greyed-out button "No updates".

- Opening it sent one broker request, `map/check_map_update_info`, with an empty body. L
- The answer was `{2: <a map>}`, 15,923 bytes, with the same fields as `map/get_map` (extent,
  two no-go zones, six doors, seven rooms, eight carpets, the grid) and no result field. It
  had the same edit version, zones and carpet ids as the map read a minute later; the grids
  were not compared.
- No web call.
- The app's strings also contain the topic names `map/save_map_update_info`,
  `map/start_update_map` and `map/set_update_regions`; none appeared in the traffic.
- Switching the app's map view to "3D space" and changing its look sent nothing over the
  broker (2026-11-17); it fetches its objects over the web, see [CLOUD-API.md](CLOUD-API.md).

Also seen once and not read: `map/enable_temp_map` with `{1: 1, 2: {1: 1, 2: <the map's
2.34>}}`, answered `{1: 2}`, at the moment the owner opened a cleaning report (16:13:37).

---

## 9. Evidence

Raw bodies, cloud envelope removed. The map holds no id; nothing needed zeroing in these
messages. Sources: the broker recordings of 2026-11-16 (20:09 to 22:01) and 2026-11-17
(14:38 to 16:13).

### The map message, small fields (`map/get_map/response`, 2026-11-17 14:38:03, 16,500 bytes)

```
head   080112ec8001 0801 1078 183c 209b01 28d802 32…      {1: 1, 2: {1: 1, 2: 120, 3: 60, 4: 155, 5: 344, 6: …
2.6    08a0feffffffffffffff01107718a6ffffffffffffffff012040                       {1: −224, 2: 119, 3: −90, 4: 64}
2.7    0a0a0d13f0f5c015c7c911c11544adb0bb                                         {1: {1: −7.6856, 2: −9.1118}, 2: −0.00539}
2.8    0a050d545505c1                                                             {1: {1: −8.3333}}        (y = 0 and heading absent)
2.9    0a0a0d000080c0150000a8c10a0a0d0000803f150000a8c10a0a0d0000803f1500001cc20a0a0d000080c01500001cc210031801
       0a0a0d0000804015000078c20a0a0d0000344215000078c20a0a0d00003442150000ecc20a0a0d00008040150000ecc210031802
2.11   0a020102120d08e7ffffffffffffffff011018120d08dcffffffffffffffff011018       rooms 1, 2: (−25, 24) to (−36, 24)
       0a020104120408111007120408071007                                           rooms 1, 4: (17, 7) to (7, 7)
       0a020203120d08d6ffffffffffffffff011024120d08cdffffffffffffffff011024       rooms 2, 3: (−42, 36) to (−51, 36)
       0a020406120d081310ebffffffffffffffff01120d080510ebffffffffffffffff01       rooms 4, 6: (19, −21) to (5, −21)
       0a020405120d080110fcffffffffffffffff01120408011004                         rooms 4, 5: (1, −4) to (1, 4)
       0a020607121608fcffffffffffffffff0110c5ffffffffffffffff01121608fcffffffffffffffff0110fafeffffffffffffff01
                                                                                  rooms 6, 7: (−4, −59) to (−4, −134), the split's line
2.12   080110013801 · 080210052002 · 08031009 · 0804100a2002 · 0805100620023001 · 080610032002 · 0807100420023001
2.13   0a9802 3185cac0 545505c1 267413c1 …        566 bytes: {1: 70 float32 x, 2: 70 float32 y}
2.18   3      2.20  63      2.33  2841      2.34  1774999637
2.21   08f7ffffffffffffffff0110ccffffffffffffffff011873209e02                     {1: −9, 2: −52, 3: 115, 4: 286}
2.26   0805 120d080410a3ffffffffffffffff01 120d080410a4ffffffffffffffff01 … 1a0d080710a7ffffffffffffffff01 2002
       349 bytes: {1: 5, 2: [(4, −93), (4, −92), … 22 points], 3: (7, −89), 4: 2}        (the floor vent's square)
2.27   0a0d080a10beffffffffffffffff010a0d080810fbfeffffffffffffff010a0d082d10fafeffffffffffffff010a0d082f10bcffffffffffffffff0110011a0c0a0a0d00004042150000c4c2
2.32   0a210801100e1a160a0a0d0000ac41150000264215000030411d0000984125000034430a210802100e1a160a0a0d00004841150000c3c215000050411d000004422500003443
       0a21080310021a160a0a0d000030c11500008a4215000018421d00000042250000b4420a1c0805104c1a160a0a0d4c5cae41151e8d9c42150000a0411d0000a041
       0a1c080610121a160a0a0d16f1a8c1150653d2c215555505411d55550541              (one field, shown on three lines)
```

### The grid (2.17)

```
first bytes   7801ed5cd16ee338129c1b04c16010e41bfce8cfdc6010ccdb2146b058f8613f …
length        4,652 bytes compressed (zlib, header 78 01)
unpacked      76,957 bytes: 0a 99d904 <76,953 bytes of varints>  →  53,320 values
```

Unpack with the function in section 2. Values and how often each occurs (2026-11-17
14:38:03):

```
0: 28604   32: 980   40: 139
room 1   257: 64    261: 2030  263: 18   272: 2035  273: 823  275: 185  281: 306
room 2   513: 735   517: 177   528: 103  529: 76    531: 41   537: 78
room 3   769: 8     773: 768   775: 82   784: 202   785: 155  787: 81   793: 135
room 4   1025: 436  1041: 23   1049: 52
room 5   1281: 416  1283: 45   1297: 33  1305: 75
room 6   1537: 2067 1541: 1841 1543: 56  1552: 596  1553: 549 1555: 218 1557: 93  1559: 8  1561: 310  1565: 135
room 7   1793: 5976 1795: 193  1797: 25  1808: 263  1809: 743 1811: 976 1817: 354
high bit 268437249 (0x10000701): 1     268437273 (0x10000719): 11
```

The same grid from `map/get_editable_map` (2026-11-17 15:52:42) for comparison:

```
0: 28604   32: 980   40: 139
257: 64  261: 2048  272: 3043  280: 306  ·  513: 735  517: 177  528: 220  536: 78  ·  769: 8  773: 850  784: 438  792: 135
1025: 436  1040: 23  1048: 52  ·  1281: 461  1296: 33  1304: 75
1537: 2067  1541: 1897  1552: 1363  1556: 101  1560: 310  1564: 135  ·  1793: 6170  1797: 25  1808: 1982  1816: 365
```

### Requests

```
map/get_map                  08001000
map/get_editable_map         080110001800
map/get_all_reduced_maps     (empty)
map/check_map_update_info    (empty)
map/enable_temp_map          08011208080110d5b0b1ce06        answer 0802
```

### `map/operation`, one or more of each kind (2026-11-16 unless dated)

Every body starts `0801 1078 18<edit version> 22<length> <operation>` and ends `2800 3000`
(`2800 3001` for the layout edit).

**Split (4.1) with the two records (4.3)**

```
21:08:55  08011078188c16221e0a1c0a0a0d000080c01500006cc2120a0d000080c015000006c318012007220a1a080a06080710032002220a1a080a0608011003200228003000
21:19:23  08011078188f16221e0a1c0a0a0d000058c215000008c3120a0d000040c115000008c318062007220c1a0a0a080807100420023001220c1a0a0a08080610042002300128003000
21:20:40  08011078189016221e0a1c0a0a0d000080c01500006cc2120a0d000080c015000006c318062008220e1a0c0a0a08081004200230014001220e1a0c0a0a0806100420023001400128003000
21:22:39  08011078189216221e0a1c0a0a0d0000c0c015000006c3120a0d0000c0c01500006cc218062008220e1a0c0a0a08081004200230014002220e1a0c0a0a0806100420023001400228003000
21:24:07  08011078189416221e0a1c0a0a0d000080c015000006c3120a0d000080c01500006cc218072008220e1a0c0a0a08081004200230014002220e1a0c0a0a0807100420023001400228003000
21:26:14  08011078189716221e0a1c0a0a0d000080c01500006cc2120a0d000080c015000006c318062007220c1a0a0a080807100420023001220c1a0a0a08080610042002300128003000
```

**Merge (4.2) with the result's record (4.3)**

```
21:15:28  08011078188e162208120608071001180722101a0e0a0c08071004200228003000380028003000
21:21:42  080110781891162208120608081006180622101a0e0a0c08061004200228003000380028003000
21:23:21  080110781893162208120608061008180822101a0e0a0c08081004200228003000380028003000
21:24:56  080110781895162208120608081007180822101a0e0a0c08081004200228003000380028003000
21:25:30  080110781896162208120608061007180722101a0e0a0c08071004200228003000380028003000
```

**Room record (4.3): naming**

```
20:59:24  0801107818f515220c1a0a0a080801100f1a00200228003000                               type 15 "Others"
20:59:40  0801107818f615221a1a180a16080110001a0e5361726168e280997320726f6f6d200228003000   type 0, a typed name
21:02:01  0801107818f715220c1a0a0a08080110011a00200228003000                               type 1; the next thirteen saves carry 2 to 14
21:11:57  08011078188d16220e1a0c0a0a080710041a002002400228003000                           room 7 → Kitchen; the app sends 8: 2 back
21:26:32  0801107818981622101a0e0a0c080610031a0020023001400128003000                       room 6 → Living Room; the app sends 6: 1, 8: 1 back
```

**Room record (4.3): floor material and grain**

```
20:29:58  0801107818dc15220e1a0c0a0a08011003200528003801220c1a0a0a080803100520032800220e1a0c0a0a0806100620022800300128003000   marble, cobblestone, tile
20:31:04  0801107818dd15220c1a0a0a08080410092004280028003000                                                                   tatami
20:33:11  0801107818de15220e1a0c0a0a08011003200128003801220c1a0a0a08080410092000280028003000                                   wood; "No material" (4: 0)
20:34:01  0801107818df15220e1a0c0a0a080110032001285a380128003000                                                               grain 90
20:35:05  0801107818e115220f1a0d0a0b08011003200128b401380128003000                                                             grain 180
20:36:59  0801107818e315220e1a0c0a0a0801100320022800380128003000                                                               back to tile
```

**Room record (4.3): character**

```
20:26:12  0801107818db15220c1a0a0a080802100138005000220e1a0c0a0a0801100320023801500028003000     bedroom 7: 0, living room 7: 1
20:56:44  0801107818f415220c1a0a0a080802100138015000220e1a0c0a0a0801100320023800500028003000     put back
```

**No-go zone (4.4)**

```
20:38:06  0801107818e415223a2238080112340a0a0d0000b0c115000020c20a0a0d0000304115000020c20a0a0d0000304115000094c20a0a0d0000b0c115000094c210031802223a2238080112340a0a0d0000804015000078c20a0a0d0000384215000078c20a0a0d00003842150000eec20a0a0d00008040150000eec21003180228003000
20:38:58  0801107818e515223a2238080112340a0a0d0000804015000078c20a0a0d0000384215000078c20a0a0d00003842150000eec20a0a0d00008040150000eec21002180228003000
20:39:20  0801107818e615223a2238080112340a0a0d0000804015000078c20a0a0d0000384215000078c20a0a0d00003842150000eec20a0a0d00008040150000eec21001180228003000
20:40:46  0801107818e815223a2238080112340a0a0dfa04a74015549674c20a0a0d04ba384215679e7bc20a0a0d611f2f4215d6b4edc20a0a0dc35f344015cc30eac210031802223a2238080112340a0a0d0000804015000078c20a0a0d0000344215000078c20a0a0d00003442150000ecc20a0a0d00008040150000ecc21003180228003000
20:43:21  0801107818e915223a2238080112340a0a0d00001cc2150000f6c20a0a0d000060c1150000f6c20a0a0d000060c115000014c30a0a0d00001cc215000014c31003180328003000     add id 3
20:43:32  0801107818ea15223a2238080212340a0a0d00001cc2150000f6c20a0a0d000060c1150000f6c20a0a0d000060c115000014c30a0a0d00001cc215000014c31003180328003000     delete id 3
20:43:47  0801107818eb15223a2238080112340a0a0d000000c2150000eec20a0a0d0000e0c0150000eec20a0a0d0000e0c015000010c30a0a0d000000c215000010c31003180328003000     add: id 3 again
20:43:58  0801107818ec15223a2238080212340a0a0d000000c2150000eec20a0a0d0000e0c0150000eec20a0a0d0000e0c015000010c30a0a0d000000c215000010c31003180328003000     delete
2026-11-17 16:00:44 (during a job)
          08011079189916223a2238080112340a0a0d0000e04015000088c20a0a0d0000304215000088c20a0a0d00003042150000dec20a0a0d0000e040150000dec21003180228003000
```

**Carpet (4.6)**, 2,607 bytes; head and tail

```
20:52:20  0801107818ed1522a114329e1408041004180022040807100922040808100a22040808100b220408 … 3800400028003000
```

**Furniture (4.8)**

```
20:10:41  0801107818d6152229422708011223080410041a160a0a0d152d00c215543426c3159c0181411d17cee0412500000000280028003000      add id 4, type 4
20:18:14  0801107818d8152229422708011223080410041a160a0a0d812914c215219f0dc3159c0181411d17cee0412500000000280028003000      move
20:18:28  0801107818d9152227422508021221080410041a160a0a0d7fd6534215904f8243159c0181411d17cee041250000000028003000          delete
20:23:28  0801107818da1522294227080112230805104c1a160a0a0d4c5cae41151e8d9c42150000a0411d0000a041250000000028002229422708011223080610121a160a0a0d16f1a8c1150653d2c215555505411d555505412500000000280028003000      add ids 5 (type 76) and 6 (type 18)
```

**Layout (4.9)**, 1,429 bytes; head and tail

```
20:10:08  0801107818d51522870b4a840b0aba020801121608beffffffffffffffff0110bbfeffffffffffff … 020202000000000128003001
```

The edit sent locally at 20:15:26 is this message with byte 5 `d5` → `d7` and bytes 32 and
302 `bb` → `bd`.

**An answer** (every operation): `0801 12<length> <map> 18<new edit version>`, for example
`{1: 1, 2: <12,687 bytes>, 3: 2842}` at 2026-11-17 16:00:45.

### Route (`status/point_navi_plan_traj`, 2026-11-17 15:10:35, 396 bytes; first five points)

```
0a0a0dd257c834154000803f 0a0a0d5300003f1560feff3e 0a0a0d0d00803f15a5a52db5 0a0a0dfaffff3f157e9c18b5 0a0a0df2ff3f4015559303b5 …
(0.0, 1.0) (0.5, 0.5) (1.0, −0.0) (2.0, −0.0) (3.0, −0.0)
```
