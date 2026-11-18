# Robot settings: `config/get` and `config/set` on a CX7

Every setting the official app offers for one Freo Z Ultra, with the message the app sent
when it was changed, the field it moved in `config/get`, and Narwal's own name for it where
one could be found.

> **Scope: one unit.** Everything below was observed on ONE robot: Freo Z Ultra (CX7),
> product key `hEA7OEshlx`, firmware `v01.13.11.02`, one account in the US region, iOS app
> 2.10.90, between 2026-11-13 and 2026-11-17. Three vantage points were recorded at once: a
> read-only listener on Narwal's cloud MQTT broker (the app's commands and the robot's
> answers), the robot's local WebSocket on port 9002, and the phone's web traffic through an
> intercepting proxy. Nothing here was tested on any other model or firmware. It is evidence,
> not a specification. (CX7 v01.13.11.02; @pdb0102, 2026-11)

How sure each line is:

| Mark | Meaning |
|---|---|
| **P** | Confirmed by an app action: one thing was changed in the app and this message was captured, or the same number was seen on both sides of a comparison |
| **L** | Likely: matched by value, name or position only, not by a controlled change |
| **G** | A guess |

All hex is the command's own protobuf, with the cloud envelope cut off: the bytes the local
WebSocket would carry as payload (see [PROTOCOL.md](PROTOCOL.md) §2 for the frame).

Related documents: [PROTOCOL.md](PROTOCOL.md) (transport, commands, status),
[CLOUD-API.md](CLOUD-API.md) (the app's web calls), [MAP-FORMAT.md](MAP-FORMAT.md) (the map
and map editing).

---

## 1. How settings travel on this unit

| Step | Topic | Body | Answer |
|---|---|---|---|
| Read everything | `config/get` | empty | `{1: 1, 2: <settings block>}`, 182 to 202 bytes on this unit (182 on 2026-11-13, 182 to 202 on 2026-11-16, 191 to 201 on 2026-11-17; it grows with what is set) |
| Change one setting | `config/set` | one field, or one composite block | `{1: 1}` (`08 01`) |
| Read back | `config/get` | empty | the block, with the change in it |

What was seen, every time (96 `config/set` messages from the app on three capture days):

- **One field or one block per `config/set`.** The app never sent two settings in one
  message. Where a single choice in the app covers two fields ("Auto-empty Frequency" →
  "Smart"), it sent two messages in the same second.
- **A composite block is sent whole.** Changing one option on the "Freo Mind Mode" page
  sends all of field 29; changing the rewash area sends all of field 18.
- **Settings are saved at the tap** (or at "Confirm" where a sheet has one), not on leaving
  the page.
- **The robot answered `{1: 1}` to every one**, and the app then sent `config/get`, usually
  within a second. The read-back showed the change every time.
- **`config/get` answers over the local socket too** ([PROTOCOL.md](PROTOCOL.md) §9 "Answered locally", same unit; read again 2026-11-17).
  **`config/set` over the local socket was not tried by us.** Every `config/set` below was
  sent by the app over the cloud broker.

**The field numbers of `config/set` are not the field numbers inside `config/get`'s block.**
Volume is 1 in both. "Do Not Disturb" is field 5 in `config/set` and field 2.4 in
`config/get`. From field 17 upward the two numberings agree for every field met; below that
they mostly differ by one, and not always. The two tables below are kept apart for that
reason: §2 is `config/set`, §3 is `config/get`.

**Zero is written by leaving the field out.** In `config/get` a switch that is off is simply
absent (proto3 default). The app's `config/set` does send explicit zeros (`58 00`).

---

## 2. `config/set`: every field met

Screen names are the pages under the app's "Settings". Dates are 2026-11-13 (`11-13`),
2026-11-16 (`11-16`) and 2026-11-17 (`11-17`). All **P** unless marked.

### 2.1 Single-value fields

| Field | Screen › label | Values | Example bytes | Captured |
|---|---|---|---|---|
| 1 | (volume slider, "Language & Voice") | percent; values seen 58 to 100 (the slider's range is presumably 0 to 100; not seen) | `08 59` = 89 | 11-13, 14 changes |
| 6 | General › "Plateau Mode" | 0 off, 1 on | `30 01` | 11-16 |
| 7 | Base Station Settings › "Automatically Add Detergent" | 0 off, 1 on | `38 00` | 11-16 |
| 8 | General › "Child Lock" | 0 off, 1 on | `40 01` | 11-16 |
| 11 | General › "Stairless mode" | 0 off, 1 on | `58 00` | 11-16 |
| 13 | Base Station Settings › "Mop Drying Intensity" | 1 "Quiet", 2 "Strong", 3 "Smart" | `68 01` | 11-16 |
| 17 | Carpet Detection and Cleaning › "Cleaning mode for newly detected carpets" | 1 "Cross", 2 "Clean", 3 "Vacuum & Mop", 4 "Avoid" | `88 01 04` | 11-16 |
| 21 | Base Station Settings › "Default Cleaning Mode for Dock" | 2 Vacuum, 3 Mop, 4 Vacuum and mop, 5 Vacuum then mop | `a8 01 05` | 11-16 |
| 22 | "Pet-friendly Mode" (its own page) | 0 off, 1 on | `b0 01 01` | 11-16 |
| 27 | Base Station Settings › "Auto-empty Frequency" (on/off part) | 0 "Close", 1 on | `d8 01 00` | 11-16 |
| 28 | Base Station Settings › "Auto-empty Frequency" (kind) | 0 "Frequent", 1 "Smart" | `e0 01 00` | 11-16 |
| 30 | Base Station Settings › "Auto-Empty Level" | 0 "Strong", 1 "Quiet" | `f0 01 01` | 11-16 |
| 31 | Base Station Settings › "Dust Bin / Dust Bag with Auto Disinfection" | 0 off, 1 on | `f8 01 00` | 11-16 |
| 32 | Base Station Settings › "Smart Mop Wash with Hot Water" | 0 off, 1 on | `80 02 00` | 11-16 |
| 33 | Freo Mind Mode › "Intensive Cleaning for Large Soiled Areas" | 0 off, 1 on | `88 02 00` | 11-16 |
| 34 | AI Recognition › "Obstacle Avoidance Strategy" | 1 "Smart", 2 "Safety" | `90 02 02` | 11-17 |
| 37 | General › "Auto Power-Off" | 0 off, 1 on | `a8 02 00` | 11-16 |

Field numbers in none of this section's tables: 2, 3, 4, 9, 12, 14, 15, 16, 19, 20, 23 to 26,
35, 36; no app action sent them.

Notes on single rows:

- **17** uses the same four numbers as a carpet's own mode in the map (see
  [MAP-FORMAT.md](MAP-FORMAT.md)): two independent runs, same result.
- **21** uses the mode numbers of `CleanParam` tag 1 in `clean/start_clean`
  ([PROTOCOL.md](PROTOCOL.md) §6): a second, independent confirmation of those numbers on
  this unit. The app's text: "Start cleaning task by pressing the Start/Stop button on the
  dock. It will default to performing whole-house cleaning in the selected mode".
- **27 and 28 are one row in the app.** "Frequent" sent `{28: 0}`; "Close" sent `{27: 0}`;
  "Smart" sent `{27: 1}` and `{28: 1}` as two messages in the same second (21:57:22).
- **11** asks for confirmation in the app when switched on: "The robot will be unable to
  recognize large height difference when this function is enabled, and may fall off if your
  house has stairs."
- **34** is the only row on the "AI Recognition" page on this unit: no object-detection
  switches, no photo options.

### 2.2 Field 5: "Do Not Disturb Mode" (General)

`{5: {1: on, 2: from, 3: to}}`, times in seconds of the day. P, 11-16 21:53.

```
2a 0a 08 00 10 e0 ea 04 18 80 e1 01     {5: {1: 0, 2: 79200, 3: 28800}}   off, 22:00 to 08:00
2a 0a 08 01 10 e0 ea 04 18 80 e1 01     {5: {1: 1, 2: 79200, 3: 28800}}   on
2a 0a 08 01 10 9c eb 04 18 80 e1 01     {5: {1: 1, 2: 79260, 3: 28800}}   from 22:01
2a 0a 08 01 10 9c eb 04 18 f8 e1 01     {5: {1: 1, 2: 79260, 3: 28920}}   to 08:02
```

The whole block goes each time. This confirms the reading of `config/get` 2.4 already in
[PROTOCOL.md](PROTOCOL.md) §9 as a do-not-disturb window in seconds. The app's text: "When
enabled, some robot voice prompts and dock lights will be turned off during Do Not Disturb
hours."

### 2.3 Field 10: "Intensive Corner Cleaning" (Freo Mind Mode)

`{10: {1: state, 2: interval in days}}`. P, 11-16 21:34. The choice opens a sheet with
"Confirm"; each Confirm sent one message.

```
52 04 08 03 10 07     {10: {1: 3, 2: 7}}     "Smart Mode" (runs once every 7 days or longer)
52 04 08 01 10 00     {10: {1: 1, 2: 0}}     "Close"
52 04 08 03 10 00     {10: {1: 3, 2: 0}}     "Every Time"
```

10.1: 1 = off, 3 = on. 10.2: 7 for "Smart Mode", 0 for "Every Time". Value 2 of 10.1 was not
seen. This setting sits on the Freo Mind page but is not part of block 29.

### 2.4 Field 18: "Floor Cleaning" (rewash strategy and house cleaning order)

`{18: {1: kind, 2: area step, 4: {1: order set, 2: order, 3: second list, 4: 1}}}`. P for
18.1, 18.2 and 18.4.2; 11-16 21:44 to 21:50.

| Sub-field | Meaning | Values |
|---|---|---|
| 18.1 | rewash kind | 1 = "Rewash by Area", 2 = "Wash mops by room" |
| 18.2 | area step | 1 = every 129 ft² (12 m²), 2 = every 108 ft² (10 m², the app's default), 3 = every 86 ft² (8 m²) |
| 18.4.1 | a "House Cleaning Order" is set | 1 yes, 0 no |
| 18.4.2 | the order | packed room ids, one byte each, in the chosen order; absent when none is set |
| 18.4.3 | a second list of all rooms | did not change across three saves; L: the order the robot takes by itself |
| 18.4.4 | unknown | 1 every time; G: the map id (see §4) |

```
92 01 04 08 01 10 02                                {18: {1: 1, 2: 2}}     every 108 ft²
92 01 04 08 01 10 01                                {18: {1: 1, 2: 1}}     every 129 ft²
92 01 04 08 01 10 03                                {18: {1: 1, 2: 3}}     every 86 ft²
92 01 04 08 02 10 03                                {18: {1: 2, 2: 3}}     "Wash mops by room"
92 01 1c 08 01 10 03 22 16 08 01 12 07 03 01 02 05 04 06 07 1a 07 05 04 06 07 01 02 03 20 01
                                                    order set: rooms 3, 1, 2, 5, 4, 6, 7
92 01 13 08 01 10 03 22 0d 08 00 1a 07 05 04 06 07 01 02 03 20 01
                                                    order cleared
```

- **The four rewash choices are one radio group.** "Wash mops by room" cannot be switched
  off by tapping it again (the same message goes out); only choosing an area leaves it. The
  area step is kept while "by room" is chosen.
- The rewash-only messages leave 18.4 out, and the robot kept its stored 18.4 (read back in
  `config/get`). The order messages carry the whole block.
- The app says the rewash strategy "applies only in Custom mode", and that in Freo Mind the
  robot returns to wash after each room by default.
- **Room ids are per map and not stable.** They changed on this robot on 2026-11-16 when
  rooms were merged and split, and 18.4.3 in `config/get` followed each edit (11 changes between 21:08:56 and 21:26:16, eight distinct lists
  counting the one it started from, with no `config/set` in between). Read ids from a fresh `map/get_map`
  before building an order.
- 18.4.2 orders a whole-house start, by the app's own words ("When the robot starts cleaning
  the entire house, it will clean in the room sequence you set"). Not tested by a run. A
  two-room start on 2026-11-17 that named its own order was not overridden by 18.4.3
  (seen once).

### 2.5 Field 29: the "Freo Mind Mode" block

`{29: {1: …, 2: …, 4: …, 5: …, 6: …, 7: …}}`, sent whole on every change. P for 29.1, 29.2,
29.4, 29.5 and 29.7; 11-16 21:32 to 21:41, 29.2 repeated 11-17 15:48.

Sub-fields 1, 2, 4, 5 and 6 share one shape: `{1: chosen by hand, 2: value}`. `{1: 0, 2: 0}`,
or an empty entry, means the app's "Smart" / "AI" choice.

| Sub-field | App label | Values (field 2 of the entry) |
|---|---|---|
| 29.1 | "Re-mopping Cycle Limit" | 1, 2, 3; "AI" = `{1: 0, 2: 0}` |
| 29.2 | "Coverage Precision" | 1 "Standard", 2 "Intensive"; "Smart" = `{1: 0, 2: 0}` |
| 29.3 | not seen | |
| 29.4 | "Suction" | 1 "Quiet", 2 "Standard", 3 "Strong", 4 "Super powerful"; "Smart" = `{1: 0, 2: 0}` |
| 29.5 | "Mopping Humidity" | 1 "Slightly dry", 2 "Standard", 3 "High"; "Smart" = `{1: 0, 2: 0}` |
| 29.6 | unknown | `{1: 1, 2: 1}` throughout; nothing on the page moved it (§4 has a guess) |
| 29.7 | "Use Heavy-duty Floor Stain Remover" | `{1: on, 2: 1 every time / 2 at an interval, 3: interval in minutes}` |

```
ea 01 1a 0a 04 08 01 10 01 12 04 08 01 10 02 22 04 08 01 10 04 2a 00 32 04 08 01 10 01     29.1 = {1: 1, 2: 1}   limit 1
ea 01 1a 0a 04 08 01 10 02 12 04 08 01 10 02 22 04 08 01 10 04 2a 00 32 04 08 01 10 01     29.1 = {1: 1, 2: 2}   limit 2
ea 01 1a 0a 04 08 01 10 03 12 04 08 01 10 02 22 04 08 01 10 04 2a 00 32 04 08 01 10 01     29.1 = {1: 1, 2: 3}   limit 3
ea 01 1a 0a 04 08 00 10 00 12 04 08 01 10 02 22 04 08 01 10 04 2a 00 32 04 08 01 10 01     29.1 = {1: 0, 2: 0}   "AI"
```

29.7, the tail of the block only (the cartridge is "Not installed" on this dock; the app
allowed the choice all the same):

```
… 3a 06 08 01 10 01 18 00              29.7 = {1: 1, 2: 1, 3: 0}         "Every time"
… 3a 07 08 01 10 02 18 e0 4e           29.7 = {1: 1, 2: 2, 3: 10080}     "Every 7 days"
… 3a 08 08 01 10 02 18 c0 9d 01        29.7 = {1: 1, 2: 2, 3: 20160}     "Every 14 days"
… 3a 08 08 00 10 02 18 c0 9d 01        29.7 = {1: 0, 2: 2, 3: 20160}     "Do Not Use"
```

- 29.7 is absent from the block until it has been set once. "Do Not Use" clears only the
  first field and keeps the last interval.
- The numbers in 29.2, 29.4 and 29.5 are those of `CleanParam` tags 8, 2 and 4 in
  `clean/start_clean`. The app labels the same four suction levels "Noise Reduction,
  Standard, Turbo, Max" in the cleaning sheet and "Quiet, Standard, Strong, Super powerful"
  here.
- **The map editor's "Room character" tool re-sends this block unchanged after every save**
  (11-16 20:26 and 20:56). Why is not known. See [MAP-FORMAT.md](MAP-FORMAT.md).
- "Intensive Corner Cleaning" (field 10) and "Intensive Cleaning for Large Soiled Areas"
  (field 33) are shown on the same page and are fields of their own.

### 2.6 Settings on other topics

| Screen › label | Topic | Body | |
|---|---|---|---|
| Language & Voice › a voice | `config/language/set_custom_voice` | `{1: language, 2: pack id, 3: version}`, e.g. `0a 02 65 6e 12 08 43 58 58 5f 30 30 30 31 1a 0b 30 33 2e 30 31 2e 30 32 2e 30 30` = `en`, `CXX_0001`, `03.01.02.00` | P, 11-13. Answer 1; answered 3 once, on switching back to a pack used shortly before (meaning unknown, seen once) |
| (read back) | `config/language/get_current_voice_info` | empty | `{1: 1, 2: {1: language, 2: version, 4: pack id}}` P |
| Device › "Locate Robot" | `common/yell` | empty | P, 11-17, three presses, each answered `{1: 1}` |
| Device › "Restart Robot" | `common/reboot` | empty | P, 11-17 14:49:34, seen once. Answered `{1: 1}`; the robot was off the broker for about a minute (last status 14:49:39, first after 14:50:38) |
| Accessory Management › "Replaced (timer reset)" | `consumable/reset_consumable_info` | `0a 03 12 01 18` = `{1: {2: [24]}}` | P, 11-16, seen once: item 24, the "Replaceable insert bin". Field 2 is the replace-item list of [PROTOCOL.md](PROTOCOL.md) §7. The hours left come from the web: [CLOUD-API.md](CLOUD-API.md) |
| Experimental Functions › "Furniture/Floor Material Updates" | `map/check_map_update_info` | empty | L, from opening the page: answered `{2: <a map>}`, 15,923 bytes. An answer holding an update, and the message that accepts one, were not seen |

A two-letter language code reads as a nested message in a schema-free decoder (`pl` parses
as `{14: 108}`). Treat field 1 as text.

---

## 3. `config/get`: the block as read

`config/get` with an empty body answers `{1: 1, 2: {…}}`. The block on 2026-11-17 14:38
(191 bytes; the 49-byte location entry is written out below instead of in hex, with the
city replaced):

```
08 01 12 ba 01
  08 64                          2.1  = 100
  10 01                          2.2  = 1
  1a 31 <49 bytes>               2.3  = {1: "America/Denver", 2: "UTC -06:00", 3: "USA", 4: "<city>"}
  22 0a 08 01 10 9c eb 04 18 f8 e1 01     2.4 = {1: 1, 2: 79260, 3: 28920}
  30 01  40 01  50 01  58 01     2.6, 2.8, 2.10, 2.11 = 1
  60 03  68 03                   2.12 = 3, 2.13 = 3
  72 02 08 03                    2.14 = {1: 3}
  78 02  88 01 02                2.15 = 2, 2.17 = 2
  92 01 11 08 01 10 03 22 0b 1a 07 05 04 06 07 01 02 03 20 01     2.18 = {1: 1, 2: 3, 4: {3: [5,4,6,7,1,2,3], 4: 1}}
  98 01 02  a0 01 01  a8 01 05   2.19 = 2, 2.20 = 1, 2.21 = 5
  b8 01 01  c0 01 01  c8 01 01  d0 01 01  d8 01 01  e0 01 01     2.23 to 2.28 = 1
  ea 01 1e 0a 00 12 04 08 01 10 02 22 04 08 01 10 04 2a 00 32 04 08 01 10 01 3a 06 10 02 18 c0 9d 01
                                 2.29 = {1: "", 2: {1: 1, 2: 2}, 4: {1: 1, 2: 4}, 5: "", 6: {1: 1, 2: 1}, 7: {2: 2, 3: 20160}}
  f8 01 01  80 02 01  88 02 01  90 02 01  a0 02 01  a8 02 01     2.31, 2.32, 2.33, 2.34, 2.36, 2.37 = 1
```

**How this table was made:** after each `config/set` the app read `config/get`; the two
answers on either side of the change were compared. "P" below means one `config/set` went
out and the next read differed in this field (and in no other, except where a row says that
two or three fields move together). This answers the "~8
unmapped flags" of [PROTOCOL.md](PROTOCOL.md) §9 for the fields that an app setting moves.

| `config/get` | Moved by `config/set` | Setting | Value read 11-17 | |
|---|---|---|---|---|
| 2.1 | 1 | volume, percent | 100 | P |
| 2.2 | – | unknown; never moved | 1 | |
| 2.3 | – (a web call, §5) | location `{1: time zone, 2: UTC offset, 3: country, 4: city}` | see above | P for "changes after the app's web call"; L for the sub-field meanings (by content) |
| 2.4 | 5 | "Do Not Disturb Mode" `{1: on, 2: from, 3: to}` | on, 79260, 28920 | P |
| 2.5 | 6 | "Plateau Mode" | absent (off) | P |
| 2.6 | 7 | "Automatically Add Detergent" | 1 | P |
| 2.7 | 8 | "Child Lock" | absent (off) | P |
| 2.8 | (17) | absent after `{17: 4}` "Avoid" and `{17: 1}` "Cross"; 1 again after `{17: 3}` and `{17: 2}` | 1 | L: "new carpets get cleaned"; a side effect of field 17, never set by itself |
| 2.9 | – | never present | | |
| 2.10 | 11 | "Stairless mode" | 1 | P |
| 2.11 | – | unknown; never moved | 1 | |
| 2.12 | 13 | "Mop Drying Intensity" | 3 "Smart" | P |
| 2.13 | (18) | follows 18.2, the rewash area step (3 → 2 → 1 → 3 in step with it) | 3 | P for "moves with 18.2"; its own meaning L |
| 2.14 | 10 | "Intensive Corner Cleaning" `{1: state, 2: days}` | `{1: 3}` "Every Time" | P |
| 2.15 | (17) | moves with field 17, same value | 2 | P for "moves with 17"; why there are two is unknown |
| 2.16 | – | never present | | |
| 2.17 | 17 | mode for newly detected carpets | 2 "Clean" | P |
| 2.18 | 18 | "Floor Cleaning" block, same layout as §2.4 | see above | P |
| 2.19 | – | unknown; never moved | 2 | |
| 2.20 | – | unknown; never moved | 1 | |
| 2.21 | 21 | "Default Cleaning Mode for Dock" | 5 | P |
| 2.22 | 22 | "Pet-friendly Mode" | absent (off) | P |
| 2.23 to 2.26 | – | unknown; never moved | 1 each | |
| 2.27 | 27 | auto-empty on/off | 1 | P |
| 2.28 | 28 | auto-empty "Smart" (1) / "Frequent" (absent) | 1 | P |
| 2.29 | 29 | "Freo Mind Mode" block, same layout as §2.5 | see above | P |
| 2.30 | 30 | "Auto-Empty Level": 1 "Quiet", absent "Strong" | absent | P |
| 2.31 | 31 | "Dust Bin / Dust Bag with Auto Disinfection" | 1 | P |
| 2.32 | 32 | "Smart Mop Wash with Hot Water" | 1 | P |
| 2.33 | 33 | "Intensive Cleaning for Large Soiled Areas" | 1 | P |
| 2.34 | 34 | "Obstacle Avoidance Strategy" | 1 "Smart" | P |
| 2.35 | – | never present | | |
| 2.36 | – | unknown; never moved | 1 | |
| 2.37 | 37 | "Auto Power-Off" | 1 | P |

Details that matter when parsing:

- In 2.29 the read side drops zeros. After "Do Not Use" the app sent
  `29.7 = {1: 0, 2: 2, 3: 20160}` and the robot returned `{2: 2, 3: 20160}`; a "Smart" entry
  comes back empty (`2a 00`), not as `{1: 0, 2: 0}`.
- 2.18.4.3 changes by itself when rooms are merged or split in the map editor.
- The nine fields that never moved (2.2, 2.11, 2.19, 2.20, 2.23 to 2.26, 2.36) and the
  three never present (2.9, 2.16, 2.35) are the remaining unknowns. §4 lists names that
  could belong to them.

---

## 4. Narwal's own names: the device shadow

Narwal's server keeps a copy of the robot's settings, the "device shadow", with two sides:
`desired` (what a client asked for) and `reported` (what the robot says it has). The app
read it once on opening "Privacy Settings" (11-17 14:51:48; the call is in
[CLOUD-API.md](CLOUD-API.md) §4). Both sides hold the same 45 keys. The key names are
Narwal's own and are the best names available for the numbered fields above.

**Almost every pairing below is by value or by name only (L).** The shadow was read once;
no setting was changed and the shadow read again to prove a pairing. The settings
themselves are P (§2); what is L is which shadow key belongs to which field.

| Shadow key (`reported` value) | `config/set` | `config/get` | App label | Pairing |
|---|---|---|---|---|
| `volume_percentage` (100) | 1 | 2.1 | volume | L, value |
| `disturb_mode {enabled, begin_time, end_time}` (true, 79260, 28920) | 5 `{1, 2, 3}` | 2.4 | "Do Not Disturb Mode" | L, value (the two odd times match) |
| `high_altitude_mode_enabled` (false) | 6 | 2.5 | "Plateau Mode" | L, name and value |
| `auto_add_detergent_enabled` (true) | 7 | 2.6 | "Automatically Add Detergent" | L, name and value |
| `child_lock_enabled` (false) | 8 | 2.7 | "Child Lock" | L, name and value |
| `clean_corner {clean_corner_freq, interval}` (3, 0) | 10 `{1, 2}` | 2.14 | "Intensive Corner Cleaning" | L, value |
| `boost_crossing_mode_enabled` (true) | 11 | 2.10 | "Stairless mode" | **G**, by the name alone |
| `dry_mop_strength` (3) | 13 | 2.12 | "Mop Drying Intensity" | L, value |
| `add_carpet_clean_option` (2) | 17 | 2.17 | mode for newly detected carpets | L, name and value |
| `carpet_clean_option` (2) | – | 2.15 | (moves with 17) | G |
| `clean_carpet_enabled` (true) | – | 2.8 | (moves with 17) | G |
| `custom_clean_strategy {strategy, area_option, clean_orders[]}` (1, 3, …) | 18 `{1, 2, 4}` | 2.18 | "Floor Cleaning" | L, shape and value |
| `clean_orders[] {is_modified, room_clean_order, default_room_clean_order, map_id}` | 18.4 `{1, 2, 3, 4}` | 2.18.4 | "House Cleaning Order" | L for the block; G for the order of the four. Both lists were empty in the shadow while `config/get` held seven ids |
| `clean_mop_freq` (3) | – | 2.13 | (follows the rewash area step) | G, value |
| `station_clean_mode` (5) | 21 | 2.21 | "Default Cleaning Mode for Dock" | L, name and value |
| `pet_mode` (false) | 22 | 2.22 | "Pet-friendly Mode" | L, name and value |
| `dust_gathering_enabled` (true) | 27 | 2.27 | auto-empty on/off | L, name and value |
| `smart_dust_gathering_enabled` (true) | 28 | 2.28 | auto-empty "Smart" | L, name and value |
| `quiet_dust_gathering_enabled` (false) | 30 | 2.30 | "Auto-Empty Level" "Quiet" | L, name and value |
| `dry_robot_bag_enabled` (true) | 31 | 2.31 | "Dust Bin / Dust Bag with Auto Disinfection" | L, name and value |
| `hot_water_wash_enabled` (true) | 32 | 2.32 | "Smart Mop Wash with Hot Water" | L, name and value |
| `massive_dirty_deep_clean_enable` (true) | 33 | 2.33 | "Intensive Cleaning for Large Soiled Areas" | L, name and value |
| `avoid_mode` (1) | 34 | 2.34 | "Obstacle Avoidance Strategy" | L, name and value |
| `automatic_poweroff_when_discharging` (true) | 37 | 2.37 | "Auto Power-Off" | L, name and value |
| `region {time_zone, offset, country, city, time_zone_posix}` | – | 2.3 | "Device Location" | L, value (identical strings) |
| `smart_clean_param` | 29 | 2.29 | "Freo Mind Mode" block | L, shape and value; parts below |

The parts of `smart_clean_param` against block 29. Each `…_strategy` is
`{is_customize_mode, <value>}`, which is the `{1: chosen by hand, 2: value}` shape of §2.5:

| Shadow key (`reported` value) | Block 29 | Pairing |
|---|---|---|
| `max_remop_count_strategy {is_customize_mode, max_remop_count}` (false, 0) | 29.1 | L, name and value |
| `overlap_level_strategy {is_customize_mode, overlap_level}` (true, 2) | 29.2 | L, name and value |
| `fan_level_strategy {is_customize_mode, fan_level}` (true, 4) | 29.4 | L, name and value |
| `mop_humidity_strategy {is_customize_mode, mop_humidity}` (false, 0) | 29.5 | L, name and value |
| `heavy_dirty_room_config[] {map_id, is_customize_mode}` (1, true) | 29.6 | **G**: the only part left for the only entry left; `{1: 1, 2: 1}` fits either order |
| `heavy_dirty_clean_config {enable_heavy_dirty_clean, heavy_dirty_clean_frequency_type, heavy_dirty_clean_frequency_minutes}` (false, 2, 20160) | 29.7 `{1, 2, 3}` | L, value (20160 on both sides) |

If the 29.6 guess holds, it is the per-map switch behind the map editor's "Room character"
(heavily soiled rooms), which would explain why that tool re-sends block 29. Not tested.

**Shadow keys with no known `config/set` field** (values as reported on this unit):
`corner_clean_mode` (0) · `carpet_clean_custom_enabled` (false) · `robot_clean_mode` (0) ·
`smart_clean_setting` (2) · `smart_clean_detection_enabled` (true) ·
`smart_deep_clean_enabled` (true) · `enable_dust_sensor_dirty_detect` (false) ·
`moisture_proof_pad_protect_enabled` (true) · `speech_control_enabled` (true) ·
`ai_voice_sound_effect_enabled` (false) · `ai_voice_sound_effect_for_waiting_enabled`
(false) · `show_vision_image_enabled` (true) · `privacy_policy_enabled` (true) · `language`
(1) · `pet_icon_type` (0) · `switch_back_to_main_map_after_temp_map_clean` (true) ·
`upload_configuration` (written over the web, [CLOUD-API.md](CLOUD-API.md) §4) ·
`scheduled_cleaning_tasks`, `scheduled_video_cruise_tasks`
([CLOUD-API.md](CLOUD-API.md) §9) · `bound_user_info` (the account; not reproduced).

Several of these are plausible owners of the `config/get` fields that never moved (§3), but
no value distinguishes them: eight of those nine fields read 1 and most of these keys read
true.
No pairing is offered.

**The `desired` side was stale on this unit.** It read `volume_percentage` 31, `pet_mode`
true and the Do Not Disturb times 79200 / 28800 while the robot reported 100, false and
79260 / 28920. A `config/set` from the app over the broker therefore does not update
`desired`; only `reported` follows the robot. In the shadow's metadata only
`upload_configuration` (and the schedule entries) carry a `desired` time stamp. L, from one
read.

---

## 5. Settings that are not robot messages on this unit

| App screen › row | What happened | |
|---|---|---|
| Device › "Device Location" | One web call per choice (`device/location/set`). Nothing over the broker. The robot's `config/get` 2.3 showed the new offset and country spelling two minutes later, by a road the broker listener did not hear. [CLOUD-API.md](CLOUD-API.md) §3 | P |
| Device › "Area Unit" | Square Meter, Square Foot or Ping. Cycled through all three, 11-17 14:43: nothing sent, neither broker nor web. The app converts; the robot reports in its own units | P |
| Device › "Device sharing" | Web only. [CLOUD-API.md](CLOUD-API.md) §6 | P |
| Privacy Settings › "Device Log Upload" | Written to the device shadow's `desired` side over the web. [CLOUD-API.md](CLOUD-API.md) §4 | P |
| Privacy Settings › "User Experience Program", "Live Video & Real Photo Privacy Policy" | Web only. [CLOUD-API.md](CLOUD-API.md) §5 | P for the first (joined and left once); the second was read, not changed |
| Map panel › 3D space › "Map selection" (Tracking period / Daytime / Night), "Map image quality" (Smooth / Balance / Clear) | "Night" chosen 11-17 15:46: nothing sent. App only. | P for "Map selection" (seen once); the rest not tested |
| Video › "Video function settings" › "Remote control speed" | Slider moved: no message, web or broker | P (seen once) |
| Third-party Control (Amazon Alexa, Google Home, Siri) | Siri shortcuts are a list on Narwal's server. No Matter, no HomeKit. [CLOUD-API.md](CLOUD-API.md) §7 | P for Siri |
| Schedule tab | Web only; the robot appears to start by its own clock. [CLOUD-API.md](CLOUD-API.md) §9 | P for "web only, no start command on the broker"; the rest L |
| Accessory Management, hours left | From the web (`consumables/list`); only the reset is a robot message (§2.6) | L |
