# Narwal Local WebSocket Protocol

Reverse-engineered notes on the local control protocol used by Narwal robot vacuums, as
implemented by this integration. Published so that other projects don't have to rediscover
it, and so that contributors have somewhere to send corrections.

**Status: partial and empirical.** Everything here was derived from live traffic against
real hardware and from decompiling the official Android app. Field names taken from the
app's compiled `BuilderInfo` are marked as such; everything else is inference from observed
bytes and should be treated as a working hypothesis. Several claims in this document's
history have been *reversed* after contradicting evidence — see
[Corrections](#corrections-things-this-project-got-wrong) at the end, which exists to make
that visible rather than quietly rewriting history.

Corrections and new captures are welcome. See [Contributing captures](#contributing-captures).

Passages tagged **(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)** come from one Freo Z Ultra, one
account in the US region and the iOS app, recorded 2026-11-13 to 2026-11-17 on the cloud MQTT
broker, on port 9002 and from the app's web traffic (@pdb0102). They are that unit's behaviour, not
a rule for other models. Besides the app, a second client of the same account was on the broker
throughout; the broker's envelope does not name the sender, so a read attributed to "the app" may
in places be that client's, while every command and settings change was timed against a named
action in the app. Their raw bytes are in [CAPTURES-CX7-2026-11.md](CAPTURES-CX7-2026-11.md). The
same captures
fill three companion documents: [SETTINGS.md](SETTINGS.md) (`config/get`, `config/set`),
[CLOUD-API.md](CLOUD-API.md) (the app's web calls) and [MAP-FORMAT.md](MAP-FORMAT.md) (the map
message and map editing).

---

## 1. Transport

| Property | Value |
|---|---|
| Endpoint | `ws://<robot_ip>:9002` |
| Server | WebSocket++ 0.8.2 |
| Framing | Binary WebSocket frames |
| Authentication | **None** |
| Encryption | None — payloads are cleartext protobuf |
| Concurrency | **One connection per source IP** |

Two consequences worth stating plainly:

**There is no authentication.** Anything on the same network segment can command the robot —
start a clean, return it to the dock, reboot it, or read the floor plan of the house. That is
the robot's design, not this integration's. Treat port 9002 the way you'd treat any other
unauthenticated LAN device and segment your network accordingly.

**The robot accepts one connection per IP.** A second connection from the same address is
refused with `connection with same ip, close old one`. In practice this means you must disable
the Home Assistant config entry before running a diagnostic script from the same host.

The robot also disconnects on a malformed frame — specifically on a mismatched header byte
(see below) — and refuses reconnection for roughly 10 seconds afterwards.

### Not all models speak this protocol

Three transports exist across the product line, and which one a robot uses is a property of
the hardware, not a setting:

| Transport | Port | Models observed | Local control? |
|---|---|---|---|
| WebSocket | 9002 | Flow (AX12), Flow 2, Freo Z10 Pro/Turbo (AX26), Freo X10 Pro (AX15), Freo Z10 Ultra (CX4), Freo Z Ultra (hardware CX7, cloud identity J5) | Yes — this document |
| ZeroMQ (ZMTP 2.0) | 6789 | Freo X Ultra (AX18/AX19) | No — cloud-mediated |

`nmap -p 9002 <robot_ip>` is the fastest triage. Most supported models broadcast when awake,
but the CX7 is an exception: it only responds to topics containing product key `hEA7OEshlx`
and its real cloud-assigned device ID. See the README's compatibility table for the current
per-model state.

This identity is verified for one global CX7/J5 on firmware `v01.13.11.02`. Earlier reports in
issue #5 associated CX7 with `BYWBPqSxeC` and firmware `1.12.10.02`; that key did not answer
addressed probes on the verified robot, and remains an unresolved regional or platform variant.

---

## 2. Frame format

Every frame — in both directions — is a small binary header followed by a protobuf payload.

```
Byte 0     0x01                  Frame type constant
Byte 1     len(topic) + 2        Header length byte — MUST match or the robot disconnects
Byte 2     0x22 or 0x2a          0x22 = field 4 (request / broadcast)
                                 0x2a = field 5 (command response)
Byte 3     len(topic)            Topic length, uint8
Bytes 4..  topic                 UTF-8, no trailing NUL
Remainder  payload               Protobuf, may be empty
```

### The header byte

```python
header_byte = len(topic.encode("utf-8")) + 2
```

This is the total length of the protobuf field-4 TLV that wraps the topic: one tag byte, one
length byte, and the topic itself. Getting it wrong is the single most common way to have the
robot hang up on you, and it fails *silently* — the connection simply drops.

```python
def build_frame(topic: str, payload: bytes = b"") -> bytes:
    topic_bytes = topic.encode("utf-8")
    return bytes([0x01, len(topic_bytes) + 2, 0x22, len(topic_bytes)]) + topic_bytes + payload
```

### Response frames

Command responses come back as field 5 (`0x2a`) with an **empty topic**, so the header byte
is `2` and there is no topic to parse. The payload carries the result directly:

```
01 02 2a 00 08 01
│  │  │  │  └──┴── protobuf: field 1 = 1  (SUCCESS)
│  │  │  └──────── topic length = 0
│  │  └─────────── field 5 → this is a response
│  └────────────── header byte = 0 + 2
└───────────────── frame type
```

Because the topic is empty, responses are **not self-identifying**. You cannot tell which
command a response belongs to from the frame itself. Serialize your commands, or you will
mis-attribute results — this integration holds a lock across send-and-await for that reason.

Serializing is not enough on its own. A response can arrive *after* its command has timed
out (1.3 s late in #108), and the keepalive sends commands of its own that are answered too.
The client therefore records every request that is owed a response, in send order, and hands
each response to the oldest one still waiting. A timed-out command keeps its place for a
further 10 s so its late answer is discarded rather than returned to the next caller.

The robot also closes any socket **60 s after the last command it received** (close 1000
`Idle timeout`; websocket pings do not count). `status/app_status_heartbeat` resets that timer, is
never answered, and does not wake a docked robot, which is why the client sends it on every
keepalive tick (#113; measured on the X10 Pro and the Flow).

Not every command is answered. Measured on a Freo X10 Pro (`v01.03.10.03`, awake) and, with
identical results, on a Flow (AX12, `v01.08.03.07`, docked and idle; latencies 3-5 ms):

| Command | Responses | Latency |
|---|---|---|
| `status/app_status_heartbeat` | **none** | — |
| `common/active_robot_publish` (either form) | 1 | 4–9 ms |
| `common/notify_app_event` | 1 | 45 ms |
| `status/get_device_base_status` | 1 | 5 ms |

A five-command wake burst drew exactly four responses on both models. A heartbeat must not hold a place in
the order, or it would swallow the next real answer.

---

## 3. Topics

Topics are MQTT-style paths, and the same names are used on the cloud MQTT transport and the
local WebSocket transport. That equivalence is one of the more useful facts in this document:
anything the app does over the cloud is, in principle, expressible locally on a WebSocket
model. It was established by [@northwestsupra](https://github.com/northwestsupra)'s combined
capture (§9).

Full form:

```
/<product_key>/<device_id>/<category>/<message_type>
```

```
/QoEsI5qYXO/71c53f01c14f49088338863e147bb53c/clean/start_clean
 └─ product key                              └─ short topic
    (model)   └─ device id (32 hex chars)
```

The product key identifies the model (`QoEsI5qYXO` = AX12 Narwal Flow); the device ID is
per-robot. Both are returned by `common/get_device_info`, but there's a bootstrap problem —
you need the device ID to build a topic, and you need a topic to ask for the device ID. This
integration resolves it by cycling known product-key prefixes during the wake burst and
reading the device ID out of the first broadcast topic the robot emits. The CX7 never
broadcasts and ignores incorrectly addressed requests, so its cloud-assigned device ID must
be supplied before connecting.

### Result codes

Command responses carry a result code in field 1:

| Code | Name | Meaning |
|---|---|---|
| 1 | `SUCCESS` | Accepted |
| 2 | `NOT_APPLICABLE` | Cannot do this now — wrong state, or unsupported on this firmware |
| 3 | `CONFLICT` | Already doing it (e.g. recall while recalling) |
| 4 | *(unconfirmed)* | Reported as "not ready" on some newer firmware; not yet reproduced |

**`SUCCESS` means "frame accepted", not "did what you meant".** This distinction cost this
project roughly two months (§10). Query commands return data in field 1 rather than a code,
so treat a non-integer field 1 as a successful data response.

On a CX7 (v01.13.11.02) the reads the app sends came back as
`{1: 1, 2: <data>}`, and `clean/current_clean_task/get` and `clean/cur_plan/get` answered
`08 02` (`{1: 2}`) whenever no cleaning job was in force: before a start, in the first second
after one, after a recall, and at the start of a cruise.

---

## 4. Sleep, wake, and keepalive

Most robots sleep aggressively. While awake they broadcast status every ~1.5 s; while asleep
they send nothing and ignore most commands — including map requests, which is the usual reason
rooms fail to appear in a fresh install. The CX7 never broadcasts and instead relies on
addressed polling, including `status/get_device_base_status`. Clients must treat successful
field5 responses as reachability for such models rather than waiting for a broadcast, renewing
broadcast subscriptions, or reconnecting when broadcasts do not arrive.

Working model:

- **Awake** — broadcasts every ~1.5 s. No broadcast for 15 s means it has gone back to sleep.
- **Wake burst** — `common/notify_app_event` ("app opened"), then
  `common/active_robot_publish` with a topic-subscription payload. Sent as a burst because
  neither is reliable alone.
- **Keepalive** — repeat every ~15 s to hold it awake; `status/app_status_heartbeat` and
  `developer/ping` also exist for this.
- **Subscription** — `common/active_robot_publish` carries a duration (this integration uses
  600 s) after which broadcasts stop even if the socket is still open.
  During a clean, a Flow on v01.09.06.07 broadcasts for only ~30 s (29.1-30.5 s measured)
  after each `active_robot_publish`, whatever the duration; heartbeat, `set_fan_level` and
  `get_device_base_status` do not restart broadcasts, but a re-subscribe does, including one
  sent inside a live window. The integration therefore renews every 20 s while a clean is
  active and leaves a docked robot alone
  ([#148](https://github.com/sjmotew/NarwalIntegration/issues/148),
  [#90](https://github.com/sjmotew/NarwalIntegration/issues/90)).

A live socket is therefore *not* evidence of a live data stream. Track broadcast age
separately from connection state.

**Over cloud MQTT a CX7 does broadcast** (v01.13.11.02; a second robot, not the one described above;
@pdb0102, 2026-11). A listening client on Narwal's broker, subscribed by topic name, received
`status/robot_base_status` on every change and every `status/time_line_status` entry without
sending anything. `status/working_status`, `map/display_map` and `status/point_navi_plan_traj`
arrived only while some client was "watching": the app sends `common/active_robot_publish` every
30 s while it is open, and the message carries 60,000 (read as a lifetime in ms; matched by value).
The app's body is `0a0b08d00f10d00f18d00f400010e0d4031800`
(`{1: {1: 2000, 2: 2000, 3: 2000, 8: 0}, 2: 60000, 3: 0}`); the second client of the same
account sends `0a0908d00f10d00f18d00f10e0d403` every 50 s.
On 2026-11-13 eleven gaps in those three streams matched the times the app was closed. A keep-alive
alone was not enough: on 2026-11-17 the app was open and sending it from 14:38, and nothing arrived
on `status/working_status` or `map/display_map` until a job started at 15:10:06. Whether the local
socket of this robot broadcasts was not tested (the local poller opened one connection
per request and never listened); the project's "Silent on CX7" list (§9) covers it.

---

## 5. Commands

Confirmed working on AX12 unless noted. Most take an **empty payload** — the topic is the
command.

### Common

| Topic | Effect |
|---|---|
| `common/yell` | Robot announces itself ("Robot is here") — used for `locate`. The app's "Locate Robot" sends this with an empty body, one message per press, answered `{1: 1}` (CX7, 2026-11-17) |
| `common/get_device_info` | `{1: product_key, 2: device_id, 3: firmware}` |
| `common/get_feature_list` | 84 feature flags |
| `common/reboot` | Reboot. The app's "Restart Robot" sends this with an empty body; answered `{1: 1}`. The robot's status stream stopped 5 s later and came back 59 s after that (14:49:39 → 14:50:38); the selected voice pack survived (CX7, 2026-11-17, seen once) |
| `common/shutdown` | Power off |

### Task control

| Topic | Effect |
|---|---|
| `task/pause` | Pause the current job |
| `task/resume` | Resume |
| `task/force_end` | Force stop. Can carry a list of what to end — see below |
| `task/cancel` | Cancel |

**What the app sends on a CX7** (v01.13.11.02; @pdb0102, 2026-11; bytes
in [captures §2 and §4](CAPTURES-CX7-2026-11.md)). All of these were sent by the app over cloud
MQTT and accepted; none was sent by us.

- `task/pause` (empty body; seen once, 2026-11-13 15:21:23): the robot stops where it is,
  `robot_base_status` 3.2 turns 1 and the
  activity value stays.
- `task/resume` (empty body): "Continue", and also the button "Issue resolved. Continue task." after
  a fault that did not end the job (clean-water tank empty, robot lifted).
- `task/cancel` was never seen from the app.
- When the next action is the hold-to-end, the app's "Pause" does not send `task/pause`; it sends
  only `task/force_end`. To stop a job and bring the robot home the app sent `task/force_end`,
  then `supply/recall`.

`task/force_end` came in five forms:

| Body | App action | Answer | What the robot did |
|---|---|---|---|
| `12 02 01 02` = `{2: [1, 2]}` | "Pause", then press and hold to end, on a running cleaning job (2026-11-13, seven times) | `08 01` | Ended the job and **stayed where it stood** |
| `0a 01 03` = `{1: [3]}` | "End mop drying" in the Dock panel (seen once) | `12 01 01` = `{2: [1]}` | Status `{1: 14, 12: 4}` → `{1: 14, 12: 6}` within 1 s |
| `0a 02 01 02` = `{1: [1, 2]}` | "End dust bag drying and disinfection" (seen once) | `12 02 01 02` = `{2: [1, 2]}` | Status `{1: 19, 18: 4}` → standby `{1: 1, 3: 1}` within 1 s |
| `0a 01 05` = `{1: [5]}` | The ✕ on "Dust cabinet disinfection" in the Dock panel (2026-11-17 20:23:40, seen once) | `12 01 01` = `{2: [1]}` | The disinfection ended: its entry left field 46 within 1 s; field 3, showing a mop drying in front, did not change ([captures §13](CAPTURES-CX7-2026-11.md)) |
| empty | Taking over the drive pad in the video view while the robot was returning to the dock (seen once) | `08 01` | The return ended: `{1: 10, 10: 1}` → `{1: 1, 3: 2}` → `{1: 21, 19: 1}` |

Field 1 therefore reads as a list of dock tasks to end: 3 = mop drying, 5 = dust-cabinet
disinfection, and 1 and 2, always sent together, for the dust-bag drying; which of the two stops
it is not shown (the integration's `_DOCK_TASK_FORCE_END_PAYLOADS` has `{1: 1}` for the dock bag
and `{1: 5}` for the dust bin, from a Flow 2). An earlier reading here, "1 and 2 = dust-bag drying
and dust-cabinet disinfection", was wrong: the disinfection is 5.

The answer's field 2 reads as one result per listed item, 1 = ended, 2 = nothing to end. On
2026-11-17 at 20:21:13 we sent `{1: [1, 2]}` over port 9002 while only the dust-cabinet
disinfection was running: the answer was `12 02 02 02` = `{2: [2, 2]}` and nothing stopped. Every
answer recorded fits (six, [captures §4 and §13](CAPTURES-CX7-2026-11.md)); matched by value. What
the two numbers in field 2 of the 2026-11-13 form stand for is not known.

### Dock / supply

| Topic | Effect |
|---|---|
| `supply/recall` | Return to dock. The app's "Recall" and the home button of its video view (CX7, 2026-11) |
| `supply/wash_mop` | Wash mop pads |
| `supply/wash_and_dry_mop` | Wash the mop pads, then dry them. This is what the app's "Wash Mop" ("Wash & Dry Mop" after a job) sends; `supply/wash_mop` was never seen from that app (CX7, 2026-11) |
| `supply/dry_mop` | Dry mop pads. The app's "Mop drying" (CX7, 2026-11-17) |
| `supply/dust_gathering` | Empty dust bin into the station. The app's "Dock dust emptying" (CX7) |
| `supply/dry_station_bag` | Dry and disinfect the dock's dust bag. The app's "Dust bag dry & disinfect" (CX7, 2026-11-17; also seen once on 2026-11-13, 16:33:50) |
| `supply/dry_dust_bag` | Dry and disinfect the robot's dust cabinet. **Not in the app's Dock panel on a CX7**: there the task ("Dust cabinet disinfection") runs by itself after a vacuum-only job and can only be cancelled. Sent by us once over port 9002 (2026-11-17 20:20:26, empty body): answer `08 01`, and the Dock panel showed "Dust cabinet disinfection" ([captures §13](CAPTURES-CX7-2026-11.md)) |

On a CX7 (v01.13.11.02; 2026-11-17) each of the five was one
press in the app's Dock panel, an **empty body**, and an answer of `08 01`. What
`robot_base_status` field 3 did next (bytes in [captures §3 and §4](CAPTURES-CX7-2026-11.md)):

| Command | Field 3 afterwards |
|---|---|
| `supply/dry_mop` | `{1: 14, 12: 4}` after 1 s ("Drying mop"); ended with `task/force_end {1: [3]}` |
| `supply/dust_gathering` | `{1: 19, 18: 1}` for 16 s (emptying), then `{1: 19, 18: 4}` (dust-bag drying); a timeline entry `{2: 9, 7: 1}` |
| `supply/dry_station_bag` | `{1: 19, 18: 4}` after 1 s (the app: "Drying dock dust bag", about 5 hours) |
| `supply/wash_and_dry_mop` | `{1: 14}` for 1 s, `{1: 14, 12: 3}` for 2 min 23 s ("Mop washing with hot water"), then `{1: 14, 12: 4}`; a timeline entry `{2: 4, 3: {1: 6}}`. With the robot off the dock (2026-11-13) it first drove home |
| `supply/recall` | `{1: 10, 10: 2}` after 1 s; field 11 read 2 (docked) 12 s later, the robot having been driven close to the dock by hand |
| `supply/dry_dust_bag` (sent by us over port 9002, not by the app) | No change while a mop drying was in front (`{1: 14, 12: 4}`); field 32 gained `{1: 14, 12: 6}` and field 46 a kind-24 entry. After a vacuum-only job the same task shows in field 3 as `{1: 14, 12: 6}` |

The app lets the user start a job while the dock is washing or drying; the start cuts the dock
chore short (2026-11-13).

### Cleaning

| Topic | Effect |
|---|---|
| `clean/start_clean` | **The real clean command.** Takes a `CleanTask` payload (§6) |
| `clean/plan/start` | Runs the plan **stored on the robot by the app**. Ignores your payload (§10) |
| `clean/easy_clean/start` | Quick clean |
| `clean/set_fan_level` | Suction — only applies while cleaning |
| `clean/set_mop_humidity` | Water level |
| `clean/current_clean_task/get` | Read back the task currently loaded — the key diagnostic tool (§11) |
| `clean/cur_plan/get` | Read back the running plan. The app sends it, empty body, beside `clean/current_clean_task/get` after every start. It answered `{1: 2}` with no job in force, 36 bytes during a two-room job and 736 bytes during a drawn-zone job, the zone's outline included (CX7, 2026-11-17; [captures §7.1](CAPTURES-CX7-2026-11.md)) |

On a CX7 (2026-11) the app was never seen to send `clean/plan/start`,
`clean/easy_clean/start`, `clean/set_fan_level` or `clean/set_mop_humidity`: every job it started
was a `clean/start_clean`. That app version offers no saved plan for a job.

### Map

| Topic | Response |
|---|---|
| `map/get_map` | ~80 KB, full map (§8) |
| `map/get_all_reduced_maps` | ~169 KB, every saved map |
| `map/get_editable_map` | Editor representation. The app reads it before and after every edit, with the body `08 01 10 00 18 00`; the answer is `{1: 1, 2: <map>, 3: <edit version>}`, about 12.5 KB, and it answers locally too (CX7, 2026-11) |
| `map/operation` | Every edit of the app's map editor (rooms, no-go zones, carpets, furniture, layout). Answers with the whole map. Accepted over port 9002 as well (CX7, 2026-11-16) — see [MAP-FORMAT.md](MAP-FORMAT.md) |
| `map/check_map_update_info` | Sent with an empty body by the app's "Experimental Functions" › "Furniture/Floor Material Updates"; answered `{2: <a map>}`, 15.9 KB (CX7, seen once, 2026-11-17) |

### Developer

| Topic | Effect |
|---|---|
| `developer/take_picture` | Single camera frame. **Refused (code 2) while docked; accepted while the robot is off the dock.** Measured on a Flow (fw v01.09.07.06) mid-clean, 2026-11-14: 30/30 accepted, 0.40 s mean round trip (0.35 to 0.65 s), about 2.4 frames/s sequential, 150 to 203 KB per frame. Every frame differs, the size is always a multiple of 16 and the entropy is 7.999 bits/byte: AES-CBC with a per-frame IV, almost certainly the first 16 bytes. The key is per device and held by the Narwal cloud ([#157](https://github.com/sjmotew/NarwalIntegration/issues/157)); no local topic returns it. A second WebSocket client from another IP can poll this while Home Assistant holds its own connection |
| `developer/get_robot_debug_image` | Cleartext carpet/planning debug PNGs |
| `developer/led_control` | Toggle the robot's LED |
| `developer/ping` | Ping/pong |

### Not found: what starts a cruise, and what carries manual driving

(CX7, v01.13.11.02; 2026-11-17.) Two things the app does left no
command on any of the 216 topic names the cloud listener was subscribed to:

- **A cruise** ("Cruise": the robot drives to chosen points and takes pictures). The one cruise
  seen was started by a schedule, and no start message appeared at its start time (§6).
- **Driving by hand** from the app's video view. During about two minutes of driving there was no
  drive command on a subscribed topic and no web call. The phone's traffic in that time was the
  video channel, busy in both directions, so the commands probably ride inside it; that is a guess.
  The video itself is set up by web calls ([CLOUD-API.md](CLOUD-API.md)).

A topic name outside the listener's list would also explain both. What the robot's status showed
during each is in §7.

---

## 6. The clean command

`clean/start_clean` takes a `CleanTask`:

```
CleanTask {
  1: map_id                     // from get_map field 2.1 — NOT always 1
  2: [ CleanItem {              // repeated, one per zone
       1: ZoneOption { 1: type, 2: zone_id }   // type 1 = room, 2 = free rectangle, 3 = whole house (no zone_id, order 0)
       2: CleanParam { ... }                   // mode, fan, water, mop strength, passes
       3: order                                // execution order, 1-based
     } ]
  3: TaskOption { 1: 0, 5: 0 }  // app sends {1: 0, 5: 0}; {1: 1, 5: 0} with Freo Mind on (CX7, Discussion #164)
  5: task_type
}
```

Notes that cost real debugging time:

- **`map_id` must be the robot's actual map id**, read from `get_map`. Hardcoding `1` happens
  to work on single-map households and is destructive elsewhere — a mismatched id has been
  observed to abort the job after ~1 s and clear the map selection in the Narwal app.
- **`clean/start_clean` works from the dock.** Sending it from an undocked STANDBY state has
  produced refusals on some firmware.
- **`ZoneOption` field 4 is not required.** It was reported as required on firmware
  v01.08.03.07; a capture of the app's own task on v01.09.05.01 shows the app omitting it.
  See [Corrections](#corrections-things-this-project-got-wrong).
- **`TaskOption` is not always empty.** Earlier captures showed it empty; on a CX7
  (v01.13.11.02, iOS app 2.10.90
  [Discussion #164](https://github.com/sjmotew/NarwalIntegration/discussions/164))
  the app sends `1a 04 08 00 28 00` (`{1: 0, 5: 0}`) and `{1: 1, 5: 0}` with "Freo Mind" on,
  with `CleanParam` tag 9 moving in step (`48 00` → `48 01`); the robot's own task readback then
  carries `1a 02 08 01`. Sending it empty still works.
- **A whole-house start from the app** uses `ZoneOption {1: 3}` with no zone id and order 0,
  and the robot's task readback lists every room (same capture).

### Verified against the app's own bytes

The strongest evidence available for this schema is a diff of our builder against a task
captured from the official app with matching settings, on the same firmware:

```
ours : 0a1c080112140a0408011003120a0804100418012003380318011a002804
app  : 0a1e080112160a0408011003120c08041004180120033803400218011a002804
                                                    ^^^^  CleanParam tag 8 = 2
```

Structurally identical. One field differs: `CleanParam` tag 8 = 2, which the app sends and we
never do. **Tag 8 is the coverage-precision setting** — 1 = *Standard*, 2 = *Meticulous* —
settled by a controlled capture pair on AX26 in which only that toggle moved and only the
byte `40 01` → `40 02` changed ([#70](https://github.com/sjmotew/NarwalIntegration/issues/70),
[#25](https://github.com/sjmotew/NarwalIntegration/issues/25)). The captured app task was
simply set to *Meticulous*.

### Narwal's own names for these fields (CX7)

(v01.13.11.02; @pdb0102, 2026-11-17.) Two of the app's web calls
carry this same task as JSON ([CLOUD-API.md](CLOUD-API.md)): the **task record** the app lists
under "Task record" (snake_case names, plain numbers) and the **schedule call** (camelCase names,
enum values by name). Set against the protobuf of the same start
(2026-11-17 15:10:05, bytes in [captures §1](CAPTURES-CX7-2026-11.md)):

| Protobuf | Narwal's name | Values seen | How sure |
|---|---|---|---|
| `CleanTask` 1 | `map_id` | 1 | Matched by value; the robot has one map |
| `CleanTask` 2 | `items` | one per room or zone | Confirmed: two rooms, two items |
| `CleanTask` 3 | `option` | `{1: 0, 5: 0}`, `{1: 1, 5: 0}` | |
| `CleanTask` 3.1 | `enable_smart_mode` | 0 "Custom", 1 "Freo Mind" | Confirmed by an app action (2026-11-13) |
| `CleanTask` 5 | `task_type` | 1 to 4, moving with the mode (below) | Matched by value |
| `CleanItem` 1 | `zone` | | Confirmed |
| `ZoneOption` 1 | `zone_type` | 1 room, 2 drawn zone, 3 whole house | Confirmed |
| `ZoneOption` 2 | `zone_id` | room id; 1 for a drawn zone | Confirmed |
| `ZoneOption` 3 | `selection_bounds` | the four corners of a drawn zone | Confirmed: same numbers on both sides |
| `ZoneOption` 4 | `cleaning_bounds` | the outline of a drawn zone, cell by cell | Confirmed: same numbers on both sides |
| `CleanItem` 2 | `param` | | Confirmed |
| `CleanItem` 3 | `order` | 1, 2, …; 0 for whole house | Confirmed by an app action |
| `CleanParam` 1 | `mode` | 2 vacuum, 3 mop, 4 vacuum and mop, 5 vacuum then mop | Confirmed |
| `CleanParam` 2 | `fan_level` | 1 to 4; the cleaning sheet calls them "Noise Reduction", "Standard", "Turbo", "Max" | 1 to 3 confirmed; 4 seen only as a Freo Mind default |
| `CleanParam` 4 | `mop_humidity` | 1 "Slightly dry", 2 "Standard", 3 "High" | Confirmed |
| `CleanParam` 5 | `sweep_time` | vacuum passes, 1 or 2 | Confirmed |
| `CleanParam` 6 | `mop_time` | mop passes, 1 or 2 (3 by position, not sent) | Confirmed |
| `CleanParam` 8 | `overlap_level` | 1 "Standard", 2 "Intensive" (coverage precision) | Confirmed |
| `CleanParam` 9 | `enable_smart_mode` | 0 or 1, in step with `option` 3.1 | Confirmed |
| `CleanParam` 3, 7, 10 | two names are left for three tags: `mop_strength_level` and `sweep_mop_sync_time` | 3 = 1, 7 = 1, 10 = 0 in every start seen | **Not placed.** Which tag carries which name was not shown by any capture |

Things to know about these names:

- The record lists more `option` names that have no tag yet: `enable_smart_deep_clean`,
  `enable_massive_dirty_clean`, `enable_maintain_after_clean`, `is_need_rebuild_map`,
  `build_new_map_before_clean`, `is_calibration` (all false in the record read). `option` tag 5 is
  unnamed. The record also has `excluded_room_ids`, `maintain_floor_items` and `debug_option`,
  with no protobuf counterpart seen.
- The record is tidied by the server, not a copy of what was sent: for a vacuum-only job it had
  `mop_humidity: 0` and `mop_time: 0` where the app had sent 2 and 1.
- The schedule call gives enum value names: `ZONE_TYPE_ROOM`, `CLEAN_MODE_SWEEP_MOP_SYNC` (the
  app's "Vacuum and mop"), `FAN_LEVEL_NORMAL`, `MOP_STRENGTH_LEVEL_NORMAL`, `MOP_HUMIDITY_NORMAL`,
  `OVERLAP_LEVEL_NORMAL`, `TASK_TYPE_SCHEDULED`, `SCHEDULE_TRIGGER_TYPE_CRON`. Going by the
  prefixes the enum types are `ZoneType`, `CleanMode`, `FanLevel`, `MopStrengthLevel`,
  `MopHumidity`, `OverlapLevel`, `TaskType`. Only these eight value names were seen. The number
  behind each name was not seen side by side; `CLEAN_MODE_SWEEP_MOP_SYNC` = 4 and `…_NORMAL` = 2
  are matched by the app's labels only.
- **The mode travels twice.** `CleanParam` 1 and `CleanTask` 5 moved together in every start
  (2026-11-13): vacuum 2 and 1, mop 3 and 2, vacuum and mop 4 and 4, vacuum then mop 5 and 3.
- **The readback drops what the mode does not use.** `clean/current_clean_task/get` with "Custom"
  repeated the start minus some `CleanParam` tags: vacuum only kept 1, 2, 5, 8; mop only 1, 3, 4, 6,
  8; vacuum and mop 1 to 8; vacuum then mop 1 to 6 and 8. Tag 3 is therefore kept wherever the job
  mops and tag 7 only for vacuum and mop.

### Room order (CX7)

(v01.13.11.02; 2026-11-17.) **The order travels in the start message
and nowhere else.** Choosing and dragging rooms on the app's "Adjust cleaning sequence" screen sent
nothing, neither over cloud MQTT nor as a web call. The start then lists the rooms in the chosen
order and numbers them in `CleanItem` 3. Hallway (room 4) first, Toilet (room 5) second:

```
0a4a0801121e0a0408011004121408021002180120022801300138014001480050001801121e0a04080110051214080210021801200228013001380140014800500018021a04080028002801
                ^^^^^^^^ room 4                                     ^^^^ order 1^^^^^^^^ room 5                                     ^^^^ order 2
```

The robot went to the Hallway first (timeline, [captures §2.3](CAPTURES-CX7-2026-11.md)). At that
moment its configuration held a different order: `config/get` field 2.18 was
`{1: 1, 2: 3, 4: {3: 05 04 06 07 01 02 03, 4: 1}}`, Toilet before Hallway
(the app's "House Cleaning Order", see [SETTINGS.md](SETTINGS.md)). It did not override the order
in the start. Seen once, with list order and `order` values in agreement; which of the two decides
was not tested. Room ids are per map and change when rooms are merged
([MAP-FORMAT.md](MAP-FORMAT.md)); read them from the map before each start.

### A drawn zone (CX7)

(v01.13.11.02; 2026-11-13 and 2026-11-17.) A zone drawn on the app's
map is one `CleanItem` whose zone is

```
ZoneOption { 1: 2                       // zone_type: drawn zone
             2: 1                       // zone_id; the app shows "Area1"
             3: [ {1: x, 2: y} ×4 ]     // selection_bounds: the rectangle as drawn
             4: [ {1: x, 2: y} ×n ] }   // cleaning_bounds: its outline, one map cell at a time
```

Coordinates are whole map cells (60 mm, see [MAP-FORMAT.md](MAP-FORMAT.md)), sent as
varints: a negative value is 64-bit two's complement and a zero is left out. The start of
2026-11-17 16:09:57 was 758 bytes: corners (7, 3) (19, 3) (19, −13) (7, −13) and 56 outline points
for a rectangle of about 0.7 × 1 m. It begins

```
0af305080112e6050acb05 0802 1001 1a0408071003 1a0408131003 1a0d081310f3ffffffffffffffff01 1a0d080710f3ffffffffffffffff01 2204080710032204080810…
```

and is whole in [captures §8](CAPTURES-CX7-2026-11.md). **That job ran to a normal end** (timeline
`1.5 = 1`, 101 s), the first zone job seen to do so; the three zone starts of 2026-11-13 ended
42 s in with fault 0x02310001, as every job did from 16:04 that day, room jobs included. A zone of
1.4 × 3 m carried 180
outline points.

This is where `ZoneOption` field 4 has a use. The "field 4 was never required" correction in §10
is about room cleans, and the app's room starts agree with it: they carry neither
field 3 nor field 4. For a drawn zone the app sends both. **Whether the robot needs field 4 for a
zone, or the four corners are enough, was not tested**: no start was sent by us.

While a zone job runs, `robot_base_status` 3.4 reads 4, `working_status` field 6 carries the zone's
id, and the timeline marks the zone as it marks a room (§7).

### Cruise is a job of its own (CX7)

(v01.13.11.02; one cruise, 2026-11-17 15:59.) The app's "Cruise" sends
the robot to chosen points to take pictures. The one seen was started by a schedule set one minute
ahead; a cruise schedule is a map id and a list of points in map cell coordinates, with no cleaning
parameters at all ([CLOUD-API.md](CLOUD-API.md)). On the robot's side:

- No `clean/start_clean` and no other command appeared on a subscribed topic at the start time.
  The robot appears to hold the schedule and start by its own clock; how the schedule reaches it
  was not seen.
- `robot_base_status` 3.1 = **24** with the stage in 3.22 (§7).
- `clean/current_clean_task/get` and `clean/cur_plan/get` answered `{1: 2}` at the start.
- `status/working_status` carried the cruise points as text in field 7 and a progress block in
  field 20 (§7).
- `status/point_navi_plan_traj` carried the planned route about once a second.
- `status/video_cruise_task_status`, a topic name from the app's strings, was subscribed and
  stayed silent.

---

## 7. Status broadcasts

### `status/robot_base_status` — primary state

Field names from the decompiled `BuilderInfo`; values live-validated where noted.

| Field | Meaning |
|---|---|
| 1 | `errorCode` (repeated; empty when healthy). A fault fills it with a message `{1: code, 2: 2, 3: text}` for some seconds (CX7) — see [Faults](#faults-on-one-cx7) |
| 2 | Battery %, **float32** |
| 3 | Nested task status — see below |
| 11 | Dock flag: 1 off the dock, 2 on the dock, 3 the dock is blowing the mops dry (3 matched by timing; CX7; see [Field 11](#field-11-on-one-cx7)) |
| 13 | Bound account UUID (string) |
| 20 | Dust box state (enum) |
| 21 | Dust bag state (enum) — *absent on AX12 v01.08.03.07* |
| 23 | Clean-water tank state (enum) |
| 24 | Sewage tank state (enum) |
| 25 | Device status code list |
| 26 | Active fan level |
| 29 | Active mop humidity |
| 32 | Repeated; each entry has the form of field 3. Reads as every state that is active or paused at once (CX7; see [Field 32](#field-32-on-one-cx7)) |
| 35 | Station bag health %, float32 — *absent on AX12 v01.08.03.07* |
| 36 | Station bag health reset time (Unix seconds) — **unverified** |
| 38 | **Disputed** — `100` on every observation. Read as battery *design capacity* in one place and as curing-agent consumption % in another; see §11 |
| 39 | Station bag state (enum) |
| 41 | Detergent remaining % (`heavyDetergentRemainPercent`) — **unverified**, `100` on every observation; see §11 |
| 47 | Charging status (enum) |

Fields 20/21/35/36/38/39/41 are the consumables group — see [Consumables and station wear](#consumables-and-station-wear).

Field 3 sub-fields:

| Sub-field | Meaning |
|---|---|
| 3.1 | Working status enum (below) |
| 3.2 | `1` = paused (overlays the cleaning state). Also set while a fault holds the job up and on a dock chore that is paused (CX7) |
| 3.4, 3.5, 3.6, 3.7 | Activity within a job, one field per mode (CX7; [table below](#robot_base_status-on-one-cx7)) |
| 3.7 | `1` = returning to dock |
| 3.10 | Dock sub-state (1 = docked, 2 = docking). With 3.1 = 10 after `supply/recall`, 2 came first and 1 later, while the robot was still driving (CX7, below) |
| 3.12 | Dock activity (2, 6 observed). 3 washing the mop, 4 drying the mop, 6 dust-cabinet disinfection (CX7, below) |
| 3.13 | While returning to wash the mop: 1 driving back, 2 docking (CX7; matched by timing) |
| 3.18 | Purpose unknown; `1` on CX7, where it is one of only two sub-fields present. On a second CX7: 1 while the dock empties the dust bin (16 s), 4 while it dries the dust bag (below) |
| 3.19 | `1`, with 3.1 = 21, while the robot is driven by hand from the app's video view (CX7) |
| 3.22 | Cruise stage, with 3.1 = 24 (CX7, below) |

**On the CX7 this message is close to useless as a state signal.** Field 3 is exactly
`{1: 19, 18: 1}` — none of 3.2, 3.7, 3.10 or 3.12 exist — and it did not change across 40 s
of polling while the robot physically drove back to its dock. It reported
`19` (TASK_COMPLETED) while driving and `2` (DOCKED_V2) moments after a clean was accepted,
and `is_docked` read `true` throughout, including while the robot was away from the dock.

It does eventually settle (the same robot later read `1` / STANDBY), so this is a lag rather
than a frozen field — which is worse to diagnose, because capabilities derived from it appear
and disappear. Clients should not gate commands on this message for non-broadcasting models;
send the command and let the robot refuse. Everything the predicates were blocking —
`clean/start_clean` with a room-and-mode CleanTask, `supply/recall`, `task/force_end` —
was accepted by the robot with `SUCCESS` in the same state.

**A second CX7 on the same firmware behaved differently** (@pdb0102, 2026-11). The two
paragraphs above stand as measured on the first robot. On this one,
`status/get_device_base_status` polled every 5 s over port 9002 followed three cleaning jobs, a
cruise, a manual drive and the dock's chores change for change, each within one poll of the
cloud's `status/robot_base_status`. Field 3 carried 3.2, 3.4, 3.10, 3.12, 3.18, 3.19 and 3.22 at
various times, and field 11 told docked from undocked. `{1: 19, 18: 1}`, the value the first robot
sat on, appeared here only for the 16 s in which the dock emptied the dust bin. Why the two units
differ is not known. What it showed is collected
[below](#robot_base_status-on-one-cx7).

**`WorkingStatus` values are empirical and deliberately do not match the app's compiled
`TaskType` enum**, whose numbering the field nominally uses. Trust live observation here:

| Value | Meaning |
|---|---|
| 1 | `STANDBY` — idle; also a transition state |
| 2 | `DOCKED_V2` — on dock (v01.07.23.00+, sub-field 4 = 1 while charging). **On v01.09.10.02 the robot also reports 2 while cleaning off the dock, with sub-field 4 = 3** (#124, #115, two Flow 2 robots); the integration promotes that pair to `CLEANING_V2` at parse time. Sub-field 4 therefore looks like a task kind (1 = charging, 3 = cleaning), with 2 meaning "a task is running" — the one observation that does not fit (status 2 off-dock with no sub-field 4, after a `start_clean` rejected during `wash_mop`) stays not-cleaning. |
| 4 | `CLEANING` |
| 5 | `CLEANING_ALT` — observed while the robot was physically stuck |
| 7 | `REMAPPING` — exploring/rebuilding; camera active |
| 10 | `DOCKED` |
| 14 | `CHARGED` — reported before 100%; use battery level for charge state |
| 19 | `TASK_COMPLETED` — transitional, returning to base |

Values 2, 17 and 19 were each discovered when someone's log flooded with an unmapped value.
**No error value has ever been observed** — a robot fault cannot currently be represented.
If you can capture one (pick the robot up mid-clean), that's a genuinely useful contribution.

That capture now exists for a CX7: the fault is not a `WorkingStatus` value at all but a block
in field 1 (see [Faults](#faults-on-one-cx7) and §11).

### `robot_base_status` on one CX7

(v01.13.11.02; @pdb0102.) Recorded 2026-11-13 to 2026-11-17
from the
cloud's `status/robot_base_status` and, for the jobs of 2026-11-16 and 2026-11-17, from
`status/get_device_base_status` over port 9002 as well; the two carry the same message and agreed
wherever both were recorded. Bytes: [captures §2 to §5, §8, §9, §12](CAPTURES-CX7-2026-11.md).
This is what one robot showed. It differs from the `WorkingStatus` table above in several places;
that table stands for the models it was measured on.

**3.1 followed the kind of job, not the activity:**

| 3.1 | Seen while | Activity in | How sure |
|---|---|---|---|
| 1 | Standby, on or off the dock; also where the robot stands after a fault that ended a job | 3.3 (1, 2, 6: below) | Matched by timing |
| 2 | A vacuum-only job is running | 3.4 | Confirmed by app actions |
| 3 | A mop-only job is running | 3.5 | Confirmed |
| 4 | A vacuum-then-mop job is running | 3.7 | Confirmed |
| 5 | A vacuum-and-mop job is running | 3.6 | Confirmed |
| 10 | Returning to the dock after `supply/recall` | 3.10 | Confirmed |
| 14 | Docked, with a dock chore | 3.12 | Matched by timing |
| 19 | Straight after a job, on or off the dock; the dock's dust path | 3.18 | Matched by timing |
| 21 | Driven by hand from the app's video view | 3.19 = 1 | Matched by timing; one session |
| 24 | A cruise is running | 3.22 | One cruise |

The job value stayed through mop washes, a mid-job recharge, a pause and a fault that could be
resumed. In the one recharge seen the robot went home at 10 % battery and resumed at 80 %. A client
that reads only 3.1 sees "cleaning" for the whole of a five-hour job.

**Activity within a job, one sub-field per mode, each with its own numbering:**

| Activity | Vacuum only 3.4 | Mop only 3.5 | Vacuum and mop 3.6 | Vacuum then mop 3.7 |
|---|---|---|---|---|
| Self test | 8 | 12 | 12 | 14 |
| Auto-empty at the start (16 s; not at every start) | 12 | | | |
| Leaving the dock | 7 | 11 | 11 | 13 |
| Vacuuming | 3 | | | 7 |
| Mopping | | 7 | | 9 |
| Vacuuming and mopping together | | | 7 | |
| Working a drawn zone | 4 | | | |
| Acquiring its position | 5 | | | |
| Returning to wash the mop | | | 2 | 2 |
| Washing the mop | | 4 | 4 | 4 |
| Returning to charge | | | | 6 |
| Driving home when done | 6 | | | |

The 3.7 column is matched to app screenshots. In 3.4, values 8, 12, 7 and 3 were read off the app
in that order while they ran (2026-11-16), and 4 came with the app's text "Area cleaning in
progress" (2026-11-17); 5 and 6 are from the order of events. The 3.5 and 3.6 columns are from the
order of events only.

**On the dock:**

| Field 3 | The app showed | How sure |
|---|---|---|
| `{1: 14, 12: 1}`, `{1: 14, 12: 2}` | A wash-and-dry request accepted; driving home for it | Matched by timing (2026-11-13) |
| `{1: 14, 12: 3}` | "Mop washing with hot water" | Confirmed by an app action |
| `{1: 14, 12: 4}` | "Drying mop" (planned 5 h) | Confirmed: switched on and off from the app |
| `{1: 14, 12: 6}` | "Dust cabinet disinfection" (planned 45 min; follows a job that vacuumed) | Confirmed |
| `{1: 19, 18: 1}` | Dust emptying, 16 s | Confirmed |
| `{1: 19, 18: 4}` | "Drying dock dust bag" (about 5 h) | Confirmed |

**Return, manual drive and cruise:**

| Field 3 | Seen while | How sure |
|---|---|---|
| `{1: 10, 10: 2}` | First value after `supply/recall`; also the last seconds before docking | Seen in two returns. This is the 3.10 of [#142](https://github.com/sjmotew/NarwalIntegration/issues/142) |
| `{1: 10, 10: 1}` | Later in the first return, for over a minute, while the robot failed to find its way home (the owner watched) | "1 = looking for the dock, 2 = driving to it" is a guess |
| `{1: 21, 19: 1}` | The robot is driven from the app's video view | Matched by timing; one session |
| `{1: 24, 22: 1}` | Cruise, first 5 s on the dock; again for 8 s after leaving it | One cruise; names from the order of events |
| `{1: 24, 22: 4}` | Cruise, leaving the dock | |
| `{1: 24, 22: 3}` | Cruise, driving the points (3 min 12 s) | |
| `{1: 24, 10: n, 22: 6}` | Cruise, points done, going home; 3.10 ran 1, 3, 1, 2 beside it | |

**Standby** is `{1: 1, 3: n}`. 3.3 = 1 was the usual value on the dock; 6 stood on the dock in the
minutes before two starts and before the cruise; 2 was seen only off the dock (after a fault that
ended a job, and after `task/force_end` on a return).

**3.2 = 1 reads as "held up", not only "paused by the user".** It was seen after `task/pause`; from
one second after a fault block appeared until `task/resume` (robot lifted, clean-water tank
empty), with the activity value unchanged beside it; and on dock chores that wait for another
one: `{1: 19, 2: 1, 18: 4}` (dust-bag drying paused) and `{1: 14, 2: 1, 12: 4}` (mop drying
interrupted when the robot was driven off the dock).

#### Field 11 on one CX7

**1 = off the dock, 2 = on the dock, 3 = the dock is blowing the mops dry.** 1 and 2 are confirmed
(they flip as the robot leaves and docks, in every job recorded). 3 is matched by timing, strongly,
and nobody stood at the dock to listen. The evidence
([captures §3](CAPTURES-CX7-2026-11.md)):

- **It follows the app's "Mop drying" on and off.** Robot docked at 100 %, no job: `supply/dry_mop`
  at 15:23:30, field 11 went 2 → 3 at 15:23:33; `task/force_end {1: [3]}` at 15:25:02, 3 → 2 at
  15:25:04 (2026-11-17; the local poll saw the same).
- **After a wash it comes 181 s into the drying.** `supply/wash_and_dry_mop`: washing until
  15:31:52, then field 3 = `{1: 14, 12: 4}` with field 11 still 2; 11 turned 3 at 15:34:53, when
  `working_status` field 8 (the drying's seconds counter) read 181. The same interval shows twice
  on 2026-11-13: a mop wash stopped by an empty clean-water tank, and field 11 turned 3 after 182 s
  and after 181 s of standing paused.
- **It can read 3 while field 3 reads plain standby.** A manual drive interrupted the drying; back
  on the dock field 11 read 2 for four seconds, then 3 from 15:42:34 until the robot next left
  (15:59:08), with field 3 = `{1: 1, 3: 1}` all the while. Field 3 does not always show a running
  drying; field 11 = 3 was then the only sign.
- **A short 3 after docking.** On 2026-11-17 it read 3 for 12 s, 11 s and 7 s after the three
  dockings that ended a vacuum job, a cruise and a zone job, with no mop drying to follow. A short
  blow of the dryer at arrival would fit; that is a guess. The docking of 2026-11-16 shows no
  such 3. It also read 3 for 1 to 10 s at the start of three mop washes (2026-11-13).
- **Through a self test it is simply what it was before the start.** In 20 recorded starts
  ([captures §3.4](CAPTURES-CX7-2026-11.md)) field 11 kept its value from the last status before the
  start through the self test in all 19 docked starts (3 in eleven, where the dock was drying mops
  or dust bag or had just been; 2 in eight); in two of them it then changed during the mop wash that
  came before leaving (2 → 3 → 2 at 15:43, 3 → 2 at 16:28, 2026-11-13). One start was off the dock.
- **It read 3 through the whole of a mid-job recharge** (10 % to 80 %, 95 min, 2026-11-13). The
  mops drying while the robot charges fits; it was not checked.

Not covered: `{1: 19, 18: 4}` (dust-bag drying) came with field 11 = 3 on 2026-11-13 after mopping
jobs and with 2 on 2026-11-17 after vacuum jobs. The reading above says the mops were drying
behind it in the first case; field 3 and field 32 did not show that.

**Two earlier readings are withdrawn.** Until this change this document read 3 as "on the dock
while a job is in progress", and "charging" was offered in
[Discussion #164](https://github.com/sjmotew/NarwalIntegration/discussions/164). Both came from
this same contributor and both are wrong: with no job and the battery at 100 % field 11 followed
the mop drying; two self tests at 100 % read 2; and the robot docked at 66 % with no job read 2.
Both readings had followed from a drying being on at the moments looked at. The "3 = charging"
reading in [#142](https://github.com/sjmotew/NarwalIntegration/issues/142) may have the same
cause; that is for the owners of those robots to check.

#### Field 32 on one CX7

Field 32 is repeated and each entry has the form of field 3. In every message looked at its first
entry equalled field 3; at times it holds more. It reads as the list of everything that is
running or waiting, where field 3 shows only the one in front
([captures §5.2](CAPTURES-CX7-2026-11.md)):

```
field 3 = {1: 14, 12: 4}     field 32 = {1: 14, 12: 4}  {1: 14, 12: 6}  {1: 19, 2: 1, 18: 4}
                             mop drying, dust-cabinet disinfection, dust-bag drying (paused)
field 3 = {1: 2, 4: 3}       field 32 = {1: 2, 4: 3}  {1: 19, 18: 4}
                             vacuuming; the dock's dust-bag drying goes on meanwhile
field 3 = {1: 14, 2: 1, 12: 4}   field 32 = {1: 14, 2: 1, 12: 4}  {1: 19, 2: 1, 18: 4}  {1: 21, 19: 1}
                             driven by hand; mop drying and dust-bag drying held up
```

When the middle sample was taken the app's Dock panel read "Dust cabinet disinfection" and "Dust
bag drying paused" for `{1: 14, 12: 6}` with `{1: 19, 2: 1, 18: 4}` behind it. This reading was made
from the recordings afterwards; no test was built around it. Field 32 does not list the drying
that field 11 = 3 points to when field 3 is at standby.

**Field 46 reads as the list of tasks running, each with a number, a kind and a stage.** This is
our reading of five days of recordings and of a test on the evening of 2026-11-17 in which the dock
commands were sent one at a time over port 9002 with the app open beside them ([captures §13](CAPTURES-CX7-2026-11.md)).
A second CX7 on the same firmware shows the same field in issue #171. Idle is `{1: {2: {1: 1}}}`.
Each entry of `46.1`:

| Path | Reads as | How sure |
|---|---|---|
| `46.1[].1` | A task number, not a task code. It rose with every new task (by 3 to 6 per dock task, more across a job), was never reused within a day, and was absent (a 0, which protobuf leaves out) on the first task after a restart and after a fault, low numbers following. The dock-bag drying carried 7, 3, 2, 23, 8, 40, 45, 144 and 149; `supply/dry_station_bag` sent twice with a stop between gave 144, then 149 | A new number for the same command: confirmed by commands sent. A counter that starts over: a guess |
| `46.1[].2` | The kind of task, then for tasks with stages the current stage: `{1: kind}` or `[{1: kind}, {1: stage}]` | Kinds matched to commands sent and to app actions |
| `46.1[].3` | `1` = paused: in all 80,867 recorded status messages an entry carried it exactly when field 32 held a paused state (`2: 1`), such as `{1: 19, 2: 1, 18: 4}` while the app read "Dust bag drying paused" | Matched by value |

| Kind | Task (the app's name) | Started by | `task/force_end` item |
|---|---|---|---|
| 1 | Idle | | |
| 3 | A cleaning job. Stages: 18 starting, 12 auto-empty, 5 leaving the dock, none while cleaning, 4 heading home, 20 washing the mop | A job start | |
| 4 | Returning to the dock | `supply/recall`; after a cancelled start | |
| 9 | Mop care ("Drying mop"). Stages: 18, 20 washing, 21 drying; a drying alone shows 21 throughout | `supply/dry_mop`, `supply/wash_and_dry_mop` | 3 |
| 12 | Dust emptying, about 16 s; kind 25 follows by itself | `supply/dust_gathering` | |
| 13 | Most likely the robot driven by hand from the video view (seen twice) | | |
| 24 | Dust-cabinet disinfection ("Dust cabinet disinfection"); follows each vacuum-only job by itself; no button for it in the app | `supply/dry_dust_bag` (sent by us; the app never sent it) | 5 |
| 25 | Dock dust-bag drying and disinfection ("Drying dock dust bag", about 5 hours) | `supply/dry_station_bag`; follows every emptying by itself | 1 and 2, sent together |
| 28 | A cruise | A schedule | |

So field 3 shows the task in front, field 32 the states of all of them, and field 46 adds kind,
stage and a number. When the dust-cabinet disinfection started beside a running mop drying
(2026-11-17 20:20:28), field 3 did not change, field 32 gained `{1: 14, 12: 6}` and field 46 a
kind-24 entry. Starting the dock-bag drying ended a running mop drying (20:24:10); a wash and dry
started during a dock-bag drying, and both went on (15:29). For telling the dock's tasks apart on
this unit, the kind in field 46 was enough, the two drying tasks included.

### `status/working_status` — metrics, not state

Names from the decompiled proto. This message reports *progress*, and reading state from it
is a mistake this project has made in both directions:

| Field | Meaning |
|---|---|
| 1 | `workingProgress`, float32 (0..1) |
| 2 | `coveredArea`, float32 — m² cleaned this session |
| 3 | `timeConsuming` — session elapsed seconds |
| 4 | `remainedTime` — seconds |
| 6 | `cleaningZoneId` — the room currently being cleaned |
| 8..17 | Station drying/sterilization/dust-bag timers. The cumulative counters (9/11/13/15/17) stay constant while idle — field 13 is `totalDryStationBagTime` (18000 = 5 h), once misread as cleaning area because 18000/10000 resembled a plausible 1.8 m² |

**On a CX7, over cloud MQTT** (v01.13.11.02; @pdb0102, 2026-11).
Whether this robot answers or broadcasts `status/working_status` locally was not tested; the
project's "Silent on CX7" list (§9) covers it. The cloud path delivered it twice a second,
with the counters moving once a second, while a client kept the stream alive and a job or a dock
chore was running: on 2026-11-17 the app was open and sending keep-alives from 14:38, yet no
`working_status` and no `display_map` arrived until the job started at 15:10:06. What the fields
held ([captures §3.2, §9, §10](CAPTURES-CX7-2026-11.md)):

| Field | Seen | How sure |
|---|---|---|
| 1 | Progress in **percent** (`50.0`, `100.0`), not 0..1. It counts the mop washes too: a single combined pass stood at 58 % when the robot went home to wash | Matched to app screenshots (2026-11-13) |
| 2 | Cleaned area, m² | Matched to app screenshots |
| 3 | Cleaning time, seconds. The app shows whole minutes, rounded down | Matched to app screenshots |
| 4 | Absent from every message of 2026-11-17 | |
| 5 | Repeated, one entry per room of the job: `{1: room id, 2: vacuum rounds done, 3: mop rounds done, 4: combined rounds done}` | 5.2 and 5.3 confirmed against the app; 5.4 and 5.1 matched by value |
| 6 | The room being cleaned; in a drawn-zone job the zone's id | Confirmed for rooms |
| 7 | During a cruise: text, `{"task":"[x: …\ny: …\n, x: …]"}`, the cruise points in map cells | One cruise |
| 8, 9 | Mop drying: seconds so far, and 18000 (the app's "about 5 hours"). Field 8 appeared 2 s after `supply/dry_mop` and with the drying state after a wash, counted by one a second, and went when the drying was ended or the robot left the dock | Matched by timing |
| 10, 11 | Dust-cabinet disinfection: seconds so far, and 2700 (45 min). Field 10 began one second after field 3 turned `{1: 14, 12: 6}` and counted on through a mop drying that ran in front of it | Matched by timing |
| 12 | A seconds counter for the current step; it keeps its last value after the job | Matched by timing only |
| 13, 15 | 18000 and 600 in every message | Agrees with the table above for 13 |
| 19 | `{1: 1}` while field 3 is `{1: 14, 12: 6}`, empty otherwise | |
| 20 | During a cruise: `{1: start time (ns), 2: seconds running, 3: points set, 4: points done}`. 20.2 stood still while the robot was held up by a fault; 20.4 went 1, 2, 3 as the app showed "Cruise point completed n/3" | Matched by value; one cruise |

### `map/display_map` — live position

Sent every ~1.5 s while cleaning. Field 2 is a moving window rather than the
complete route: a live Freo X Ultra capture repeatedly carried 30 points, with
the next observed window sharing four points with the previous one. Consumers
must join exact overlapping coordinates if they want to retain the whole route.

| Field | Meaning |
|---|---|
| 1.1.1 / 1.1.2 | Robot X / Y — float32, **decimetres** |
| 1.2 | Heading — float32 radians, [-π, π] |
| 2 | Rolling trajectory window `{1: x_bytes, 2: y_bytes}` |
| 5 | Dock reference position (constant) |
| 7 | Cleaned-area overlay: `{1: width, 2: height, 3: zlib grid}` — *not* the house map |
| 10 | Timestamp, **milliseconds** since epoch |
| 12 | Active room list |

A `display_map` with position `(0.00, 0.00)` and `ts=0` means the robot has lost map context —
it is the signature of a job about to abort, not a robot at the origin.

On a CX7 (v01.13.11.02; cloud path only: the local socket was not tested for it, see "Silent on CX7"
in §9) the positions in 1.1 are **map grid cells of 60
mm**, not decimetres: 12,282 positions of one
job, drawn 1:1 on the map's grid, lie on the floor and trace the furniture. The message arrived
twice a second, and its field 7 carried detected objects (7.5, 7.6) and treated spills (7.8, 7.9)
rather than a zlib grid. The two readings differ; the table above stands for the models it was
measured on. Details are in [MAP-FORMAT.md](MAP-FORMAT.md).

### Other broadcasts

| Topic | Content |
|---|---|
| `upgrade/upgrade_status` | 2 status, 3 progress, 4 stage, 7 current firmware, 8 target firmware |
| `status/download_status` | OTA download state |
| `status/time_line_status` | Session timeline — one message per row and status line the app shows; taken apart for a CX7 [below](#statustime_line_status-on-one-cx7) |
| `status/point_navi_plan_traj` | The route the robot plans to drive next: `{1: [{1: x, 2: y}, …]}`, float32, map cells. On a CX7 **broadcast on the cloud path** about once a second whenever the robot drove a planned route (cleaning jobs, a return to the dock, a cruise); see the note under "Silent on CX7" in §9 |
| `status/streaming_info` | Cloud path: about once a second while the app's live video is open, `{1: counter, 3: 1, 6: n, 7: n}` with 4 and 5 at times; it stops when the viewer leaves (CX7, 2026-11-17). The video itself does not travel on these topics ([CLOUD-API.md](CLOUD-API.md)) |
| `report/clean_report` | End-of-session summary: 3 elapsed, 6 start, 7 end, 12 detail, 33 end-reason string (localized) |
| `developer/planning_debug_info` | Bumper/cliff/mop-collision sensor debug |

A robot mid-OTA refuses commands it would normally accept. If `upgrade_status` and
`download_status` are chattering, `NOT_APPLICABLE` may mean "busy updating" rather than
anything about your payload.

On a CX7 (2026-11) `status/download_status` arrived on the cloud path as `08 02`
(`{1: 2}`) about once a second throughout every recording, idle or working, and did not change while
the robot
downloaded a 17 MB voice pack. There it says nothing about a download in progress.

### `status/time_line_status` on one CX7

(v01.13.11.02; @pdb0102, 2026-11.) The robot pushes one message for each
row and
each status line of the app's timeline. On the cloud path it needs no keep-alive and came in every
mode. Locally, `info/get_clean_time_line` returns the same entries as a list in field 2.1, with the
same time stamps (§11). Read from two full days of jobs with the app beside them; bytes in
[captures §2.3, §8, §9](CAPTURES-CX7-2026-11.md).

Everything sits inside field 1:

| Field | Meaning | How sure |
|---|---|---|
| 1.1 | Time stamp, nanoseconds since the epoch | Matched by value |
| 1.2 | Phase: 1 start and dock work, 4 cleaning, 5 fault, 6 job ended, 9 emptying the dust bin | Confirmed against the app |
| 1.3 | With phase 4: `{1: status, 2: work block, 5: strategy card, 6 and 7: lists}` (below) | |
| 1.4 | With phase 1: 1 self test, 4 washing the mop before or between passes | 1 and 4 confirmed |
| 1.5 | With phase 6, how the job ended: **1 completed, 7 ended by a fault, 9 ended by the user** | Confirmed |
| 1.6 | The fault block ([Faults](#faults-on-one-cx7)) | Confirmed |
| 1.7 | 1 = this message opens a new row | Matched by position |
| 1.8 | Number of the row. A cleaning job started again at 1; the dock actions and the cruise that followed a job went on counting from its last row | Matched by position |

Status values in phase 4 (1.3.1):

| Value | The app shows | How sure |
|---|---|---|
| 1 | A new row: a room, a drawn zone or a round begins (with the work block) | Confirmed 2026-11-17 |
| 2 | Nothing of its own: the room, zone or step is finished (with the work block) | Confirmed 2026-11-17 |
| 3 | "Mop rewashing in progress" (the drive back to wash) | Confirmed |
| 4 | "Mop washing with hot water" | Confirmed |
| 6 | A wash begins after `supply/wash_and_dry_mop` | Seen with both such commands |
| 9 | Paused | Confirmed |
| 11 | Recall: the drive home when the work is done | Confirmed |
| 13 | Resumed | Confirmed |
| 14 | "Charging in progress"; "Low battery. The robot started to return for charging" | Confirmed |
| 16 | Sent on leaving the dock | Confirmed |
| 17, 32 | "Vacuuming in progress" | 32 confirmed, 17 matched by timing |
| 20 | "Intensive Corner Cleaning" | Confirmed |
| 21 | "Carpet Detection and Cleaning" | Confirmed |
| 22 | The start of a mopping pass | A guess |
| 23 | A fault, with the block in 1.6 | Confirmed |
| 28 | Stopped after a fault; "Mop washing paused" | Matched by timing |

**The work block marks every room and every drawn zone with a start and an end entry.**

```
start  {1: {1: <time>, 2: 4, 3: {1: 1, 2: {1: <zone type>, 2: <id>, 3: 1, 4: <work>}}, 7: 1, 8: <row>}}
end    {1: {1: <time>, 2: 4, 3: {1: 2, 2: {1: <zone type>, 2: <id>, 3: 2, 4: <work>}}, 8: <row>}}

0a1e08c6f489b4b694bdf41810041a0c08011208080110041801200238014003     room 4 begins   (2026-11-17 15:10:34)
0a1c08da889caa9398bdf41810041a0c0802120808011004180220024003         room 4 is done  (15:12:42)
0a1e08d384c5dccbfcbdf41810041a0c08011208080210011801200238014002     zone 1 begins   (16:10:13)
0a1c08fbf2c5fbaefebdf41810041a0c0802120808021001180220024002         zone 1 is done  (16:11:14)
```

Zone type and id are those of the start command: 1 and the room id for a room, 2 and the zone's id
for a drawn zone (the app's "Area1"). `<work>` (1.3.2.4) is 2 vacuuming, 3 mopping, 4 both
(confirmed). 1.3.2.3 read 1 in every start entry and 2 in every end entry of 2026-11-17; in the
long jobs of 2026-11-13 it also counted steps within a row, which was not worked out. Seen the
same way over the cloud push and in the local `info/get_clean_time_line` answer.

With "Freo Mind" on, a new row also carries a **strategy card** in 1.3.5, which the app shows as
the room's card: 1.3.5.1 floor (1 wood, 2 tile; confirmed), 1.3.5.4 suction (4 = "Max";
confirmed), 1.3.5.5 and 1.3.5.6 mop humidity and downward pressure in an order not settled
(1 = "Slightly dry" / "Soft press", 2 = "Standard" / "Hard press"), and 1.3.5.3 and 1.3.5.7 on a
room's first vacuum row, one of which is the tag "Not cleaned for long" (a guess). A vacuum-only
card has 1 and 4 only. The first row of a job carries a list in 1.3.6 (the app's "Strategy"; 5 =
"Dynamic mop washing with hot water", confirmed; 1, 3, 4 are auto adjustment, space perception and
path planning in an order not settled) and the last a list in 1.3.7 (the app's "Execute"; 4 =
"Mop Drying", confirmed; 1, 2, 5 are dust cabinet disinfection, UV disinfection of the dust bag and
dock self-cleaning in an order not settled). "Smart cleaning strategy switching" has no value of
its own: the app shows it for a few seconds when the robot sends the vacuuming status again.

Outside cleaning jobs: `{2: 9, 7: 1}` when the dock empties the dust bin (at a job's start and
after `supply/dust_gathering`); `{2: 1, 4: 1, 7: 1}` and `{2: 4, 3: {1: 16}}` at the start of a
cruise as at the start of a cleaning job. The cruise seen got no closing entry.

#### Faults on one CX7

A fault is a block `{1: code, 2: 2, 3: text}`. The text is UTF-8 with Chinese labels: code, level,
domain, node, cause. It appears in two places at once:

- **`robot_base_status` field 1**, for some seconds: 10 s and 2 s for the lifted robot (cleaning
  job, cruise), 4 s and 3 s for the empty water tank. Field 1 is present and empty at all other
  times.
- **The timeline's 1.6**: with status 23 in phase 4 when the fault hit a cleaning job, or as an
  entry of phase 5 when it hit the cruise. One second later status 28 follows if the job is held,
  or the closing entry with **1.5 = 7** and the block repeated if the job is over.

| Code | The robot's text | The app showed | What it was, and what followed |
|---|---|---|---|
| `0x01010035` | not kept | "(2006) Water outlet error of the clean water tank. Please check if there's water in the tank." and "Mop washing paused" | The clean-water tank was empty. The job waited with 3.2 = 1; `task/resume` after a refill continued it (2026-11-13) |
| `0x02310001` (36765697) | Level Error; robot, perception application; main control board, perception node; "Robot Perception System Error!" | A request to restart the robot or contact customer service | Ended the job (1.5 = 7); the robot went to standby where it stood. On 2026-11-13 every job from 16:04 on ended this way exactly 42 s after work began. Gone on 2026-11-16; the cause was never found |
| `0x02310031` (36765745) | Level Error; robot, perception application; main control board, perception node; "robot hangs up in the air" | "(1017) The robot is suspended. Please restart it in an unobstructed location." with "Issue resolved. Continue task." | The robot was lifted off the floor. The job was held, not ended; `task/resume` continued it (2026-11-17, twice: in a cleaning job and in a cruise). The cleaning job closed with 1.5 = 1; the cruise went on and got no closing entry and no status 13 |

The app's four-digit numbers are its own.
The task record the app fetches from Narwal's server carries the same number in `error_code` for a
job a fault ended (36765697), and 0 for the job that was lifted and resumed
([CLOUD-API.md](CLOUD-API.md)). A brief lift during the cruise raised no fault at all (seen once).

### Consumables and station wear

Two sources, and they answer different questions.

**`consumable/get_consumable_info`** (queried, never broadcast) returns which parts want
attention — not how worn they are:

```
{1: ConsumableInfoPayload{
     1: maintainItems[],   // clean / check these
     2: replaceItems[]     // replace these
}}
```

Both lists are **packed repeated varints**. That matters more than it sounds: a decoder that
treats a repeated field as "an int, or a list of ints" gets neither — blackboxprotobuf hands
back a `str` whose code points are the values. A live capture from an AX12:

```
{'1': {'1': '\x04\x06\x08\n', '2': '\x03\x14'}}
   maintainItems = [4, 6, 8, 10]   wash ribs, universal wheel, side distance sensor, anti-winding brush
   replaceItems  = [3, 20]         side brush, station bag
```

An empty payload means nothing needs attention. **Do not confuse "parsed to nothing" with
"nothing to report"** — this project shipped exactly that bug, silently reporting healthy
consumables on a robot asking for six parts (§10).

`ConsumableMaintainItem`: 1 dust box, 2 dust filter, 4 wash ribs, 6 universal wheel,
7 cliff sensor, 8 side distance sensor, 9 water-tank sponge, 10 anti-winding brush,
11 smart-module sponge, 20 dust container.

`ConsumableReplaceItem`: 1 dust filter, 2 mop, 3 side brush, 4 clear-water filter,
5 roller brush, 6 detergent, 7 smart-module filter, 8 dust bag, 20 station bag,
21 silver ions, 22 curing agent, 23 heavy detergent, 24 inner dust box.

**Per-consumable remaining life % is believed cloud-only** — no local topic has produced it.
That claim is inherited rather than tested, and is listed in §11.

On a CX7 (v01.13.11.02; @pdb0102, 2026-11) the hours and bars on the
app's
"Accessory Management" page came from a web call to Narwal's server, made when the page opens
([CLOUD-API.md](CLOUD-API.md)); the robot was asked `consumable/get_consumable_info` at each opening
of the app, after the restart, after jobs and after a reset, never for that page, and answered `0a
00` every time. No robot-side source for the remaining
life was seen there either.

**`consumable/reset_consumable_info`** as the app sent it for "Replaced (timer reset)" on the part
"Replaceable insert bin" (2026-11-16, seen once; the app then said "Reset
successfully" and showed the full 2,160 h):

```
0a 03 12 01 18      {1: {2: [24]}}        answer: 08 01
```

24 is `ConsumableReplaceItem` 24, inner dust box, in a packed list in field 2. By the same layout a
maintain item would go in field 1; the app was never seen to send one, since on the parts opened
only the replacement side has a reset button.

**`status/robot_base_status`** carries the numeric/station side: fields 20, 21, 23, 24, 35,
36, 38, 39, 41. Which of them a robot sends varies by model and firmware, and absence is
normal rather than an error — an AX12 on v01.08.03.07 omits 21 and 35 entirely, so a client
that assumes a dust-bag health score exists will render a permanently empty gauge. Report
absent fields as unknown; do not substitute zero.

**What a CX7 sent in these fields** (v01.13.11.02; @pdb0102; five
cloud recordings, 2026-11-13 to 2026-11-17, 77,819 `robot_base_status` messages). Observations
only; they bear on the open questions in §11 without settling them.

| Field | Seen |
|---|---|
| 20 | `1` always, except `2` for 46 s on 2026-11-13 (16:06:41 to 16:07:27), robot off the dock; field 25.2 held `{1: 1, 2: 33685554}` (`0x02020032`) for the same seconds. The owner emptied the dust bin that afternoon; the minute was not noted, so "bin out" is matched by timing only |
| 21 | **Absent** from every message |
| 23 | `1` always, except `2` twice on 2026-11-13 (13:43:48 to 13:43:52 and 13:52:58 to 13:53:01): the clean-water tank was empty, both times. Field 25.5 held `{1: 1, 2: 16842805}` (`0x01010035`, the code of the fault block that field 1 carried in the same seconds) |
| 24 | `1` always. The dirty-water tank was never full in a recording |
| 25 | `{2: '', 3: '', 4: '', 5: '', 6: ''}` (`12001a0022002a003200`) except in the two cases above |
| 26 | Present during jobs and following the job's suction: 1, 2, 3, 4 all seen; absent at times on the dock |
| 29 | 1, 2, 3 during jobs that mop; absent in every message of the vacuum-only days |
| 35 | Present in all but 6 messages. A float that only fell: 17.46 on the morning of 2026-11-13, 8.56 on the afternoon of 2026-11-17. It stepped down at dust emptyings (15:10:27 and 15:26:42 on 2026-11-17, by 0.03 and 0.08) and by 0.667 at 13:34:30 on both 2026-11-13 and 2026-11-17. 0.667 a day is 100 in 150 days; that it is a daily step is matched by those two days only |
| 36 | `1786307669` in every message (2026-08-09 20:34:29 UTC). Nothing was reset on the station bag during the recordings |
| 38 | `100` in every message |
| 39 | `3` in every message |
| 41 | `100` in every message. No heavy-duty detergent cartridge is installed on this dock (the app: "Not installed") |
| 47 | **Absent** from every message, docked or not, charging or full |

So here field 23 = 2 did mean "clean-water tank needs attention" once, field 20 = 2
came with a status code of its own, field 35 behaves like a wear figure for the station bag, and
fields 38, 39 and 41 never moved in five days. Field 41 reading 100 with no cartridge installed
does not fit "detergent remaining". The battery was not at 100 % for most of 2026-11-13 while 38
read 100, which does not fit a battery reading either; "design capacity" is not ruled out.

---

## 8. Map data

`map/get_map` returns the full map under field 2.

One CX7's map was taken apart field by field, grid included, and every tool of the app's map
editor was captured as a `map/operation` message: see [MAP-FORMAT.md](MAP-FORMAT.md). It differs
from the tables below in a few places (units, 2.17, 2.26, 2.32 type 14, 2.33, room field 4); those
are set
out there, as one robot's observation.

| Field | Meaning |
|---|---|
| 2.1 | **Map id** — the value `CleanTask.map_id` needs |
| 2.3 | Resolution |
| 2.4 / 2.5 | Grid width / height |
| 2.6 | Coordinate transform: `6.1` = origin_y, `6.3` = origin_x |
| 2.8 | **Dock position** `{1: {1: x, 2: y}, 2: heading}` — decimetres |
| 2.11 | Door segments — room pair + two endpoints, 23 observed |
| 2.12 | **Rooms** — see below |
| 2.13 | Historical trajectory `{1: x, 2: y}` |
| 2.17 | Entire map, gzip-compressed (~20 KB) |
| 2.26 | Room boundary polygons, one per room |
| 2.32 | Furniture/annotations — type 14 doors, 2 furniture, 28 obstacles. Map-editor placed, **not** live detection |
| 2.33 | Map area |
| 2.34 | Creation timestamp |

Use field 2.8 for the dock, not field 48 — field 48 is position history and is unreliable
for this.

### Rooms (field 2.12)

| Sub-field | Meaning |
|---|---|
| 1 | `room_id` — the value `ZoneOption.zone_id` takes |
| 2 | `RoomType` enum (0–15) |
| 3 | User-assigned name (UTF-8, empty if never named) |
| 4 | Category — 1 = room, 2 = utility/small space |
| 8 | Instance index, 1-based ("Bathroom 2") |

When field 3 is empty, the app derives the name from the `RoomType` enum. That mapping is
**model-independent** — the app's `MapEnginei18nConfiger.roomTypei18nKey(int)` takes only the
enum, no product key — and resolves through one shared `en-US.json`:

| 0 Room | 1 Master bedroom | 2 Secondary bedroom | 3 Living room |
|---|---|---|---|
| **4** Kitchen | **5** Bathroom | **6** Toilet | **7** Balcony |
| **8** Dining room | **9** Closet | **10** Corridor | **11** Study |
| **12** Kids' room | **13** Entertainment room | **14** Storage room | **15** Others |

### Coordinate transform

```
pixel = (value_dm * 10) / (resolution / 10) - origin
```

`display_map` reports decimetres; `get_map`'s dock field is decimetres; some other map fields
are centimetres. Mixing them silently puts the robot in the wrong room on a rendered map.

---

## 9. Topic reference

Combined MQTT + WebSocket topic list contributed by
[@northwestsupra](https://github.com/northwestsupra) (issues #4, #5), merged from two
independent capture efforts. Direction is C→R (client to robot) or R→C.

Not all of these have been exercised locally. Rows this integration uses are marked ✓; the
rest are known-to-exist and unexplored — good starting points for anyone probing.

| # | Path | Dir | Category | Used |
|---|---|---|---|---|
| 01 | `/common/yell` | C→R | Common | ✓ |
| 02 | `/common/yell/response` | R→C | Common | ✓ |
| 03 | `/common/reboot` | C→R | Common | ✓ |
| 04 | `/common/shutdown` | C→R | Common | ✓ |
| 05 | `/common/get_device_info` | C→R | Common | ✓ |
| 06 | `/common/get_device_info/response` | R→C | Common | ✓ |
| 07 | `/common/get_feature_list` | C→R | Common | ✓ |
| 08 | `/common/active_robot_publish` | C→R | Wake | ✓ |
| 09 | `/common/active_robot_publish/response` | R→C | Wake | ✓ |
| 10 | `/common/notify_app_event` | C→R | Wake | ✓ |
| 11 | `/task/pause` | C→R | Task | ✓ |
| 12 | `/task/pause/response` | R→C | Task | ✓ |
| 13 | `/task/resume` | C→R | Task | ✓ |
| 14 | `/task/resume/response` | R→C | Task | ✓ |
| 15 | `/task/force_end` | C→R | Task | ✓ |
| 16 | `/task/force_end/response` | R→C | Task | ✓ |
| 17 | `/task/cancel` | C→R | Task | ✓ |
| 18 | `/task/cancel/response` | R→C | Task | ✓ |
| 19 | `/supply/recall` | C→R | Dock | ✓ |
| 20 | `/supply/recall/response` | R→C | Dock | ✓ |
| 21 | `/supply/wash_mop` | C→R | Dock | ✓ |
| 22 | `/supply/wash_mop/response` | R→C | Dock | ✓ |
| 23 | `/supply/dry_mop` | C→R | Dock | ✓ |
| 24 | `/supply/dry_mop/response` | R→C | Dock | ✓ |
| 25 | `/supply/dust_gathering` | C→R | Dock | ✓ |
| 26 | `/supply/dust_gathering/response` | R→C | Dock | ✓ |
| 27 | `/clean/start_clean` | C→R | Cleaning | ✓ |
| 28 | `/clean/start_clean/response` | R→C | Cleaning | ✓ |
| 29 | `/clean/plan/start` | C→R | Cleaning | ✓ |
| 30 | `/clean/plan/start/response` | R→C | Cleaning | ✓ |
| 31 | `/clean/easy_clean/start` | C→R | Cleaning | ✓ |
| 32 | `/clean/easy_clean/start/response` | R→C | Cleaning | ✓ |
| 33 | `/clean/set_fan_level` | C→R | Cleaning | ✓ |
| 34 | `/clean/set_fan_level/response` | R→C | Cleaning | ✓ |
| 35 | `/clean/set_mop_humidity` | C→R | Cleaning | ✓ |
| 36 | `/clean/set_mop_humidity/response` | R→C | Cleaning | ✓ |
| 37 | `/clean/current_clean_task/get` | C→R | Cleaning | ✓ |
| 38 | `/clean/current_clean_task/get/response` | R→C | Cleaning | ✓ |
| 39 | `/config/get` | C→R | Config | |
| 40 | `/config/get/response` | R→C | Config | |
| 41 | `/config/set` | C→R | Config | |
| 42 | `/config/set/response` | R→C | Config | |
| 43 | `/config/volume/set` | C→R | Config | |
| 44 | `/config/volume/set/response` | R→C | Config | |
| 45 | `/consumable/get_consumable_info` | C→R | Consumable | |
| 46 | `/consumable/get_consumable_info/response` | R→C | Consumable | |
| 47 | `/consumable/reset_consumable_info` | C→R | Consumable | |
| 48 | `/consumable/reset_consumable_info/response` | R→C | Consumable | |
| 49 | `/schedule/clean_schedule/get` | C→R | Schedule | |
| 50 | `/schedule/clean_schedule/get/response` | R→C | Schedule | |
| 51 | `/map/get_map` | C→R | Map | ✓ |
| 52 | `/map/get_map/response` | R→C | Map | ✓ |
| 53 | `/map/get_all_reduced_maps` | C→R | Map | ✓ |
| 54 | `/map/get_all_reduced_maps/response` | R→C | Map | ✓ |
| 55 | `/map/get_editable_map` | C→R | Map | |
| 56 | `/map/get_editable_map/response` | R→C | Map | |
| 57 | `/map/display_map` | R→C | Map | ✓ |
| 58 | `/map/display_map/response` | R→C | Map | |
| 59 | `/status/working_status` | R→C | Status | ✓ |
| 60 | `/status/robot_base_status` | R→C | Status | ✓ |
| 61 | `/status/upgrade_status` | R→C | Status | |
| 62 | `/upgrade/upgrade_status` | R→C | Status | ✓ |
| 63 | `/status/download_status` | R→C | Status | ✓ |
| 64 | `/status/time_line_status` | R→C | Status | ✓ |
| 65 | `/status/app_status_heartbeat` | R→C | Status | ✓ |
| 67 | `/report/clean_report` | C→R | Report | |
| 68 | `/clean/report` | C→R | Report | |
| 69 | `/developer/ping` | C→R | Developer | ✓ |
| 70 | `/developer/take_picture` | C→R | Developer | ✓ |
| 71 | `/developer/take_picture/response` | R→C | Developer | ✓ |
| 72 | `/developer/led_control` | C→R | Developer | ✓ |
| 73 | `/developer/planning_debug_info` | R→C | Developer | |
| 74 | `/info/get_clean_time_line` | C→R | Status | |
| 75 | `/info/get_clean_time_line/response` | R→C | Status | |
| 76 | `/supply/wash_and_dry_mop` | C→R | Dock | |
| 77 | `/supply/wash_and_dry_mop/response` | R→C | Dock | |
| 78 | `/supply/dry_station_bag` | C→R | Dock | |
| 79 | `/supply/dry_station_bag/response` | R→C | Dock | |
| 80 | `/clean/cur_plan/get` | C→R | Cleaning | |
| 81 | `/clean/cur_plan/get/response` | R→C | Cleaning | |
| 82 | `/map/operation` | C→R | Map | |
| 83 | `/map/operation/response` | R→C | Map | |
| 84 | `/map/check_map_update_info` | C→R | Map | |
| 85 | `/map/check_map_update_info/response` | R→C | Map | |
| 86 | `/map/get_vision_image` | C→R | Map | |
| 87 | `/map/get_vision_image/response` | R→C | Map | |
| 88 | `/map/enable_temp_map` | C→R | Map | |
| 89 | `/map/enable_temp_map/response` | R→C | Map | |
| 90 | `/task/get_continue_task` | C→R | Task | |
| 91 | `/task/get_continue_task/response` | R→C | Task | |
| 92 | `/status/get_device_base_status` | C→R | Status | ✓ |
| 93 | `/status/get_device_base_status/response` | R→C | Status | ✓ |
| 94 | `/status/point_navi_plan_traj` | R→C | Status | |
| 95 | `/status/streaming_info` | R→C | Status | |

Also observed but not in the table above: `/status/get_device_base_status` (C→R, full status
dump on demand) and `/developer/get_robot_debug_image` (C→R, cleartext carpet/planning PNGs).

Rows 76 to 95 were added from a CX7's cloud MQTT recording (v01.13.11.02; @pdb0102, 2026-11):
each is a topic the official app or the robot was seen to use, with the direction seen. §5 and §7
say what each carried. Of these, `map/operation`, `map/get_editable_map`,
`status/get_device_base_status`, `info/get_clean_time_line` and `clean/current_clean_task/get` were
also exercised over port 9002, and so were `clean/cur_plan/get` (answered `{1: 2}`,
robot idle), `task/get_continue_task` (empty body), `common/get_feature_list` and `config/get`
(read-only probes, 2026-11-17 about 16:20, one try each); the rest were only watched on the cloud
path.
`map/get_vision_image` (body `{1: 1, 2: <object number>}`) answered there with the address of an
encrypted picture ([CLOUD-API.md](CLOUD-API.md)); `map/enable_temp_map` and
`task/get_continue_task` are sent by the app by itself and were answered `{1: 2}` and with an empty
body. In those recordings, rows 43 and 44 (`/config/volume/set`), 21 and 22
(`/supply/wash_mop`), 17 and 18 (`/task/cancel`), 29 to 36 and 49 and 50 were subscribed and never
carried a message: the app did not use them. For rows 39 to 42 (`/config/get`,
`/config/set`) see [SETTINGS.md](SETTINGS.md): the app sets the volume with `config/set {1: n}`.

### Answered locally, previously unexplored

Probed read-only against a CX7 on fw `v01.13.11.02`. All returned data. Sizes are the raw
response frame.

| Topic | Size | Content |
|---|---|---|
| `/developer/get_robot_info` | ~830 B | Labelled sections: device/product id, network (**including the Wi-Fi SSID and PSK in cleartext**, over the unauthenticated socket), per-component firmware, and a battery block: level, real level, health %, charge cycles, charge-time-remaining, current, voltage, temperature |
| `/common/upgrade/get_firmware_version` | ~350 B | Per-module firmware: robot mcu/ble/cpu, base-station mcu/ble/cpu, vision ai/cpu, plus sensor modules (`0220_SS_LD02`, `0220_SS_CH01`) |
| `/config/get` | ~175 B | Settings block. Field 2.1 = `70` (volume-shaped), 2.4.2/2.4.3 = `79200`/`28800` — a 22:00→08:00 do-not-disturb window in seconds — 2.3 = timezone, plus ~8 unmapped flags. Mapped in [SETTINGS.md](SETTINGS.md) |
| `/region/get` | ~75 B | Timezone, UTC offset, country, city, and the robot's own wall clock |
| `/config/language/get_current_voice_info` | ~35 B | Language code, voice-pack version and pack id |
| `/info/get_clean_time_line` | ~330 B | Session timeline. `{1: 1, 2: {1: [entry, …]}}`; 4 bytes (`08 01 12 00`) when there is none; entries as in §7 |
| `/consumable/get_consumable_info` | 6 B | Empty payload when nothing needs attention — the §10 trap, and a useful fixture for it |

### Silent on CX7

Requested and never answered, idle and mid-clean. Worth recording so nobody re-probes them
hoping to substitute for the missing broadcasts:

`status/working_status` · `map/display_map` · `status/point_navi_plan_traj` ·
`info/get_clean_progress_info` · `robot/status/get` · `robot/task/status/get` ·
`info/battery_info` · `schedule/clean_schedule/get` · `config/key_mapping/get` ·
`operate/conf/get` · `voice/get_voice_list` · all 27 `clean_system/*` topics

A second CX7 (v01.13.11.02; @pdb0102, 2026-11) adds two notes. The list
above is
about **requests over the local socket** and stands.

- `schedule/clean_schedule/get` gave no answer locally there either, and neither did
  `schedule/get` (probed 2026-11-17 about 16:20, one try each; noted in the lab journal, no raw file
  kept). The likely reason: the app keeps schedules on
  Narwal's server and never sends this topic ([CLOUD-API.md](CLOUD-API.md)).
- `status/working_status`, `map/display_map` and `status/point_navi_plan_traj` are a different
  matter **as broadcasts on the cloud MQTT path**, where the same robot sends all three while a
  client keeps the stream alive (§4). `status/point_navi_plan_traj` came about once a second
  whenever the robot drove a planned route: 6,250 messages in a five-hour job on 2026-11-13, and on
  2026-11-17 117 during a two-room job, 25 during a return to the dock, 222 during a cruise and 45
  during a drawn-zone job ([captures §7.2](CAPTURES-CX7-2026-11.md)). No request for it was ever
  seen. So the data exists on the cloud path. Requesting it over port 9002 was not tested; the list
  above covers that.

### Confirmed cloud-only

These exist as topics but do not serve data locally:

| Topic | Behaviour |
|---|---|
| `get_vision_image` | Returns `NOT_APPLICABLE` — object-detection images are cloud-processed |
| `get_dynamic_map` | Times out, no response |
| Shortcuts / scene presets | Cloud-managed via Alibaba Alink IoT REST, no local WS equivalent |

On a CX7 (v01.13.11.02; @pdb0102, 2026-11) these things the app does
were web
calls to Narwal's own servers, with **no message to the robot on any subscribed topic**. They are
documented in [CLOUD-API.md](CLOUD-API.md):

| What | Seen |
|---|---|
| Schedules, cleaning and cruise: add, change, enable, delete | Web only. A scheduled cruise then started with no start command on the cloud path |
| Consumables: hours left and the bars on the "Accessory Management" page | Web only. The reset is a robot command (§7) |
| Task records, the cleaning report, the "History" statistics | Web only |
| Device location, device sharing, privacy policies, "Device Log Upload" | Web only; the last is written to a server-side "device shadow" |
| Siri shortcuts ("Third-party Control") | Web only, stored per phone: the shortcut list went to Narwal's own server. The Alibaba IoT hosts the app contacts were not read |
| Live video and talk | Set up by web calls; the stream is not on these topics. The robot reports `status/streaming_info` meanwhile |
| "Area Unit" (m², ft², Ping) | Kept in the app; nothing sent anywhere |

---

## 10. Corrections: things this project got wrong

Published deliberately. Every entry below was stated confidently, acted on, and later
contradicted by evidence — if you are building against this protocol, these are the traps.

### `clean/plan/start` is a plan-runner, not a clean command

From 2025 until July 2026 this project believed `clean/plan/start` was the room-clean command
and that `clean/start_clean` was wrong. It is the other way round. **`clean/plan/start`
discards your payload and runs the plan the Narwal app last saved on the robot** — and it
returns `SUCCESS` while doing so.

Four separate payload-schema "fixes" were shipped against that topic. Each one returned
`code=1` and changed nothing, because the bytes were never read. Users reported the wrong room
cleaning; we kept re-encoding the room list.

Three contributors independently reached the correct answer — [@jgus](https://github.com/jgus),
[@Sean-StarLabs](https://github.com/Sean-StarLabs) and [@sytchi](https://github.com/sytchi) —
on different hardware, before it was accepted.

**Lesson: when a command ACKs successfully but has no effect, verify the topic contract before
touching the payload.** A `SUCCESS` response is not evidence that the robot read your bytes.

### `ZoneOption` field 4 was never required

Reported as mandatory on firmware v01.08.03.07, and believed for three days, which delayed a
merge. A capture of the app's own clean task showed the app omitting field 4 entirely — and a
firmware that genuinely required it would break the official app. Treat "field X is required"
as a hypothesis until a capture of the app's traffic confirms it.

The field does exist. On a CX7 (v01.13.11.02, 2026-11) Narwal's name for it is
`cleaning_bounds`, and the app fills it, together with field 3 (`selection_bounds`), for a zone
drawn on the map; for a room it sends neither (§6).

### `robot_base_status` field 11 = 3 was not "a job in progress"

This document said, from 2026-11-16 to this change, that field 11 = 3 on a CX7 means "on the dock
while a job is in progress"; "charging" was also on offer. Both readings came from one contributor
(@pdb0102, [Discussion #164](https://github.com/sjmotew/NarwalIntegration/discussions/164)) and
were drawn from one afternoon in which, as it turned out, the dock was drying mops every time
anyone looked. A day with the dock's own buttons pointed to another reading (matched by timing, not
proven): 3 followed "Mop drying" on and off within two seconds on a robot that was docked, full and
idle (§7).

**Lesson: a value that correlates with "job running" in every capture may only correlate with
what jobs leave behind.** Switch the suspected cause on and off by itself before naming a field.

### The room-name table was wrong for everyone

A user reported that room labels differed on Flow 2. A per-model override map was added to fix
"the Flow 2 case". The real cause was that the shared `RoomType` table was misaligned from
index 5 for *every* model, and the override entrenched the error. Decompiling
`roomTypei18nKey(int)` showed it takes no model argument at all.

**Lesson: a device-specific symptom usually means the shared table is wrong for everyone.**

### Enum values discovered one bug report at a time

`WorkingStatus` values 2, 17 and 19 were each found when a user's log flooded with an unmapped
value — every discovery shipped after someone hit it. `ERROR` remains a placeholder. Ask
contributors holding an APK decode for the *complete* enum rather than mapping values
reactively.

### A parse failure that looked exactly like good news

`consumable/get_consumable_info` returns its `maintainItems` / `replaceItems` lists as packed
repeated varints, which blackboxprotobuf surfaces as a `str`. The parser accepted "an int, or a
list of ints", so `int('\x04\x06\x08\n')` raised, the exception was swallowed per-item, and both
lists came back empty. Empty means "nothing needs attention" — so a robot asking for six parts
was reported as perfectly healthy, for as long as the feature had existed.

Nothing looked broken from the outside, which is the point: the failure mode of a `try/except
continue` inside a decoder is a confident wrong answer. Two habits fall out of it —
**distinguish "parsed to nothing" from "reported nothing"**, and **check a decoder against a
device in a known-bad state**, since anything that returns empty looks correct on a healthy one.

---

## 11. Open questions

Concrete, and each one is answerable with a capture rather than an argument:

**How many suction levels exist — answered.** The app 2.7.92 proto carries five (`MUTE`,
`NORMAL`, `STRONG`, `DEEP`, `SUPER`, values 1–5). Its English resources label those values
Quiet, Standard, Strong, Super Powerful and Ultra Powerful. AX26 captures show its highest
available tier sending tag 2 = **4** (`DEEP`), with the tier below it sending 3 (`STRONG`), so
`SUPER` (5) is unreachable from that model's app UI
([#70](https://github.com/sjmotew/NarwalIntegration/issues/70)). A Flow 2 accepted a room-clean
payload containing tag 2 = **5** for every room and reported the same value from
`clean/current_clean_task` while cleaning, confirming that `SUPER` is a real device-supported
tier. The app's ordinary picker still presents values 1–4 and adds value 5 through a separate
optional `enableSuperLevel` path. The live `clean/set_fan_level` enum (`SweepFanLevel`) has no
`SUPER`; the app maps 5 down to `STRONG` there. The integration instead clamps a live level-5
request to `DEEP` (4), the highest tier that endpoint can represent, while retaining level 5
as the pending setting for the next task. Home Assistant select entities also advertise the
previous `Ultra` spelling beside `Ultra Powerful`: the select service validates options before
entity-level alias normalization, so keeping that option is required for existing automations.

**The error state — answered on one unit.** It is not a `WorkingStatus` value. On a Freo Z
Ultra (CX7, `hEA7OEshlx`, v01.13.11.02;
[Discussion #164](https://github.com/sjmotew/NarwalIntegration/discussions/164), @pdb0102,
captured on the cloud MQTT path and since then over the local socket, below) a fault arrives in
**`robot_base_status`
field 1** as a message `{1: code, 2: 2, 3: text}` — for example code `0x02310001`
(36765697), text "Robot Perception System Error!" — while field 3.1 keeps the job's value for a
few seconds and then goes to `{1: 1, 3: 2}`. Field 1 empties again within seconds. On
`status/time_line_status` the job closes with **1.5 = 7**, against `1` for a normal end and `9`
for a stop from the app. A second fault the same day (clean-water tank, `0x01010035`) arrived
the same way and was resumable with `task/resume`. The integration does not yet surface this;
it is the obvious shape for an error sensor.

**The same block over port 9002 (same unit, 2026-11-17; the local repeat that was pending).** A
two-room vacuum job was running; the robot was lifted and held. `status/get_device_base_status`,
polled every 5 s, answered with field 1 filled twice:

```
local 15:10:54  field 1 empty                                3 = {1: 2, 4: 3}         vacuuming
local 15:10:59  field 1 = {1: 36765745, 2: 2, 3: <text>}     3 = {1: 2, 4: 3}
local 15:11:04  the same block                               3 = {1: 2, 2: 1, 4: 3}   3.2 = 1 while it waits
local 15:11:09  field 1 empty                                3 = {1: 2, 2: 1, 4: 3}
local 15:11:14  field 1 empty                                3 = {1: 2, 4: 3}         after "Continue task"

field 1:  08b180c411 1002 1ab401 0ae99499e8afafe7a0813a30783032333130303331…   ("错误码:0x02310031 … 原因:robot hangs up in the air")
```

The code is `0x02310031` (36765745), the robot's text "robot hangs up in the air", the app's
message "(1017) The robot is suspended. Please restart it in an unobstructed location." The cloud's
`robot_base_status` showed the same block from 15:10:59 to 15:11:09. Whole answers and the text
are in [captures §2](CAPTURES-CX7-2026-11.md). Three things follow:

- **The block stood for about 10 s here, and a 5 s poll caught it twice. That was luck.** In the
  four sightings on the cloud it stood 10 s, 2 s (the same lift fault during the cruise) and 4 s and
  3 s (the water-tank fault of 2026-11-13). The 5 s local poll caught one of the two it could have
  seen: it missed the 2 s one in the cruise. A client that polls should take the fault from the
  timeline instead (`info/get_clean_time_line`, below), where it stays.
- **Unlike `0x02310001` this fault did not end the job.** 3.1 stayed 2 and there was no closing
  entry. The app's "Issue resolved. Continue task." sent `task/resume` with an empty body
  (15:11:13, answered `08 01`), and the robot went on.
- **The job then closed with end reason 1**, a normal end, although a fault and a resume lay in
  between (15:14:17, `{2: 6, 5: 1}`). The end reason alone does not say that a job ran clean.

On the timeline the lift left three entries, the same over the cloud push and in the local
`info/get_clean_time_line` answer: 15:10:58 status 23 with the block in 1.6, 15:11:08 status 28
(stopped), 15:11:13 status 13 (resumed). The same fault during a cruise came as an entry of phase 5
(`{2: 5, 6: <block>}`) followed by status 28. All fault codes met, and the timeline's
values, are in §7. Seen locally: this one fault, once (and missed once, in the cruise). The fault of
a job that ends with
`1.5 = 7` was not repeated locally (it has not occurred since 2026-11-13).

**Pass count is two fields — answered.** `CleanParam` tag 5 is vacuum passes and tag 6 is
mop passes. Two app starts for the same room that differ only there show `28 02 30 01` against
`28 01 30 02`, and `clean/current_clean_task/get` echoes the split
([Discussion #164](https://github.com/sjmotew/NarwalIntegration/discussions/164), CX7
v01.13.11.02). The integration still exposes one control that sets both.

**Field 3 carries a different activity sub-field per work mode (one unit).** The same capture
shows 3.1 following the running job's mode and the activity sitting in a mode-specific
sub-field: vacuum only `{1: 2, 4: n}`, mop only `{1: 3, 5: n}`, vacuum and mop `{1: 5, 6: n}`,
vacuum then mop `{1: 4, 7: n}`. The 3.6 list in §7 and on
[#142](https://github.com/sjmotew/NarwalIntegration/issues/142) is therefore the vacuum-and-mop
column only, and the "2 while cleaning off the dock" (#124) and "5 while stuck" notes in §7
may be the same activity numbered differently per column. Matched to app screenshots for 3.7
(vacuum then mop): 14 self test, 13 leaving the dock, 7 vacuuming, 9 mopping, 2 returning to
wash the mop, 4 washing the mop, 6 returning to charge. For 3.4 (vacuum only): 8 self test, 12
auto-empty, 7 leaving the dock and 3 vacuuming were read off the app in that order (2026-11-16), 4
working a drawn zone came with the app's text (2026-11-17), 6 driving home is from event order.
Dock-side states seen: `{1: 14, 12: 4}` mop drying, `{1: 14, 12: 6}`
dust-cabinet disinfection, 3.18 = 4 dust-bag drying. **Field 11**: 1 off the dock, 2 on the dock,
**3 = the dock is blowing the mops dry** (matched by timing, strongly). The reading given here
before, "on the dock while a job is in progress", came from this same contributor and is
**withdrawn**: on 2026-11-17 field 11 followed the app's "Mop drying" on and off within two
seconds on a robot that was docked, full and idle; after a wash it turned 3 exactly 181 s into the
drying; it read 3 for 7 to 12 s after each docking that ended a job that day; and through a self
test it is simply what it was just before the start (19 docked starts). The evidence and what it
leaves open are under
[Field 11](#field-11-on-one-cx7) in §7. **Confirmed over the local socket on the
same unit** (second capture in the discussion, 2026-11-16): `status/get_device_base_status`
polled every 5 s through a vacuum-only job answered 31 of 31 times (53 of 53 counting the
timeline and task reads made beside it; the "48 of 48" posted in the discussion was this
contributor's miscount) and showed the same field 3
and field 11 transitions the cloud saw, within seconds: `{1: 1, 3: 6}` on the dock, then
`{1: 2, 4: 8}` self test, `{1: 2, 4: 12}` auto-empty, `{1: 2, 4: 7}` leaving the dock,
`{1: 2, 4: 3}` vacuuming, `{1: 2, 4: 6}` driving home, `{1: 19, 18: 4}` and `{1: 14, 12: 6}` back
on the dock. Field 11 flipped 2 → 1 on leaving and back to 2 on docking. The fault block has
since been seen locally too (the error-state answer above). Whether other models agree is the open
question; a Flow capture of
the same four starts would settle it.

**More field 3 states on the same unit (2026-11-17).**
Each was seen on the cloud and, except `{1: 1, 3: 2}`, in the local 5 s poll; the tables and how
sure each is are in
[§7](#robot_base_status-on-one-cx7):

| Field 3 | Seen while |
|---|---|
| `{1: 2, 4: 4}` | Working a drawn zone; the app: "Area cleaning in progress" (the reading from event order, now with the app's text) |
| `{1: 24, 22: n}` | A cruise: 22 = 1 preparing, 4 leaving the dock, 3 driving the points, 6 going home |
| `{1: 21, 19: 1}` | Driven by hand from the app's video view |
| `{1: 10, 10: n}` | Returning to the dock after `supply/recall`: 2 first, 1 later; the 3.10 of [#142](https://github.com/sjmotew/NarwalIntegration/issues/142) |
| `{1: 14, 12: 3}` | The dock is washing the mop |
| `{1: 19, 18: 1}` | The dock is emptying the dust bin (16 s) |
| 3.2 = 1 beside any of these | Held up: during a fault that waits for "Continue", and on a dock chore that is paused or interrupted, as well as after `task/pause` |
| `{1: 1, 3: 1}`, `{1: 1, 3: 6}`, `{1: 1, 3: 2}` | Standby: on the dock (1, 6) and off it (2) |

Not seen with the local poll running: any mopping job (3.5, 3.6, 3.7), a pause from the app, a
job ended from the app, a recharge. Those rest on the cloud recording of 2026-11-13 alone.

**Consumables — several, tracked together in
[#79](https://github.com/sjmotew/NarwalIntegration/issues/79).**

- *What is `base_status` field 38?* It reads `100` on every observation, and this project
  describes it as battery design capacity in one place and curing-agent consumption % in
  another. Both survive the data; one is wrong.
- *Is field 41 really detergent remaining?* The name `heavyDetergentRemainPercent` comes from
  the decompiled app. It has only ever been observed as `100`, on a robot whose battery also
  reads `100`. A capture taken side by side with a visibly low cartridge settles it.
- *Are per-consumable life percentages truly cloud-only?* The app shows them; no local topic
  has produced them. The claim is inherited, not tested. One data point for it: on a CX7
  (v01.13.11.02, 2026-11-16) the app fetched the hours and bars from Narwal's server
  when its parts page opened ([CLOUD-API.md](CLOUD-API.md)) and asked the robot nothing for them.
  That shows where the app gets them, not that the robot cannot give them.
- *Which models send fields 21 and 35?* Absent on AX12 v01.08.03.07. One data point is not a
  rule, and clients currently render a permanently empty dust-bag gauge because of it.
- *Are the tank/box/bag enum thresholds right?* We treat `1` as OK and `>= 2` as attention by
  inference from enum ordering. [#77](https://github.com/sjmotew/NarwalIntegration/issues/77)
  suggests at least one model disagrees.

**`/info/get_clean_time_line` — probed (CX7).** It returns the **whole timeline of the last job
as a list**, the same entries with the same timestamps that `status/time_line_status` pushes one
by one over the cloud, including the closing entry with the end reason (`1.2 = 6`, `1.5 = 1`
for a normal end; see the fault paragraph above for `7`)
([Discussion #164](https://github.com/sjmotew/NarwalIntegration/discussions/164), second
capture). On a model that does not broadcast, polling it once after a job is a local way to
get the end reason.

More from the same unit (2026-11-17; [captures §2.3, §2.4, §8](CAPTURES-CX7-2026-11.md)):

- **The timeline marks each room and each drawn zone with a start and an end entry**:
  `3: {1: 1, 2: {1: <zone type>, 2: <id>, 3: 1, 4: 2}}` when the robot begins it and
  `3: {1: 2, 2: {…, 3: 2, …}}` when it is done, zone type 1 with the room id or zone type 2 with
  the zone's id. In a two-room job: Hallway 15:10:34 to 15:12:42, Toilet 15:12:42 to 15:13:50. Seen
  over the cloud push and, entry for entry, in the local answer. Polling it during a job tells
  which room is being cleaned and which are done, without `working_status`.
- The answer grows during the job: 4 bytes before the start (`08 01 12 00`), then 42, 94, 263, 303,
  365, 415 and 437 bytes with 12 entries at the end. The list is not cleared when the job ends: it
  went on growing through the dock actions and the cruise that followed (455, 475, 515, 535, 721
  bytes) and started again at 44 bytes at 16:10:11, with the next cleaning job.
- A fault that was resumed stays in the list (status 23 with the block, 28, 13), although the
  closing entry says 1.
- All values met are tabled in [§7](#statustime_line_status-on-one-cx7).

**Unexplored topics — mostly answered for one CX7.** This entry used to list
`/schedule/clean_schedule/get`, `/config/get` and `/config/volume/set` as never probed locally. For
that CX7 (v01.13.11.02; @pdb0102, 2026-11):

- `/config/get` **answers locally**, as §9 already records, and is mapped in
  [SETTINGS.md](SETTINGS.md).
- `/schedule/clean_schedule/get` gave **no answer locally** (2026-11-17, one try; `schedule/get`
  likewise), in line with the
  "Silent on CX7" list in §9. The app never sent it either: it keeps schedules on Narwal's server
  ([CLOUD-API.md](CLOUD-API.md)), and saving one put nothing on the cloud MQTT path.
- `/config/volume/set` was **never seen from the app**. The app's volume slider sent
  `config/set` with `{1: n}` (`08 59` = 89, `08 64` = 100; 14 such messages on 2026-11-13 and 2 on
  2026-11-14, mirrored in `config/get` field 2.1). The topic was not sent by us, so whether the
  robot would accept it is
  still open.

`/consumable/get_consumable_info` **has** now been probed — see §7.

---

## 12. Contributing captures

The highest-value contribution is a capture of what the **official app** sends, because it
settles arguments that reasoning cannot. The method needs no packet capture and was worked out
by [@ken99999](https://github.com/ken99999):

1. **Disable the Home Assistant config entry.** The robot allows one connection per IP and will
   close yours otherwise.
2. Set the option you're testing **in the Narwal app** and start a clean from the app.
3. Call `clean/current_clean_task/get` from a local script and record the raw response.
4. Change exactly one setting, repeat, and diff.

Post **raw hex**, not your decoding. Field names in this protocol have been misread more than
once, including in this document's history — the bytes survive a bad interpretation, a summary
doesn't.

Also valuable:

- **`nmap -p 9002 <robot_ip>`** on any model not in the README's compatibility table
- **A robot fault captured live** — pick the robot up mid-clean and record `robot_base_status`
  (done on a CX7, §11: the block lasted 10 s, 2 s and 3 to 4 s in four sightings and a 5 s poll
  caught one of two, so take it from the timeline; other models and other faults are still wanted)
- **A complete enum decode** from the APK, rather than individual values

Corrections to this document are welcome as issues or PRs. If something here contradicts what
your hardware does, your hardware is right.
