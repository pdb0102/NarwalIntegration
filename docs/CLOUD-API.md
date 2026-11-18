# What the official app does over the web (CX7)

This integration is local-first, and this document does not change that. It records which
of the app's features never touch the robot's local socket or the MQTT topics at all,
because they are calls from the phone to Narwal's web services. Its use is to answer "can
this be done locally?" with evidence, and to give names to things the numbered protobuf
fields leave unnamed. It is not an invitation to build on these calls: they need the
account's login, they are undocumented, and they can change without notice.

> **Scope: one unit, one account.** Everything below was observed on ONE robot: Freo Z
> Ultra (CX7), product key `hEA7OEshlx`, firmware `v01.13.11.02`, one account in the US
> region, iOS app 2.10.90, on 2026-11-16 and 2026-11-17 (the robot's own traffic on
> 2026-11-13 and 2026-11-14). Three vantage points were recorded at once: the phone's web
> traffic through an intercepting proxy (the phone trusted the proxy's root; the app does not
> pin certificates), a read-only listener on Narwal's cloud MQTT broker, and a poller on the
> robot's local WebSocket. Nothing was tested on another model, firmware, region or the
> Android app. Besides the app, a second client of the same account was on the broker
> throughout; it makes no web calls through the phone, so the web calls here are the app's,
> but broker reads timed near a web call may be that client's. It is evidence, not a specification. (CX7 v01.13.11.02; @pdb0102, 2026-11)

How sure each line is: **P** = confirmed by an app action (one thing done in the app, this
call captured), **L** = likely (matched by value, name or timing), **G** = a guess.

**Every identifying value is replaced**: `<device_id>` (32 hex characters), `<user_uuid>`,
`<user_id>`, `<uuid>` (schedule and shortcut keys), `<record_id>`, `<token>`, `<email>`.
`hEA7OEshlx` is the model's product key and is public. Times are local (UTC−7).

Related documents: [PROTOCOL.md](PROTOCOL.md) (the local protocol),
[SETTINGS.md](SETTINGS.md) (robot settings), [MAP-FORMAT.md](MAP-FORMAT.md) (the map).

---

## 1. Hosts

The host names seen here begin `us-`; other regions presumably use other prefixes (not seen).

Read from the phone (all TLS):

| Host | Used for |
|---|---|
| `us-app.narwaltech.com` | most calls below: device shadow, policies, sharing, shortcuts, schedules, video setup, statistics, picture keys |
| `us-app-sweeper.narwaltech.com` | location, city list, consumables, task records, cleaning report, stored per-device settings data (§12) |
| `us-op.narwaltech.com` | one call seen, a per-part lookup that answered 404 (§8) |
| `us-appbury.narwaltech.com`, `us-idass.narwaltech.com` | contacted by the app; calls not catalogued here |
| `us-01.mqtt.narwaltech.com:8883` | the app's own broker connection (the topics of [PROTOCOL.md](PROTOCOL.md) §3) |
| `public.itls…aliyuncs.com:1883`, `api-iot…`, `living-account…` (Alibaba IoT) | contacted by the app; purpose not established |
| names under `rtnsvc.com` (`ap-america-tls`, `ap-tds-na`, `report-america`, …; nine in all) | Agora, during live video (§11) |
| S3 buckets `narwal-device-media-resized`, `narwal-general-public` | pictures (§11) |
| `narwalroboticsus.zendesk.com` | "Help Center" pages |

The app resolves its hosts through Alibaba's HTTPS name service, not ordinary DNS (L: from
the phone's capture of 2026-11-16, as recorded in the capture log; not re-examined).

Looked up or contacted by the robot itself (seen at the gateway and DNS, 2026-11-13/14):
`us-01.mqtt`, `us-02.mqtt`, `us-mqtt` (the broker), `us.device.narwaltech.com`,
`us-open-data.narwaltech.com`, `us-open.narwaltech.com`, `us-sweeper.narwaltech.com`,
`narwal-general-public-cdn.narwal.com` (voice packs),
`narwal-robot-logs-10.oss-us-west-1.aliyuncs.com` (log upload), several NTP servers, and
one fixed UDP destination on port 9700. None of these connections is described here (§13).

**Common shape.** Requests carry the login in headers (`Auth-Token`, `UUID`, `did`,
`Aiot-Application-Id`; values never reproduced here). Almost every call names the robot by
product key and device id, spelled `product_id` / `device_id` on some services and
`productId` / `deviceId` on others; the spelling is given per call because it is not
uniform. Answers are JSON, usually
`{"code": 0, "msg": …, "err_code": …, "result": …, "success": true}`; a few use `"data"`
instead of `"result"`.

---

## 2. Device info and firmware

- **The app's device query.** After "Restart Robot" (2026-11-17 14:49:34, `common/reboot`
  over the broker) the app asked Narwal's device service for the device once, at 14:50:09,
  30 s after the command and while the robot was still off the air:
  `GET us-app.narwaltech.com/iot-platform/device-server/v1/device/getDeviceByParams?productId=hEA7OEshlx&deviceId=<device_id>`
  (seen once; seen in the phone's capture, 2026-11-17; the answer was not read). It is listed so that
  nobody assumes the restart itself is a web call. It is not: [SETTINGS.md](SETTINGS.md) §2.6.
- **Firmware versions the app shows** come from the robot, not the web: on opening Settings
  the app sent `common/upgrade/get_firmware_version` over the broker (the topic
  [PROTOCOL.md](PROTOCOL.md) §9 already lists as answered locally).
- **A firmware update check and the voice-pack download are the robot's own business**, not
  the app's: no web call of the app was seen for either. After
  `config/language/set_custom_voice` over the broker ([SETTINGS.md](SETTINGS.md) §2.6) only
  the three short values travel; the robot fetches the pack itself (about 17 MB, seen at the
  gateway as a download by the robot, 2026-11-13). The robot's own connections are outside
  this document (§13).

---

## 3. Device location

App: Settings › Device › "Device Location" (a searchable city list with UTC offsets).
2026-11-17 14:41 to 14:42. P: two choices made, one call each.

| Time | Call |
|---|---|
| 14:41:27 | `GET us-app-sweeper.narwaltech.com/device-extend-info-server/v1/app/device/location/query?product_id=hEA7OEshlx&device_id=<device_id>&timezone=America/Denver` (opening the row) |
| 14:41:49 | `GET us-app-sweeper.narwaltech.com/time-zone-server/v1/app/cities/timezone/list?timezone=America/Denver` (the city list) |
| 14:42:07 | `POST us-app-sweeper.narwaltech.com/device-extend-info-server/v1/app/device/location/set` (first choice) |
| 14:42:25 | the same (second choice, back to the original city) |

```json
{"product_id": "hEA7OEshlx", "device_id": "<device_id>",
 "country_code": "ar", "city_code": "Salta", "location_id": 1000470,
 "country": "Argentina", "city": "Salta", "is_capital": 1,
 "offset": "UTC -03:00", "timezone": "America/Argentina/Salta"}
```

The second call was the same shape with `"country_code": "us"`, `"country": "United States"`,
`"offset": "UTC -07:00"`, `"timezone": "America/Denver"` and the home city.

**On the broker at the same moment: nothing.** The listener heard no `config/set` and no
other command between 14:41:27 and 14:43.

**The robot's own copy changed all the same.** `config/get` field 2.3 holds a location
([SETTINGS.md](SETTINGS.md) §3):

| Read | 2.3 |
|---|---|
| 14:41:27, before | `{1: "America/Denver", 2: "UTC -06:00", 3: "USA", 4: "<city>"}` |
| 14:44:39, after | `{1: "America/Denver", 2: "UTC -07:00", 3: "United States", 4: "<city>"}` |

The offset and the country's spelling are now those of the app's web call of 14:42:25. No
message on any topic the listener subscribes to carried the change. P for the fact; how the
server reached the robot is not seen. One trace (L): in the device shadow read at 14:51
(§4), 41 of the 45 `reported` entries carried the same time stamp, 14:42:26, one second
after the second `location/set`, as if the robot had re-reported its state then. The other
four (`upload_configuration`, the two schedule lists, `bound_user_info`) carried 14:50:31,
just after the restart of 14:49.

A client that talks only to the robot cannot set the location the app's way.

---

## 4. Device shadow

A server-side copy of the robot's settings with a `desired` side (what a client asked for)
and a `reported` side (what the robot says it has), 45 keys each on this unit, plus a time
stamp per key. The key list, with the pairing to `config/set` fields, is in
[SETTINGS.md](SETTINGS.md) §4.

### Read

App: opening Settings › Device › "Privacy Settings" (2026-11-17 14:51:48). L: seen on
opening the page (read once).

```
GET us-app.narwaltech.com/iot-platform/device-shadow-server/v1/get?deviceId=<device_id>&productId=hEA7OEshlx

{"code": 0, "msg": "ok", "err_code": 10000,
 "result": {
   "state":    {"desired": {<45 keys>}, "reported": {<45 keys>}},
   "metadata": {"desired": {"<key>": {"timestamp": <ms>}, …}, "reported": {"<key>": {"timestamp": <ms>}, …}},
   "timestamp": <ms>}}
```

Among the keys: `scheduled_cleaning_tasks` and `scheduled_video_cruise_tasks` (§9),
`upload_configuration` (below), `region` (§3) and `bound_user_info {uuid}` (the account).

### Write: `desired`

App: Privacy Settings › "Device Log Upload" (a switch: "When enabled, it can help
troubleshoot device issues"). Switched off at 14:53:31 and on again at 14:53:36. P.

```
POST us-app.narwaltech.com/iot-platform/device-shadow-server/v1/desired

off: {"deviceId": "<device_id>", "productId": "hEA7OEshlx", "timestamp": <ms>, "messageId": "",
      "stateDesired": {"upload_configuration": {"tracingEvent": false, "log": false, "bag": false,
                                                "minidump": false, "coreDump": false, "data": false,
                                                "idc": false}}}
on:  the same with tracingEvent, log, bag, minidump, coreDump, data = true; "idc" stays false

→ {"code": 0, "data": {"timestamp": <ms>}}
```

- One switch, seven flags; six follow it. The request spells them in camel case
  (`tracingEvent`, `coreDump`); the shadow as read spells them `tracing_event`, `core_dump`.
- **`idc` is unexplained.** It was false before, during and after. The owner's guess: it
  belongs to the "User Experience Program" (§5), which is not joined on this account.
  Consistent, unproven: the shadow was not read during the 24 seconds the programme was
  joined.
- **On the broker at the same moment: nothing.**
- This is the one write to the shadow seen. That schedules reach the robot the same way is
  suggested by the key names only (§9).
- The `desired` side is not a mirror of the robot: settings the app changed with
  `config/set` over the broker were stale in `desired` and current in `reported`
  ([SETTINGS.md](SETTINGS.md) §4).

---

## 5. Policies

App: Settings › Device › "Privacy Settings", rows "User Experience Program" and "Live
Video & Real Photo Privacy Policy". 2026-11-17 14:51 to 14:56.

**Read** (L: on opening the page):

```
POST us-app.narwaltech.com/user-device-platform-server/policy/getPolicyStatus
{"policy_type_list": [{"policy_type": 8, "business_id": "<device_id>", …},
                      {"policy_type": 5, "business_id": "<device_id>", …}],
 "country_code": "us", "language_code": …, "user_uuid": "<user_uuid>"}
→ per policy: authorized_status, authorized_time
```

| `policy_type` | App row | `authorized_status` on this account |
|---|---|---|
| 8 | "Live Video & Real Photo Privacy Policy" | 1 = authorized |
| 5 | "User Experience Program" | 2 = not authorized |

Type 8 by elimination and by the app's row reading "Authorized" (L); type 5 confirmed by
the write below (P).

**Write** (P: joined at 14:55:44, withdrew at 14:56:08, one call each):

```
POST us-app.narwaltech.com/privacy-policy-platform/user/policy/reportProductPolicyV2
{"policy_version": "0.1.6", "country": "us", "policy_type": 5,
 "device_id": "<device_id>", "product_id": "hEA7OEshlx", "authorized_status": 1}     join
 … "authorized_status": 2                                                             withdraw
→ {"success": true}
```

In those 24 seconds: no write to the device shadow by the app, no message over the broker,
no new host contacted by the phone. "Device Authorization" on the same page has no action.

---

## 6. Device sharing

App: Settings › Device › "Device sharing" › "Add family member" › "Send Invitation".
2026-11-17 14:45 to 14:47. P for the calls; no invitation succeeded.

| Step | Call |
|---|---|
| Opening the page | `GET us-app.narwaltech.com/user-sweeper-app-server/v2/device-share/getInviteUsers?product_id=hEA7OEshlx&device_id=<device_id>` → `"result": []` |
| The nickname is checked first | `POST us-app.narwaltech.com/base-api-security-server/v1/textContentDetection {"text": "<nickname>"}` → `{"code": 0, "msg": "succeed!", "result": true, "success": true}` |
| The invitation | `POST us-app.narwaltech.com/user-sweeper-app-server/v2/device-share/invite {"share_user_email": "<email>", "product_id": "hEA7OEshlx", "device_id": "<device_id>", "share_user_mobile": null, "area_code": null, "nickname": "<nickname>"}` |

- **Only another Narwal account can be invited.** An address with no account answered, twice:
  `{"code": -1, "err_code": 101702700, "success": false}`, which the app shows as "No user.
  Try again."
- The same text check runs when a room is given a typed name in the map editor
  ([MAP-FORMAT.md](MAP-FORMAT.md)).
- **On the broker: nothing.**

---

## 7. Siri shortcuts ("Third-party Control")

App: Settings › "Third-party Control" shows three tiles: "Amazon Alexa", "Google Home",
"Siri". Only Siri was opened. 2026-11-17 14:57 to 15:01.

```
GET  us-app.narwaltech.com/app-settings-app-server/v1/getSweeperExtend
       ?device_id=<device_id>&product_id=hEA7OEshlx&extend_type=shortcut&app_device_id=<phone id>
POST us-app.narwaltech.com/app-settings-app-server/v1/setSweeperExtend
       {"device_id": "<device_id>", "product_id": "hEA7OEshlx", "extend_type": "shortcut",
        "extend_data": {"robot_shortcuts": [ … the whole list … ]}}      → {"success": true}
```

- The `GET` goes out on opening "Third-party Control" (L). The `POST` goes out on opening
  the "Siri" tile with nothing changed, and again after every add or delete: **the whole
  list is saved each time** (P).
- One shortcut, as added through Apple's "Add to Siri" sheet at 14:59:52:

  ```json
  {"shortcut_content": "Twiddle thumbs",
   "robot_shortcut": "Paused Manually",
   "shortcut_type": "task_pause",
   "shortcut_identifier": "<uuid>",
   "shortcut_icon": …, "shortcut_prefix": …,
   "shortcut_param": {"sweep_mode": "", "sweep_fan_level": "", "mop_strength_level": "",
                      "mop_humidity_level": "", "clean_zone_type": "", "clean_count": ""}}
  ```

  `shortcut_content` is the phrase the owner chose, `robot_shortcut` the app's label for the
  action, `shortcut_prefix` the "Please say, Hey Siri, …" hint, `shortcut_identifier` the
  phone's own id for the shortcut. A cleaning shortcut fills `shortcut_param`
  (`clean_zone_type: "whole_house"`, a `clean_count`); `shortcut_type` values seen:
  `sweep_of_mop`, `mop`, `task_pause`.
- The app's list of actions on offer ("All commands"): Freo Mind Mode Vac & Mop, Vac then
  Mop, Vacuuming, Mopping, Drying and disinfection, Paused Manually, Resume cleaning, Cancel.
- **A shortcut stores words, not a robot command.** The reading (L): Siri wakes the app,
  and the app sends the ordinary broker command. What the phone sends when a shortcut runs
  was **not seen**; the test shortcut was deleted before a run.
- **An app bug, as observed (seen once):** after the test shortcut was deleted at Apple's,
  the app's list still showed it, and its saves of 15:00:47 and 15:01:35 still carried the
  entry; its edit pencil opened and closed an empty sheet. The phrase was gone from Siri,
  the entry stayed on Narwal's server. Harmless.
- No Matter or HomeKit tile exists on this unit.
- **On the broker: nothing.**

---

## 8. Consumables

App: Settings › "Accessory Management" ("Parts and Consumables"). The page was opened and
one reset pressed on 2026-11-16 22:02: the broker rows and the description of the list's
answer rest on that evening. The request bodies and the `us-op` call rest on the phone's
capture of 2026-11-17. This
bears on the open question in [PROTOCOL.md](PROTOCOL.md) §7 and §11, "are per-consumable
life percentages truly cloud-only?": on this unit the app took them from the web.

| What | Where it came from | |
|---|---|---|
| The list of parts with hours or days left | `POST us-app-sweeper.narwaltech.com/consumables-management-app-server/v3/consumables/list` with body `{product_id, device_id, language: "en", is_up_down_water: 0, is_dust_box: false, is_dust_bag: false}` | L: called on opening the page. The robot's own `consumable/get_consumable_info` answers that evening were all empty (`0a 00`), before and after the reset, while the page showed hours for every part and 0 h for one |
| One part's page | `POST us-app-sweeper.narwaltech.com/consumables-management-app-server/v1/consumables/detail` with body `{product_id, device_id, type: <n>, language, consumables_code: "<code>", is_dust_box, is_dust_bag}` | L: called on opening a part; `type` 115, 22, 23 and 20 were seen. The answer was not read |
| A shop link for the part (by the path; G) | `GET us-op.narwaltech.com/api/app-web/operate/consumablesProduct/getByPidAndType?pid=hEA7OEshlx&type=<n>` | answered 404 for each type on this unit |
| "Replaced (timer reset)" | broker: `consumable/reset_consumable_info`, body `0a 03 12 01 18` = `{1: {2: [24]}}`, answered `{1: 1}` | P, seen once |
| After the reset | broker: `consumable/get_consumable_info` → empty (`0a 00`) | P |

The request bodies and the third call are as seen in the phone's capture, 2026-11-17. The
answers of `list` and `detail` were not read beyond the following, which is from
2026-11-16.

`consumables/list` answers a list with, per part: a name, a `type` number,
`total_duration`, `usage_duration`, texts and icons, and flags for showing a bar and a
reset button. **The `type` numbers are not the robot's item numbers**: 22, 23, 106, 107,
115, 117 and others were seen, against 1 to 24 in the broker command
([PROTOCOL.md](PROTOCOL.md) §7). The mapping between the two was not worked out.

So on this unit: the reset is a robot-topic command (seen over the cloud broker; not tried
locally). It carried item 24, "inner dust box" in [PROTOCOL.md](PROTOCOL.md)'s list, shown by
the app as "Replaceable insert bin": the list holds here. The remaining life is served by Narwal. No local topic was seen
to carry it. The app offered a reset only for replaceable parts, never for parts that are
cleaned, so a "maintain item" reset (field 1 of the same body, by the layout) was not seen.

---

## 9. Schedules

App: the "Schedule" tab ("Scheduled Plan": all, clean, cruise). 2026-11-17 15:52 to 15:59.
**No broker message at any point while schedules were added, changed, switched or
deleted** (15:52 to 15:56). `schedule/clean_schedule/get` is silent on this unit
([PROTOCOL.md](PROTOCOL.md) §9 "Silent on CX7"); this is where schedules live instead.

| Action | Call | |
|---|---|---|
| Open the tab; after every change | `GET us-app.narwaltech.com/sweeper-schedule-app-server/v2/schedule/getScheduleTaskList?…&timezone=UTC-7` → `{scheduled_cleaning_tasks, scheduled_video_cruise_tasks, task_status_info}` | P |
| "Add" | `POST us-app.narwaltech.com/device-task/scheduled-task/sweeper/additional` | P |
| Change the time | the same call, the whole schedule again under the same key | P |
| Switch on / off | the same call with `"enable": true / false` | P |
| Delete | `POST us-app.narwaltech.com/device-task/scheduled-task/sweeper/deleteEntry {"device_id": "<device_id>", "product_id": "hEA7OEshlx", "scheduled_cleaning_tasks_key": "<uuid>"}` → `{"code": 0}` | P |

A schedule is one stored object under a uuid the app makes. Add, change and enable replace
it whole; delete names the key.

### A cleaning schedule

Added 15:54:09: 18:00 the same day, one room, the app's "Vacuum and mop" with Freo Mind.

```json
{"deviceId": "<device_id>", "productId": "hEA7OEshlx",
 "scheduled_cleaning_tasks": {"<uuid>": {
   "task": {"mapId": 1,
            "items": [{"zone": {"zoneType": "ZONE_TYPE_ROOM", "zoneId": 5},
                       "param": {"mode": "CLEAN_MODE_SWEEP_MOP_SYNC",
                                 "fanLevel": "FAN_LEVEL_NORMAL",
                                 "mopStrengthLevel": "MOP_STRENGTH_LEVEL_NORMAL",
                                 "mopHumidity": "MOP_HUMIDITY_NORMAL",
                                 "sweepTime": 1, "mopTime": 1, "sweepMopSyncTime": 1,
                                 "overlapLevel": "OVERLAP_LEVEL_NORMAL",
                                 "enableSmartMode": true},
                       "order": 1}],
            "option": {"enableSmartMode": false},
            "extra": "<JSON as text: the cron line again, taskName \"New tasks\", created_at, updated_at>",
            "taskType": "TASK_TYPE_SCHEDULED"},
   "cron": "0 0 18 17 11 ? 2026", "enable": true,
   "triggerType": "SCHEDULE_TRIGGER_TYPE_CRON"}}}

→ {"code": 0, "result": {}}
```

- **The task is the `CleanTask` of `clean/start_clean` in protobuf's JSON form, with enum
  values by name.** That yields Narwal's names for the enums of [PROTOCOL.md](PROTOCOL.md)
  §6: `ZoneType` (`ZONE_TYPE_ROOM` = 1), `CleanMode` (`CLEAN_MODE_SWEEP_MOP_SYNC` = the
  app's "Vacuum and mop"; mode 4 in a start, L), `FanLevel`, `MopStrengthLevel`,
  `MopHumidity`, `OverlapLevel` (each `…_NORMAL` here), `TaskType`
  (`TASK_TYPE_SCHEDULED`), and the trigger `SCHEDULE_TRIGGER_TYPE_CRON`. Only the values
  in this one schedule were seen; the other enum members were not.
- **The cron line** is Quartz-style with a year: second, minute, hour, day, month, weekday,
  year, in the zone given by `timezone`. A repeating schedule's line was not captured.
- `zoneId` is a room id of that day's map. Room ids are per map and changed on this robot
  when rooms were merged and split ([MAP-FORMAT.md](MAP-FORMAT.md)).

### A cruise schedule

Added 15:57:15: three points placed in one room, 17:00 the same day. The same call with the
other list:

```json
{"deviceId": "<device_id>", "productId": "hEA7OEshlx",
 "scheduled_video_cruise_tasks": {"<uuid>": {
   "task": {"mapId": 1,
            "videoCruisePoints": [{"x": -37.58, "y": -120.46},
                                  {"x": -38.56, "y": -148.20},
                                  {"x": -36.88, "y": -164.59}],
            "extra": "<JSON as text: the three points again, in protobuf's text form>"},
   "cron": "0 0 17 17 11 ? 2026", "enable": true,
   "triggerType": "SCHEDULE_TRIGGER_TYPE_CRON"}}}

→ {"code": 0}
```

A cruise is a map id and a list of points in the map's own cell coordinates, fractions of a
cell (rounded here), with no cleaning parameters. P.

### What happened when one fired

The cruise schedule was moved to one minute ahead and ran at 15:59 (seen once).

- **No start command reached the robot over the broker.** No `clean/start_clean`, nothing
  cruise-related from any client. The robot appears to hold the schedule and start by its own
  clock. P only for the absence of a start command on the topics the listener subscribes to.
- The server sent the phone a push notification ("The scheduled task you have reserved
  starts").
- **A one-time schedule shows switched off after it has fired.**
- What the robot then reported over the broker and the local socket (main state 24, the
  planned route on `status/point_navi_plan_traj`) belongs to [PROTOCOL.md](PROTOCOL.md).
- How the robot received the schedule is not seen. The two list names are also keys of the
  device shadow (§4), which is the likely road (L).

---

## 10. Task records, cleaning reports, statistics

All web only: nothing was asked of the robot when these screens were opened.

### The list: "Task record"

Reached from the main screen; tabs "All", "Clean", "Maintenance", "Cruise". 2026-11-17
15:19.

```
GET us-app-sweeper.narwaltech.com/sweeper-map-scheme-app-server/v2/work_record/all
      ?page=1&type=<n>&status=0&deviceId=<device_id>&productId=hEA7OEshlx
```

| `type` | Tab | |
|---|---|---|
| 1 | "All" | P |
| 2 | "Clean" | P |
| 4 | "Maintenance" | P; empty on this account: washes, dryings and dust emptying left no record |
| 5 | "Cruise" | P; empty at that time |

Type 3 was not sent by any tab. Fifteen records came back on page 1. Each record's fields:

| Group | Fields |
|---|---|
| Identity | `id`, `record_id`, `report_id`, `device_id`, `product_id`, `user_id`, `user_uuid`, `custom_name`, `item_icon` |
| Time and size | `start_time`, `end_time`, `duration` (seconds), `area` (m²; the app converts), `created_time`, `last_modified_time` |
| Outcome | `error_code`, `record_status`, `is_continued_task` |
| Kind | `record_type`, `task_type`, `region_type` (1 rooms, 2 a drawn zone; L), `init_clean_param {enable_smart_clean, enable_smart_deep_clean}` |
| Map | `map_id`, `map_generate_time`, `is_temp_map`, `room_infos[] {room_id, type, room_type_id, custom_name, texture, texture_direction_angle, is_default_heavy_dirty_room, is_customize_heavy_dirty_room}` |
| The job | `clean_order` (room ids in the order run), `clean_params[] {zone_id, mode, sweep_mode, sweep_times, mop_mode, mop_times}`, `clean_task` (below) |
| `extend_data` | the job fields again, plus `schedule_task_result`, `use_new_detail`, `work_record_source`, `work_record_type` |

- **`error_code` is the fault code of `robot_base_status` field 1.** Four jobs that died of
  a perception fault on 2026-11-13 carry 36765697 (`0x02310001`, the code in
  [PROTOCOL.md](PROTOCOL.md) §11); a job that was lifted mid-run and resumed carries 0.
  L, by value.
- `room_infos` holds the rooms **as they were at the time**, so the app labels old records
  with old room names after a merge.
- **`clean_task` is the start message as JSON with every field named**:

  ```
  clean_task {
    map_id, task_type,
    items [{ order,
             zone  {zone_type, zone_id, selection_bounds [], cleaning_bounds []},
             param {mode, fan_level, sweep_time, mop_time, mop_humidity, mop_strength_level,
                    overlap_level, sweep_mop_sync_time, enable_smart_mode} }],
    option {enable_smart_mode, enable_smart_deep_clean, enable_massive_dirty_clean,
            enable_maintain_after_clean, is_need_rebuild_map, build_new_map_before_clean,
            is_calibration},
    excluded_room_ids [], maintain_floor_items [], debug_option {enable_only_clean_door}, extra }
  ```

  Set against the protobuf of the same start, this names the `CleanTask` tags of
  [PROTOCOL.md](PROTOCOL.md) §6. The table of tag ↔ name, with which pairings are confirmed,
  is that document's subject and is not repeated here. Two cautions: the record is tidied by
  the server and is not a copy (a vacuum-only job read `mop_time: 0` and `mop_humidity: 0`
  where the app had sent 1 and 2); and `selection_bounds` / `cleaning_bounds` are filled
  only for a drawn zone (the rectangle as drawn, and its outline cell by cell; P, the same
  numbers as in the start message).

### The latest record, and a day's summary

| Call | When | Answer |
|---|---|---|
| `GET us-app.narwaltech.com/sweeper-map-scheme-app-server/v2/work_record/getLatestRecord` | opening a just-finished job's report (16:13:34) | one record, same fields as above. For the zone job: `region_type: 2`, `area: 0.8`, `duration: 101` |
| `GET us-app.narwaltech.com/clean-record-app-server/v1/deviceFile/getRecordSummer?device_id=<device_id>&product_id=hEA7OEshlx&zone=UTC-7&date=2026-11-17&map_id=1` | opening the record page and using its calendar (three times) | `"result": null` each time; what it holds when filled was not seen |

The calendar made no call that lists days with records.

### The report: `clean-record/detail`

```
GET us-app-sweeper.narwaltech.com/clean-record-app-server/v1/clean-record/detail
      ?clean_record_id=<record_id>&product_id=hEA7OEshlx&device_id=<device_id>
```

The report the app draws after a job: 39 kB, 88 fields in `result`, for a 101-second
drawn-zone job (2026-11-17 16:13, seen once). It is the map with the robot's track on it,
every part named. The **map-related names** (`resolution`, `width`, `height`, `border`,
`origin`, `station`, `map_data`, `map_data_format`, `map_version`, `map_generate_time`,
`map_valid_bit`, `map_center_align_data`, `rotate_angle`, `forbiddens`, `virtual_walls`,
`carpets`, `doors`, `thresholds`, `room_infos`, `sub_room_infos`, `vision_data`,
`pet_heat_areas`, `update_map_regions`, `carpet_change_events`, `carpet_updated`,
`add_carpet_clean_option`, `isLatestMap`, `is_temp_map`, `map_id`, `map_list_type`,
`show_station_direction`) are read against the numbered map fields in
[MAP-FORMAT.md](MAP-FORMAT.md). The job-related ones:

| Group | Fields |
|---|---|
| Identity | `id`, `record_id`, `report_id`, `mission_id`, `device_id`, `product_id`, `user_id`, `custom_name`, `version`, `created_time`, `clean_record_path`, `extension_string` |
| Time, size, result | `start_time`, `end_time`, `duration`, `area`, `percent` (100), `task_res` (1), `status`, `error_code` (0), `scenario_error_code`, `exception_info_list[]`, `type_for_pause_too_long_end`, `is_continued_task` |
| What was asked | `task_type`, `record_type`, `region_type`, `clean_trigger_type` (1), `schedule_task_id`, `schedule_task_result`, `clean_task` (as above), `init_clean_param`, `clean_order`, `clean_params[] {zone_id, sweep_times, mop_times, mode, mop_mode, sweep_mode}`, `zone_infos[] {mode, actual_zone, original_zone}` |
| What was done | `clean_times[] {zone_id, sweep_times, mop_times}`, `room_clean_events[] {room_clean_event_type, room_id, index, clean_times, second_clean_region, sub_room_id}`, `uncleaned_zones[]`, `robot_trapped_points[]`, `max_dirty_level` (5), `up_obstacle_detected`, `clean_with_mapping_result`, `clean_event_msgs[]` |
| The track | `robot_trajectory` (text, 584 characters here), `robot_trajectory_format` (2), `trajectory_infos[] {trajectory_type, index, group_id, clean_count, direction}`, `trajectory_arcs`, `trajectory_start_indices[]`, `origin_robot_trajectory`, `origin_trajectory`, `origin_trajectory_infos`, `enable_clean_trajectory_display` |
| Timeline and highlights | `time_line_status {robot_event_list}`, `event_extraction {lightspot, postposition_action}` |
| Pictures | `image_resources` (null here; in a job with detected objects it lists them, per [Discussion #163](https://github.com/sjmotew/NarwalIntegration/discussions/163); not seen filled by us) |
| Debug | `debug_data {application_task_data, planning_task_data}` (firmware versions and planner data), `debug_detail` |

Readings, all L (by content, one report):

- `room_clean_events` are the timeline's two marks per room or zone
  (`room_clean_event_type` 1 = start, 2 = end); `index` points into the track.
- `time_line_status.robot_event_list` is the job's timeline, the list that
  `info/get_clean_time_line` returns locally ([PROTOCOL.md](PROTOCOL.md) §11).
- `clean_trigger_type`, `task_res`, `record_type` (2 here), `max_dirty_level`: one value
  each, meaning not established.

What the local socket
offers of it (timeline, task, map) is in [PROTOCOL.md](PROTOCOL.md). The track and the
per-job area were not seen locally on this unit.

### Statistics: the "History" tab

2026-11-17 15:50. Opening the tab made five calls to
`us-app.narwaltech.com/clean-record-statistics-server/<v>/robot-journey/<name>`, all `GET`, each
with the device id and product key (paths as seen in the phone's capture, 2026-11-17):

| Call | Answer | On the screen | |
|---|---|---|---|
| `/clean-record-statistics-server/v1/robot-journey/getFinalData` | `{area: 7831.02, cleanTimes: 232, duration: 582224, firstDistributionDate}` | "84.3K ft²", "232 Time", "161.7 Hours", "Time with Narwal 573 Days" | P (m² and seconds; the app converts) |
| `/clean-record-statistics-server/v2/robot-journey/getAllData?…&timezone=UTC-7` | `{area: 623.84, cleanTimes: 29, duration: 52603, dataList: [{date, day, area, cleanTimes, duration, whaleTimes}, …]}` | the Week / Month / Year chart: "6.7K ft²", "14.6 Hours", "29" for the year | P. **One answer serves all three views**: switching to "Year" sent nothing. `dataList` held one entry per day with a job (8) |
| `/clean-record-statistics-server/v1/robot-journey/getWhaleData` | `{cornerDeepCleanTimes: 44, dirtyReDragTimes: 35, dirtyInspectionTimes: 162, temperatureAdjustmentTimes: 0}` | "Freo Mind data": 44 "Intensive Corner Cleaning", 35 "Repeated Mopping on Dirt Residue", 162 "Dirt detection" | P, by the three matching numbers |
| `/clean-record-statistics-server/v1/robot-journey/getMaintenanceData` | `{area: 0, count: 0, duration: 0}` | | not shown |
| `/clean-record-statistics-server/v1/robot-journey/getTourTaskData` | null | | not shown |

"Whale" may be Narwal's internal name for Freo Mind (G, from this one call's labels). The lifetime counters live on
Narwal's server; the robot was not seen to offer them over the broker or locally.

---

## 11. Live video and pictures

### Live video

App: the main screen's "Video" button, which asks for a PIN set earlier. 2026-11-17 15:33
to 15:37. Values were never written down; names and lengths only.

| Time | Call | |
|---|---|---|
| 15:33:44 | `GET us-app.narwaltech.com/iot-application-platform/app-product-media-server/v1/getDeviceInfo?deviceId=<device_id>&productId=hEA7OEshlx` → `{active, appId (32 characters), areaCode, enableFunction, enablePassword, isMaster, policy, watermarkSwitch, …}` | P: pressing "Video" |
| 15:33:50 | `POST …/app-product-media-server/v1/checkPassword {device_id, product_id, encrypted_password (24 characters)}` → `{pass: true, enable_function: true}` | P: entering the PIN |
| 15:33:51 | `POST …/app-product-media-server/v1/channel/start {deviceId, productId, appId, sessionID, isGroup: true, debugMode: false}` → `{channel (32 characters), token (207), tokenExpireTime, uid, salt (44), securityKey (64), isFirst: true}` | P |
| 15:34:48 | `POST …/app-product-media-server/v1/channel/function/add {deviceId, productId, type: 1, channel}` → `true` | P: microphone on (the robot played the owner's voice) |
| 15:34:57 | the same with `type: 0` | P: microphone off |

- **It is an Agora real-time channel** (L). The grounds: the answer's `appId`, `channel`,
  `token`, `uid` are Agora's vocabulary; the phone looked up nine names under Agora's
  `rtnsvc.com` in the same second; the app ships Agora's SDK. `salt` and `securityKey` look
  like Agora's built-in media encryption (G).
- **Media travels through Agora's servers, also when phone and robot are in the same
  house** (L): the picture arrived at the phone as UDP from an outside address, about
  10.5 MB in eight minutes, 0.55 MB back.
- **The PIN is sent to Narwal's server; no check by the robot was seen** (P for the web
  call, `checkPassword`).
- **On the broker: no start command.** The listener heard nothing that tells the robot to
  begin; it must be told on a topic outside the listener's list, or by another road. The
  robot broadcast `status/streaming_info` once a second while it streamed (198 reports from
  15:33:52 to 15:37:26, with one gap while the app was in the video settings and the album).
  Field 1 is a counter. The other fields took five shapes in the 423 messages of the day
  (video, manual driving and the cruise together): `{3: 1, 4: 1, 6: 2, 7: 2}` 350 times,
  `{7: 2}` 31, `{3: 1, 4: 1, 6: 2, 7: 1}` 24, `{3: 1, 6: 1, 7: 2}` 9 (the first seconds of
  the first viewing), `{3: 1, 4: 1, 5: 1, 6: 3, 7: 2}` 9. Their meanings were not worked out.
- **Coming back to the picture asks for a new channel each time** (`channel/start` again at
  15:35:18 and 15:35:51).
- **Closing the video sends nothing to Narwal**: no web call and no broker message after
  the close button. The phone leaves the channel and `status/streaming_info` stops.
- While a viewer is connected the robot says "The camera is in use" at intervals (heard by
  the owner).
- **Driving by hand from the video view** produced no drive command on any topic the
  listener has and no web call, only a busier channel in both directions. The commands most
  likely ride inside the Agora channel (G). What the robot's status showed meanwhile is in
  [PROTOCOL.md](PROTOCOL.md).
- "Video function settings" offers "Reset password", "Photo and video watermarks" and
  "Remote control speed". Only the slider was moved: nothing sent.

For a camera without Narwal's cloud this road is closed on this unit: it needs Narwal's
token and Agora. What remains locally is `developer/take_picture`
([PROTOCOL.md](PROTOCOL.md) §5).

### Pictures

| What | Call or address | |
|---|---|---|
| The album | `GET us-app.narwaltech.com/clean-record-app-server/v2/deviceFile/listMedia?product_id=hEA7OEshlx&device_id=<device_id>&type=…` | L: on opening the album from the video view. The answer was 102 bytes, i.e. an empty list on this account; its fields were not read (seen in the phone's capture, 2026-11-17) |
| Cruise thumbnails | an S3 bucket host beginning `narwal-device-media-resized`, path `album/hEA7OEshlx/<device_id>/cruise/image/<job stamp>-<point>-<n>.jpg`, time-limited signed query parameters, several per point (n = 0 to 3) | P: fetched by the app while a cruise ran (2026-11-17 15:59 to 16:04) |
| A cruise's full picture | a host beginning `narwal-general-public`, path `device/video/hEA7OEshlx/<device_id>/<stamp>_…_5_1.jpg.nenc` | P, same cruise |
| A detected object's picture | the same bucket, `device/video/hEA7OEshlx/<device_id>/<number>.nenc`; the address is handed out by the robot in its `map/get_vision_image` answer over the broker | P (2026-11-13) |
| The key for `.nenc` files | `POST us-app.narwaltech.com/iot-platform/iot-device-key-manage-server/v2/device/secret/key/get {productId, deviceId, keyName: 1, publicKey}` → `{keyName, aesSecretCiphertext, ivCiphertext, secretKeyCiphertext}` (names only) | P: the app calls it; it was also sent once by a client of ours (2026-11-16) |

- A `.nenc` file is encrypted: a 256-byte wrapped key, then the JPEG in AES-CBC. The layout
  and the key call were published by another owner in
  [Discussion #163](https://github.com/sjmotew/NarwalIntegration/discussions/163) and
  **hold on this unit**: one key fetch, then a 2026-11-13 sample (66,000 bytes = 256 +
  16 × 4,109) decrypted locally to a 480 × 480 JPEG, and so did six more. Each file carried
  its own key (seven files, seven keys). This is the key
  [#157](https://github.com/sjmotew/NarwalIntegration/issues/157) refers to.
- On this unit `map/get_vision_image` over the **broker** answered with an address
  (`{3: address, 4: box, 5: size, 7: point}` for body `{1: 1, 2: <object number>}`).
  [PROTOCOL.md](PROTOCOL.md) §9 records `NOT_APPLICABLE` for `get_vision_image` locally; the
  two observations are on different channels and were not compared in one test.
- **So pictures leave the house**: cruise pictures and detected-object pictures are
  uploaded by the robot and fetched by the app from storage. The upload itself was not seen
  (§13).

---

## 12. Map-side web calls

The map itself, and every edit to it, travels over the broker
([MAP-FORMAT.md](MAP-FORMAT.md)). These reads were seen beside it (paths and answer shapes as seen in the phone's capture, 2026-11-17):

| Call | When | |
|---|---|---|
| `POST us-app.narwaltech.com/business-sweeper-app-platform-server/general-feature/v1/getDynamicResource` | opening the Map panel, and at app start | request about 2.7 kB, answer about 25 kB; contents not read |
| `GET us-app.narwaltech.com/sweeper-map-scheme-app-server/v1/getRoomCleanInfoOfMap?device_id&product_id&map_generate_time` | trigger not recorded | `result: [{id, map_id, map_generate_time, room_clean_time_array: [{room_id, last_sweep_time, last_mop_time, last_maintain_time}]}]`: one entry per room (7), a last-vacuumed, last-mopped and last-maintained time each. All three were null for every room in the answer seen, so the units and whether it is ever filled are unknown |
| `GET us-app-sweeper.narwaltech.com/device-setting/v2/getData?product_id&device_id&setting_data_type=room_custom_cleanparams&map_id=1&map_generate_time=…` | switching the map view to "3D space" (2026-11-17 15:44:22) | `result` null on this account. By its name, per-room cleaning parameters kept on the server (G) |
| `GET us-app.narwaltech.com/device-map/map/sweeper/vision-data/get?device_id&product_id&map_id` | the same moment; 894 bytes | `result {map_id, map_generate_time, image_resources, vision_data {vision_dirty[], vision_obs[], funitures[]}}`: the 3D view's obstacles and furniture (the spelling "funitures" is Narwal's). Field detail belongs to [MAP-FORMAT.md](MAP-FORMAT.md) |
| `POST us-app.narwaltech.com/base-api-security-server/v1/textContentDetection {"text": …}` | typing a room name of one's own | the text check of §6; presets cause no call |

None of them wrote anything, and none had a broker message beside it.

---

## 13. Not seen from here

What stays out of reach of a local client, and of this method: the robot's own connections
to Narwal were not read and are outside this document (the host names are in §1). So it is
not seen how the robot receives what the app sets over the web, namely the device location
(§3), "Device Log Upload" (§4) and schedules (§9); the device shadow is the likely road, and
nothing appeared on the broker topics the listener subscribes to (its topic list may not be
complete). Likewise not seen: what the robot uploads (logs, the reports behind the task
records and statistics of §10, the pictures of §11), what tells it to start streaming video,
and the drive commands of the video view (§11).
