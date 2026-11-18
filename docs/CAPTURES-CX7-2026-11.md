# CX7 capture evidence, November 2026

Raw bytes behind the statements tagged "(CX7, `hEA7OEshlx`, v01.13.11.02; one unit)" in
[`PROTOCOL.md`](PROTOCOL.md). Contributed by @pdb0102.

> **Scope: one robot.** Everything here was recorded on **one** Narwal Freo Z Ultra (hardware CX7,
> product key `hEA7OEshlx`, firmware `v01.13.11.02`), with **one** account in the US region, driven
> from the official iOS app (2.10.90), between 2026-11-13 and 2026-11-17. Nothing was tested on any
> other model or firmware. It is evidence, not a specification: other units may differ.

## How these were captured

Three recorders ran side by side while one person pressed one thing at a time in the app and said
what and when:

- **Cloud MQTT, listening only.** A second client on Narwal's broker, subscribed by name to 216
  topic names taken from the app's strings (with this account's session the broker accepts
  wildcards but delivers nothing for them). It hears the app's commands, the robot's answers and
  the robot's broadcasts. Lines below
  without a source mark come from this recording.
- **Local WebSocket, port 9002.** A poller that sent `status/get_device_base_status` every 5 s and
  `info/get_clean_time_line` and `clean/current_clean_task/get` every 15 s, one request per
  connection, reads only. Marked `local` below. A local answer is `{1: 1, 2: <payload>}`.
- **The phone's web traffic** through an intercepting proxy, for the app's calls to Narwal's web
  services. Those are in [`CLOUD-API.md`](CLOUD-API.md), not here.

**A second client was on the broker.** Besides the official app, a second client of the same
account was connected. It sends `common/active_robot_publish` every 50 s and makes reads of its
own. The broker's envelope does not name the sender, so a read attributed to "the app" below
may in places be that client's. Every command and every settings change in these documents was
timed against a named action by the owner in the app. The two keep-alive bodies, as recorded on
2026-11-17:

```
0a0908d00f10d00f18d00f10e0d403
  = {1: {1: 2000, 2: 2000, 3: 2000}, 2: 60000}
  ×401, 10:39:40 to 16:15:31: the second client (every 50 s)
0a0b08d00f10d00f18d00f400010e0d4031800
  = {1: {1: 2000, 2: 2000, 3: 2000, 8: 0}, 2: 60000, 3: 0}
  ×186, 14:38:01 to 16:14:38: the app (every 30 to 31 s while it is open)
```

The second client's form appears in the 2026-11-17 recording only; the recording of the afternoon
of 2026-11-13 holds the app's form alone (177 times).

What the bytes are:

- **The cloud envelope is cut off.** A cloud payload is `0x01`, a varint length, a small frame
  (sender ids, response topic, request id), then the command's own protobuf. Only that last part is
  shown; it is the same protobuf the local WebSocket carries after its topic header.
- **Ids are zeroed.** Any 32-character hex text inside a payload is replaced by ASCII `0` of the
  same length, so the bytes still parse. In practice that is `robot_base_status` field 13 (the bound
  account), which reads `30 30 30 …` below. Topics are shown without product key and device id.
- **Decoding is schema-free**: `{field: value}` by field number. A packed list of small integers
  shows as its bytes (`'0102'` = `[1, 2]`). A float32 prints as a float. Negative coordinates
  travel as 64-bit two's complement (`18446744073709551603` = −13).
- **Times** are local, UTC−7. The cloud recording has whole seconds; cloud and local clocks are
  the recording machines' and agree to about a second.
- **Room ids** are those of the robot's map on 2026-11-17: 1 Master bedroom, 2 Bathroom, 3 Closet,
  4 Hallway, 5 Toilet (the dock stands here), 6 Living Room, 7 Kitchen. Captures of 2026-11-13 use
  an older numbering (rooms were merged and split on 2026-11-16, which renumbers them; see
  [`MAP-FORMAT.md`](MAP-FORMAT.md)).
- **The 2026-11-17 broker recording** runs from 10:39:34 to 15:39:35 and from 15:41:20 to
  16:15:42. The gap of 1 min 45 s is where the listener reached its time limit and was started
  again; the local poll kept running through it. The owner's actions in the app that day begin at
  14:38.

Confidence words used in `PROTOCOL.md`: *confirmed by an app action* (one press, one message, or
one setting changed and one number moved), *matched by value* (fits by value, order or timing;
nobody isolated it), *a guess*.

## 1. A two-room start in a chosen order (2026-11-17 15:10)

In the app: "Vacuum" ×1, Hallway chosen first and Toilet second in "Adjust cleaning sequence".
Choosing and dragging the rooms on that screen sent nothing (15:04 to 15:09: no cloud message, no
web call). The start:

```
15:10:05  clean/start_clean  (76 bytes)
0a4a0801121e0a0408011004121408021002180120022801300138014001480050001801121e0a04080110051214080210021801200228013001380140014800500018021a04080028002801
  = {1: {1: 1, 2: [{1: {1: 1, 2: 4}, 2: {1: 2, 2: 2, 3: 1, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: 0, 10: 0}, 3: 1}, {1: {1: 1, 2: 5}, 2: {1: 2, 2: 2, 3: 1, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1, 9: 0, 10: 0}, 3: 2}], 3: {1: 0, 5: 0}, 5: 1}}
15:10:06  clean/start_clean/response  (2 bytes)
0801
  = {1: 1}
```

The robot's own readback seven seconds later (the app asks both by itself after every start; both
answered `{1: 2}` at 15:10:07, before the job was in force):

```
15:10:12  clean/current_clean_task/get/response  (52 bytes)
08011230080112120a040801100412080802100228014001180112120a04080110051208080210022801400118021a0028013200
  = {1: 1, 2: {1: 1, 2: [{1: {1: 1, 2: 4}, 2: {1: 2, 2: 2, 5: 1, 8: 1}, 3: 1}, {1: {1: 1, 2: 5}, 2: {1: 2, 2: 2, 5: 1, 8: 1}, 3: 2}], 3: '', 5: 1, 6: ''}}
15:10:12  clean/cur_plan/get/response  (36 bytes)
080112201001180220014a0a080410012204080210014a0a080510012204080210015200
  = {1: 1, 2: {2: 1, 3: 2, 4: 1, 9: [{1: 4, 2: 1, 4: {1: 2, 2: 1}}, {1: 5, 2: 1, 4: {1: 2, 2: 1}}], 10: ''}}
```

The house order stored in the robot's configuration at that moment, `config/get/response` field
2.18 (the settings themselves are in [`SETTINGS.md`](SETTINGS.md)):

```
15:10:06  config/get/response field 2.18
08011003220b1a07050406070102032001
  = {1: 1, 2: 3, 4: {3: '05040607010203', 4: 1}}
  4.3 = 05 04 06 07 01 02 03: Toilet, Hallway, Living Room, Kitchen, Master bedroom, Bathroom, Closet
```

The start asked for Hallway (4) then Toilet (5); the stored order has Toilet before Hallway. The
robot cleaned the Hallway first (timeline in section 2).

## 2. A fault seen over the local socket: robot lifted mid-job (2026-11-17 15:10 to 15:14)

The same job. The robot was lifted about 25 s into vacuuming the Hallway and held. The app showed
"(1017) The robot is suspended. Please restart it in an unobstructed location." with the button
"Issue resolved. Continue task."; the robot was put down and the button pressed.

### 2.1 Local poll, `status/get_device_base_status` every 5 s

```
local 15:10:54  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
local 15:10:59  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 fault block
local 15:11:04  field 3 = 080210012003     {1: 2, 2: 1, 4: 3}           field 11 = 1   field 1 fault block
local 15:11:09  field 3 = 080210012003     {1: 2, 2: 1, 4: 3}           field 11 = 1   field 1 empty
local 15:11:14  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
local 15:11:19  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
```

The two answers that carry the fault, whole (the answer is `{1: 1, 2: <status>}`), and the one
before them for comparison:

```
local 15:10:54  status/get_device_base_status answer  (171 bytes)
080112a6010a00150000c8421a04080220032801580160016a20303030303030303030303030303030303030303030303030303030303030303070017801800101900101a00101b80101c00101ca010a12001a0022002a003200d00102e00101f001018202040802200382020508139001048802019002019d022b410a41a002d5c8e3d306b00264b80203c00201c80264e00201f202140a0a120808031204080110020a06080812020819
local 15:10:59  status/get_device_base_status answer  (362 bytes)
080112e5020abe0108b180c41110021ab4010ae99499e8afafe7a0813a307830323331303033310ae7ad89e7baa73a4572726f7220e7baa7e588ab0ae59f9f3ae69cbae599a8e4baba2de6849fe79fa5e5ba94e794a80ae88a82e782b93ae4b8bbe68ea7e69dbf2070657263657074696f6e206e6f64650ae58e9fe59ba03a726f626f742068616e677320757020696e20746865206169720a5be5ba94e794a8e7b3bbe7bb9fe99499e8afafe79a84e58e9fe59ba05d3ae38090e697a0e99499e8afafe38091150000c8421a04080220032801580160016a20303030303030303030303030303030303030303030303030303030303030303070017801800101900101a00101b80101c00101ca010a12001a0022002a003200d00102e00101f001018202040802200382020508139001048802019002019d022b410a41a002d5c8e3d306b00264b80203c00201c80264e00201f202140a0a120808031204080110020a06080812020819
local 15:11:04  status/get_device_base_status answer  (372 bytes)
080112ef020abe0108b180c41110021ab4010ae99499e8afafe7a0813a307830323331303033310ae7ad89e7baa73a4572726f7220e7baa7e588ab0ae59f9f3ae69cbae599a8e4baba2de6849fe79fa5e5ba94e794a80ae88a82e782b93ae4b8bbe68ea7e69dbf2070657263657074696f6e206e6f64650ae58e9fe59ba03a726f626f742068616e677320757020696e20746865206169720a5be5ba94e794a8e7b3bbe7bb9fe99499e8afafe79a84e58e9fe59ba05d3ae38090e697a0e99499e8afafe38091150000c8421a060802100120032801580160016a20303030303030303030303030303030303030303030303030303030303030303070017801800101900101a00101b80101c00101ca010a12001a0022002a003200d00102e00101f00101820206080210012003820207081310019001048802019002019d022b410a41a002d5c8e3d306b00264b80203c00201c80264e00201f202180a0c1208080312040801100218010a080808120208191801
```

Field 1 of the status, alone, and its text (field 1.3, UTF-8; Chinese labels, English cause):

```
08b180c41110021ab4010ae99499e8afafe7a0813a307830323331303033310ae7ad89e7baa73a4572726f7220e7baa7e588ab0ae59f9f3ae69cbae599a8e4baba2de6849fe79fa5e5ba94e794a80ae88a82e782b93ae4b8bbe68ea7e69dbf2070657263657074696f6e206e6f64650ae58e9fe59ba03a726f626f742068616e677320757020696e20746865206169720a5be5ba94e794a8e7b3bbe7bb9fe99499e8afafe79a84e58e9fe59ba05d3ae38090e697a0e99499e8afafe38091
  = {1: 36765745 (0x02310031), 2: 2, 3: <text>}

  错误码:0x02310031
  等级:Error 级别
  域:机器人-感知应用
  节点:主控板 perception node
  原因:robot hangs up in the air
  [应用系统错误的原因]:【无错误】
```

In English: error code 0x02310031; level: Error; domain: robot, perception application; node: main
control board, perception node; cause: "robot hangs up in the air"; the last line reads "cause of
the application-system error: none".

### 2.2 The same seconds on the cloud, `status/robot_base_status`

```
15:10:33  field 3 = 08022007         {1: 2, 4: 7}                 field 11 = 1   field 1 empty
15:10:33  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
15:10:59  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 fault block
15:11:00  field 3 = 080210012003     {1: 2, 2: 1, 4: 3}           field 11 = 1   field 1 fault block
15:11:09  field 3 = 080210012003     {1: 2, 2: 1, 4: 3}           field 11 = 1   field 1 empty
15:11:14  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
```

The block stood from 15:10:59 to 15:11:09, about 10 s. The 5 s local poll caught it twice.

### 2.3 Timeline entries (`status/time_line_status`, cloud push), the whole job

```
15:10:08  0a1208858afdbed593bdf4181001200138014001
  = {1: {1: 1794953408128435461, 2: 1, 4: 1, 7: 1, 8: 1}}
15:10:11  0a1008859ff1b1e293bdf418100938014002
  = {1: {1: 1794953411590639493, 2: 9, 7: 1, 8: 2}}
15:10:27  0a120888bbe99b9d94bdf41810041a0208104002
  = {1: {1: 1794953427382066568, 2: 4, 3: {1: 16}, 8: 2}}
15:10:34  0a1e08c6f489b4b694bdf41810041a0c08011208080110041801200238014003
  = {1: {1: 1794953434143816262, 2: 4, 3: {1: 1, 2: {1: 1, 2: 4, 3: 1, 4: 2}}, 7: 1, 8: 3}}
15:10:58  (168 bytes; field 1.6 is the fault block of 2.1)  0aa5010882e8a0d29195bdf41810041a02081732…
  = {1: {1: <time>, 2: 4, 3: {1: 23}, 6: {1: 36765745, 2: 2, 3: <text>}, 8: 3}}
15:11:08  0a1208e2d68be3b595bdf41810041a02081c4003
  = {1: {1: 1794953468333714274, 2: 4, 3: {1: 28}, 8: 3}}
15:11:13  0a120881ffc1b9c995bdf41810041a02080d4003
  = {1: {1: 1794953473615232897, 2: 4, 3: {1: 13}, 8: 3}}
15:12:42  0a1c08da889caa9398bdf41810041a0c0802120808011004180220024003
  = {1: {1: 1794953562166854746, 2: 4, 3: {1: 2, 2: {1: 1, 2: 4, 3: 2, 4: 2}}, 8: 3}}
15:12:42  0a1e08afd6bfdb9498bdf41810041a0c08011208080110051801200238014004
  = {1: {1: 1794953562538634031, 2: 4, 3: {1: 1, 2: {1: 1, 2: 5, 3: 1, 4: 2}}, 7: 1, 8: 4}}
15:13:50  0a1c08fe8794d8909abdf41810041a0c0802120808011005180220024004
  = {1: {1: 1794953630177362942, 2: 4, 3: {1: 2, 2: {1: 1, 2: 5, 3: 2, 4: 2}}, 8: 4}}
15:13:50  0a12088d8faf87929abdf41810041a02080b4004
  = {1: {1: 1794953630544807821, 2: 4, 3: {1: 11}, 8: 4}}
15:14:17  0a1408a8e492c7f69abdf41810062801320038014005
  = {1: {1: 1794953657522106920, 2: 6, 5: 1, 6: '', 7: 1, 8: 5}}
```

Field 1.1 is a time stamp in nanoseconds. 15:10:58 `3.1 = 23` is the fault, 15:11:08 `3.1 = 28`
the stop after it, 15:11:13 `3.1 = 13` the resume. The closing entry (15:14:17) has `1.5 = 1`.

"Issue resolved. Continue task." in the app:

```
15:11:13  task/resume  (0 bytes)
(empty body)
15:11:13  task/resume/response  (2 bytes)
0801
  = {1: 1}
```

### 2.4 The same timeline from the local socket, `info/get_clean_time_line`

```
local 15:09:34  info/get_clean_time_line answer  (4 bytes)
08011200
  = {1: 1, 2: ''}      (before the job: an empty list)
local 15:14:19  info/get_clean_time_line answer  (437 bytes)
080112b0030a1208858afdbed593bdf41810012001380140010a1008859ff1b1e293bdf4181009380140020a120888bbe99b9d94bdf41810041a02081040020a1e08c6f489b4b694bdf41810041a0c080112080801100418012002380140030aa5010882e8a0d29195bdf41810041a02081732900108b180c41110021a86010ae99499e8afafe7a0813a307830323331303033310ae7ad89e7baa73a4572726f7220e7baa7e588ab0ae59f9f3ae69cbae599a8e4baba2de6849fe79fa5e5ba94e794a80ae88a82e782b93ae4b8bbe68ea7e69dbf2070657263657074696f6e206e6f64650ae58e9fe59ba03a726f626f742068616e677320757020696e207468652061697240030a1208e2d68be3b595bdf41810041a02081c40030a120881ffc1b9c995bdf41810041a02080d40030a1c08da889caa9398bdf41810041a0c08021208080110041802200240030a1e08afd6bfdb9498bdf41810041a0c080112080801100518012002380140040a1c08fe8794d8909abdf41810041a0c08021208080110051802200240040a12088d8faf87929abdf41810041a02080b40040a1408a8e492c7f69abdf41810062801320038014005
```

The second answer holds 12 entries in field 2.1, the same entries with the same time stamps as the
12 pushed over the cloud above. Sizes of the local answer through the job (bytes): 4 before the
start, 42 at 15:10:19, 94 at 15:10:34, 263 at 15:11:04 (the fault entry is in), 303, 365, 415, 437
at 15:14:19.

### 2.5 The end of the job, local poll

```
local 15:13:49  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
local 15:13:54  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 1   field 1 empty
local 15:14:14  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 2   field 1 empty
local 15:14:19  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 3   field 1 empty
local 15:14:24  field 3 = 0813900104       {1: 19, 18: 4}               field 11 = 3   field 1 empty
local 15:14:29  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
```

## 3. `robot_base_status` field 11 (2026-11-17, with the earlier starts)

### 3.1 Mop drying switched on and off from the app's Dock panel

Robot docked at 100 %, no job. "Mop drying" then "End mop drying":

```
15:23:30  supply/dry_mop  (0 bytes)
(empty body)
15:23:31  supply/dry_mop/response  (2 bytes)
0801
  = {1: 1}
15:23:25  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
15:23:31  field 3 = 080e6004         {1: 14, 12: 4}               field 11 = 2   field 1 empty
15:23:33  field 3 = 080e6004         {1: 14, 12: 4}               field 11 = 3   field 1 empty
15:25:02  task/force_end  (3 bytes)
0a0103
  = {1: '03'}
15:25:03  task/force_end/response  (3 bytes)
120101
  = {2: '01'}
15:25:03  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 3   field 1 empty
15:25:04  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
```

Local poll of the same minutes:

```
local 15:23:20  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
local 15:23:35  field 3 = 080e6004         {1: 14, 12: 4}               field 11 = 3   field 1 empty
local 15:25:05  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
```

### 3.2 A wash, then the drying that follows it

"Wash Mop" (the app: "Drying will automatically start after mop washing"):

```
15:29:28  supply/wash_and_dry_mop  (0 bytes)
(empty body)
15:29:28  supply/wash_and_dry_mop/response  (2 bytes)
0801
  = {1: 1}
15:29:28  field 3 = 080e             {1: 14}                      field 11 = 2   field 1 empty
15:29:29  field 3 = 080e6003         {1: 14, 12: 3}               field 11 = 2   field 1 empty
15:31:52  field 3 = 080e6004         {1: 14, 12: 4}               field 11 = 2   field 1 empty
15:34:53  field 3 = 080e6004         {1: 14, 12: 4}               field 11 = 3   field 1 empty
```

`status/working_status` at the moments that matter (field 8 = seconds into the drying, 9 = 18000):

```
15:31:52  48d08c01588c15602b68d08c0178d8049201009a0100
  = {9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:31:52  400148d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 1, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:33:00  404448d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 68, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:33:00  404548d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 69, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:34:52  40b40148d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 180, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:34:52  40b50148d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 181, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:34:53  40b50148d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 181, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:34:53  40b60148d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 182, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
```

Field 11 turned 3 with field 8 at 181: 181 s after the drying state `{1: 14, 12: 4}` began.

### 3.3 Field 11 = 3 after each of the four dockings of 2026-11-17

```
-- end of the two-room job
15:14:05  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 1   field 1 empty
15:14:11  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 2   field 1 empty
15:14:16  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 3   field 1 empty
15:14:23  field 3 = 0813900104       {1: 19, 18: 4}               field 11 = 3   field 1 empty
15:14:26  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 3   field 1 empty
15:14:28  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
-- docking after the manual drive
15:42:25  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 1   field 1 empty
15:42:30  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 2   field 1 empty
15:42:32  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
15:42:34  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
-- end of the cruise
16:03:58  field 3 = 08185002b00106   {1: 24, 10: 2, 22: 6}        field 11 = 1   field 1 empty
16:04:02  field 3 = 08185002b00106   {1: 24, 10: 2, 22: 6}        field 11 = 2   field 1 empty
16:04:05  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
16:04:07  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
16:04:18  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
-- end of the zone job
16:11:30  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 1   field 1 empty
16:11:35  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 2   field 1 empty
16:11:40  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 3   field 1 empty
16:11:43  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
16:11:46  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 3   field 1 empty
16:11:47  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
```

At the three job ends 3 stood for 12 s, 11 s and 7 s. After the manual drive (which had interrupted
the mop drying of section 3.2) it stayed 3: the next change of field 11 in the recording is at the
cruise start, to 1 at 15:59:08. Every status change from 15:42:34 to then:

```
15:42:34  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
15:42:34  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
15:58:43  field 3 = 08011806         {1: 1, 3: 6}                 field 11 = 3   field 1 empty
15:59:01  field 3 = 0818b00101       {1: 24, 22: 1}               field 11 = 3   field 1 empty
15:59:06  field 3 = 0818b00104       {1: 24, 22: 4}               field 11 = 3   field 1 empty
15:59:08  field 3 = 0818b00104       {1: 24, 22: 4}               field 11 = 1   field 1 empty
```

The docking at the end of the job of 2026-11-16 (section 12) shows no such 3: field 11 went 1 → 2 at
18:09:41 and stayed 2, on the cloud and in the local poll.

### 3.4 Field 11 through every recorded start

Each line: the time of `clean/start_clean`; field 3 and field 11 in the last status before it;
then every change until field 11 reads 1. Runs of 2026-11-13 (old room ids, several modes),
2026-11-16 and 2026-11-17.

```
2026-11-13 09:27:38  before: {1: 1, 3: 1} 11=2
      09:27:39 {1: 4, 7: 14} 11=2  →  09:27:46 {1: 4, 7: 18} 11=2  →  09:28:02 {1: 4, 7: 13} 11=2  →  09:28:03 {1: 4, 7: 13} 11=1
2026-11-13 15:01:00  before: {1: 14, 12: 4} 11=3
      15:01:02 {1: 4, 7: 14} 11=3  →  15:01:09 {1: 4, 7: 13} 11=3  →  15:01:10 {1: 4, 7: 13} 11=2  →  15:01:10 {1: 4, 7: 13} 11=1
2026-11-13 15:16:05  before: {1: 14, 12: 4} 11=3
      15:16:07 {1: 4, 7: 14} 11=3  →  15:16:15 {1: 4, 7: 13} 11=3  →  15:16:20 {1: 4, 7: 13} 11=1
2026-11-13 15:20:38  before: {1: 19, 18: 4} 11=3
      15:20:38 {1: 4, 7: 14} 11=3  →  15:20:45 {1: 4, 7: 13} 11=3  →  15:20:49 {1: 4, 7: 13} 11=1
2026-11-13 15:29:17  before: {1: 14, 12: 4} 11=3
      15:29:19 {1: 4, 7: 14} 11=3  →  15:29:26 {1: 4, 7: 13} 11=3  →  15:29:29 {1: 4, 7: 13} 11=1
2026-11-13 15:30:37  before: {1: 19, 18: 4} 11=3
      15:30:38 {1: 4, 7: 14} 11=3  →  15:30:46 {1: 4, 7: 13} 11=3  →  15:30:49 {1: 4, 7: 13} 11=1
2026-11-13 15:36:06  before: {1: 19, 18: 4} 11=2
      15:36:07 {1: 4, 7: 14} 11=2  →  15:36:14 {1: 4, 7: 13} 11=2  →  15:36:15 {1: 4, 7: 13} 11=1
2026-11-13 15:37:34  before: {1: 19, 18: 4} 11=3
      15:37:36 {1: 4, 7: 14} 11=3  →  15:37:43 {1: 4, 7: 13} 11=3  →  15:37:48 {1: 4, 7: 7} 11=3  →  15:37:49 {1: 4, 7: 7} 11=1
2026-11-13 15:39:37  before: {1: 19, 18: 4} 11=3
      15:39:38 {1: 2, 4: 8} 11=3  →  15:39:45 {1: 2, 4: 7} 11=3  →  15:39:50 {1: 2, 4: 7} 11=1
2026-11-13 15:43:31  before: {1: 14, 12: 6} 11=2
      15:43:33 {1: 5, 6: 12} 11=2  →  15:43:39 {1: 5, 6: 12} 11=3  →  15:43:39 {1: 5, 6: 4} 11=3  →  15:43:49 {1: 5, 6: 4} 11=2  →  15:45:36 {1: 5, 6: 11} 11=2  →  15:45:37 {1: 5, 6: 11} 11=1
2026-11-13 15:53:20  before: {1: 14, 12: 4} 11=3
      15:53:22 {1: 2, 4: 8} 11=3  →  15:53:28 {1: 2, 4: 7} 11=3  →  15:53:29 {1: 2, 4: 7} 11=1
2026-11-13 15:56:10  before: {1: 14, 12: 6} 11=2
      15:56:12 {1: 2, 4: 8} 11=2  →  15:56:19 {1: 2, 4: 7} 11=2  →  15:56:20 {1: 2, 4: 7} 11=1
2026-11-13 15:57:23  before: {1: 19, 18: 4} 11=3
      15:57:25 {1: 2, 4: 8} 11=3  →  15:57:30 {1: 2, 4: 7} 11=3  →  15:57:36 {1: 2, 4: 3} 11=3  →  15:57:40 {1: 2, 4: 3} 11=1
2026-11-13 16:04:05  before: {1: 14, 12: 6} 11=2
      16:04:09 {1: 2, 4: 8} 11=2  →  16:04:15 {1: 2, 4: 7} 11=2  →  16:04:15 {1: 2, 4: 7} 11=1
2026-11-13 16:09:08  before: {1: 1, 3: 2} 11=1   (started off the dock)
2026-11-13 16:15:42  before: {1: 1, 3: 1} 11=3
      16:15:44 {1: 2, 4: 8} 11=3  →  16:15:48 {1: 2, 4: 12} 11=3  →  16:16:04 {1: 2, 4: 7} 11=3  →  16:16:05 {1: 2, 4: 7} 11=1
2026-11-13 16:28:37  before: {1: 19, 18: 4} 11=3
      16:28:38 {1: 3, 5: 12} 11=3  →  16:28:46 {1: 3, 5: 4} 11=3  →  16:28:47 {1: 3, 5: 4} 11=2  →  16:30:44 {1: 3, 5: 11} 11=2  →  16:30:45 {1: 3, 5: 11} 11=1
2026-11-16 18:07:47  before: {1: 1, 3: 6} 11=2
      18:07:48 {1: 2, 4: 8} 11=2  →  18:07:54 {1: 2, 4: 12} 11=2  →  18:08:11 {1: 2, 4: 7} 11=2  →  18:08:11 {1: 2, 4: 7} 11=1
2026-11-17 15:10:05  before: {1: 1, 3: 6} 11=2
      15:10:06 {1: 2, 4: 8} 11=2  →  15:10:12 {1: 2, 4: 12} 11=2  →  15:10:28 {1: 2, 4: 7} 11=2  →  15:10:28 {1: 2, 4: 7} 11=1
2026-11-17 16:09:57  before: {1: 1, 3: 1} 11=2
      16:09:57 {1: 2, 4: 8} 11=2  →  16:10:05 {1: 2, 4: 7} 11=2  →  16:10:06 {1: 2, 4: 7} 11=1
```

Reading the table: `{1: 14, 12: 4}` is mop drying, `{1: 19, 18: 4}` dust-bag drying, `{1: 14, 12: 6}`
dust-cabinet disinfection, `{1: 1, …}` standby. In every start field 11 keeps the value it had just
before the start through the self test (`4: 8`, `5: 12`, `6: 12`, `7: 14`) and turns 1 as the robot
leaves. Two starts show a change in between: 2026-11-13 15:43 (2, then 3 for 10 s as the mop wash
began, then 2) and 16:28 (3, then 2 one second into the mop wash).

### 3.5 Field 11 = 3 inside the long job of 2026-11-13 (vacuum then mop, "Freo Mind")

Cloud, `status/robot_base_status`, every change in four windows. Old room numbering; not relevant
here. `7: 6` is returning to charge, `7: 2` returning to wash the mop, `7: 4` washing the mop,
`7: 13` leaving the dock.

```
-- docking for a recharge at 10 % battery
10:58:00  field 3 = 080438065802     {1: 4, 7: 6, 11: 2}          field 11 = 1   field 1 empty
10:58:04  field 3 = 080438065802     {1: 4, 7: 6, 11: 2}          field 11 = 2   field 1 empty
10:58:07  field 3 = 080438065803     {1: 4, 7: 6, 11: 3}          field 11 = 2   field 1 empty
10:58:08  field 3 = 080438065803     {1: 4, 7: 6, 11: 3}          field 11 = 3   field 1 empty
-- leaving after the recharge, at 80 %
12:32:59  field 3 = 080438065803     {1: 4, 7: 6, 11: 3}          field 11 = 3   field 1 empty
12:33:01  field 3 = 08043807         {1: 4, 7: 7}                 field 11 = 3   field 1 empty
12:33:03  field 3 = 0804380d         {1: 4, 7: 13}                field 11 = 3   field 1 empty
12:33:04  field 3 = 0804380d         {1: 4, 7: 13}                field 11 = 1   field 1 empty
-- docking for a mop wash
12:49:49  field 3 = 080438026802     {1: 4, 7: 2, 13: 2}          field 11 = 2   field 1 empty
12:49:53  field 3 = 080438026802     {1: 4, 7: 2, 13: 2}          field 11 = 3   field 1 empty
12:49:56  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 3   field 1 empty
12:49:57  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 2   field 1 empty
-- a mop wash stopped by fault 0x01010035 (clean-water tank empty), resumed once, stopped again
13:43:16  field 3 = 080438026802     {1: 4, 7: 2, 13: 2}          field 11 = 2   field 1 empty
13:43:21  field 3 = 080438026802     {1: 4, 7: 2, 13: 2}          field 11 = 3   field 1 empty
13:43:21  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 3   field 1 empty
13:43:22  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 2   field 1 empty
13:43:49  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 2   field 1 fault block
13:43:51  field 3 = 080410013804     {1: 4, 2: 1, 7: 4}           field 11 = 2   field 1 fault block
13:43:53  field 3 = 080410013804     {1: 4, 2: 1, 7: 4}           field 11 = 2   field 1 empty
13:46:53  field 3 = 080410013804     {1: 4, 2: 1, 7: 4}           field 11 = 3   field 1 empty
13:52:54  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 2   field 1 empty
13:52:59  field 3 = 08043804         {1: 4, 7: 4}                 field 11 = 2   field 1 fault block
13:53:00  field 3 = 080410013804     {1: 4, 2: 1, 7: 4}           field 11 = 2   field 1 fault block
13:53:02  field 3 = 080410013804     {1: 4, 2: 1, 7: 4}           field 11 = 2   field 1 empty
13:56:01  field 3 = 080410013804     {1: 4, 2: 1, 7: 4}           field 11 = 3   field 1 empty
```

Field 11 read 3 from the second after docking for the whole recharge (10:58:08 to 12:33:04). At
the start of two washes it read 3 for a few seconds (12:49:53 to 12:49:57; 13:43:21). While the
wash stood paused it turned 3 at 13:46:53 and 13:56:01: 182 s and 181 s after the pause marker
3.2 = 1 appeared (13:43:51, 13:53:00).

## 4. Dock commands from the app's Dock panel (2026-11-17 15:23 to 15:42)

One press each. Every body is empty unless shown.

```
-- "Mop drying"
15:23:30  supply/dry_mop  (0 bytes)
(empty body)
15:23:31  supply/dry_mop/response  (2 bytes)
0801
  = {1: 1}
-- "End mop drying"
15:25:02  task/force_end  (3 bytes)
0a0103
  = {1: '03'}
15:25:03  task/force_end/response  (3 bytes)
120101
  = {2: '01'}
-- "Dock dust emptying"
15:26:23  supply/dust_gathering  (0 bytes)
(empty body)
15:26:24  supply/dust_gathering/response  (2 bytes)
0801
  = {1: 1}
-- "End dust bag drying and disinfection"
15:28:19  task/force_end  (4 bytes)
0a020102
  = {1: '0102'}
15:28:20  task/force_end/response  (4 bytes)
12020102
  = {2: '0102'}
-- "Dust bag dry & disinfect"
15:28:43  supply/dry_station_bag  (0 bytes)
(empty body)
15:28:44  supply/dry_station_bag/response  (2 bytes)
0801
  = {1: 1}
-- "Wash Mop"
15:29:28  supply/wash_and_dry_mop  (0 bytes)
(empty body)
15:29:28  supply/wash_and_dry_mop/response  (2 bytes)
0801
  = {1: 1}
-- taking over the drive pad during a return to the dock
15:41:44  task/force_end  (0 bytes)
(empty body)
15:41:46  task/force_end/response  (2 bytes)
0801
  = {1: 1}
-- the home button in the video view
15:42:17  supply/recall  (0 bytes)
(empty body)
15:42:18  supply/recall/response  (2 bytes)
0801
  = {1: 1}
```

Status after each (cloud, `status/robot_base_status`, every change of field 3, field 11 or field 1):

```
15:25:05  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
15:26:26  field 3 = 0813900101       {1: 19, 18: 1}               field 11 = 2   field 1 empty
15:26:42  field 3 = 08131001900104   {1: 19, 2: 1, 18: 4}         field 11 = 2   field 1 empty
15:26:42  field 3 = 0813900104       {1: 19, 18: 4}               field 11 = 2   field 1 empty
15:28:20  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
15:28:44  field 3 = 08131001900104   {1: 19, 2: 1, 18: 4}         field 11 = 2   field 1 empty
15:28:44  field 3 = 0813900104       {1: 19, 18: 4}               field 11 = 2   field 1 empty
15:29:28  field 3 = 080e             {1: 14}                      field 11 = 2   field 1 empty
15:29:29  field 3 = 080e6003         {1: 14, 12: 3}               field 11 = 2   field 1 empty
   (15:31:52 to 15:39:30: section 3.2 and section 5)
15:41:23  field 3 = 080a5001         {1: 10, 10: 1}               field 11 = 1   field 1 empty
15:41:46  field 3 = 08011802         {1: 1, 3: 2}                 field 11 = 1   field 1 empty
15:41:46  field 3 = 0815980101       {1: 21, 19: 1}               field 11 = 1   field 1 empty
15:42:18  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 1   field 1 empty
15:42:30  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 2   field 1 empty
15:42:32  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
15:42:34  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
```

For comparison, the form the app sent on 2026-11-13 for "press and hold to end" on a running
cleaning job (seven times that day, each answered `{1: 1}`; the robot stopped where it stood):

```
15:16:51  task/force_end  (4 bytes)
12020102
  = {2: '0102'}
15:16:56  task/force_end/response  (2 bytes)
0801
  = {1: 1}
```

So four request forms were seen: `{1: [3]}`, `{1: [1, 2]}`, `{2: [1, 2]}`, and an empty body.

## 5. Status states not yet in `PROTOCOL.md` (2026-11-17)

### 5.1 Manual drive from the video view, and the return (local poll; the cloud recording has a gap here)

```
local 15:38:00  field 3 = 080e6004         {1: 14, 12: 4}               field 11 = 3   field 1 empty
local 15:39:15  field 3 = 080e10016004     {1: 14, 2: 1, 12: 4}         field 11 = 3   field 1 empty
local 15:39:30  field 3 = 080e10016004     {1: 14, 2: 1, 12: 4}         field 11 = 1   field 1 empty
local 15:40:15  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 1   field 1 empty
local 15:40:25  field 3 = 080a5001         {1: 10, 10: 1}               field 11 = 1   field 1 empty
local 15:41:50  field 3 = 0815980101       {1: 21, 19: 1}               field 11 = 1   field 1 empty
local 15:42:20  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 1   field 1 empty
local 15:42:30  field 3 = 080a5002         {1: 10, 10: 2}               field 11 = 2   field 1 empty
local 15:42:35  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
```

### 5.2 `robot_base_status` field 32: several states at once

Field 32 is a repeated message of the same form as field 3. Its first entry equalled field 3 in
every message looked at; at times it holds more entries. Samples (cloud):

```
15:10:34  field 3 = {1: 2, 4: 3}   field 11 = 1
            field 32 entry  08022003       {1: 2, 4: 3}
            field 32 entry  0813900104     {1: 19, 18: 4}
15:14:27  field 3 = {1: 14, 12: 6}   field 11 = 3
            field 32 entry  080e6006       {1: 14, 12: 6}
            field 32 entry  08131001900104 {1: 19, 2: 1, 18: 4}
15:23:32  field 3 = {1: 14, 12: 4}   field 11 = 2
            field 32 entry  080e6004       {1: 14, 12: 4}
            field 32 entry  080e6006       {1: 14, 12: 6}
            field 32 entry  08131001900104 {1: 19, 2: 1, 18: 4}
15:29:30  field 3 = {1: 14, 12: 3}   field 11 = 2
            field 32 entry  080e6003       {1: 14, 12: 3}
            field 32 entry  08131001900104 {1: 19, 2: 1, 18: 4}
15:39:15  field 3 = {1: 14, 2: 1, 12: 4}   field 11 = 3
            field 32 entry  080e10016004   {1: 14, 2: 1, 12: 4}
            field 32 entry  08131001900104 {1: 19, 2: 1, 18: 4}
            field 32 entry  0815980101     {1: 21, 19: 1}
15:41:24  field 3 = {1: 10, 10: 1}   field 11 = 1
            field 32 entry  080a5001       {1: 10, 10: 1}
            field 32 entry  080e10016004   {1: 14, 2: 1, 12: 4}
            field 32 entry  08131001900104 {1: 19, 2: 1, 18: 4}
15:42:35  field 3 = {1: 1, 3: 1}   field 11 = 3
            field 32 entry  08011801       {1: 1, 3: 1}
15:59:21  field 3 = {1: 24, 22: 3}   field 11 = 1
            field 32 entry  0818b00103     {1: 24, 22: 3}
```

The app's Dock panel at 15:22 read "Dust cabinet disinfection" and "Dust bag drying paused"; the
status then was field 3 = `{1: 14, 12: 6}` with a second entry `{1: 19, 2: 1, 18: 4}` in field 32.
At 15:39:15 the robot was being driven by hand from the video view. At 15:42:35 (field 11 = 3,
standby) field 32 has the one standby entry only.

## 6. `common/yell` and `common/reboot` from the app (2026-11-17 14:48 to 14:50)

"Locate Robot" (pressed twice, and once more after the restart) and "Restart Robot":

```
14:48:14  common/yell              (empty body)
14:48:14  common/yell/response     0801  = {1: 1}
14:48:36  common/yell              (empty body)
14:48:37  common/yell/response     0801  = {1: 1}
14:49:34  common/reboot            (empty body)
14:49:35  common/reboot/response   0801  = {1: 1}
14:51:19  common/yell              (empty body)
14:51:19  common/yell/response     0801  = {1: 1}
last status/robot_base_status before the restart: 14:49:39
first after it: 14:50:38
```

## 7. Topics the app used that are not in the topic table

### 7.1 `clean/cur_plan/get`

Sent by the app, empty body, together with `clean/current_clean_task/get` after every start and
after a recall. Answers seen on 2026-11-17:

```
15:10:07  (2 bytes)  0802
  = {1: 2}
15:10:12  (36 bytes)  080112201001180220014a0a080410012204080210014a0a080510012204080210015200
  = {1: 1, 2: {2: 1, 3: 2, 4: 1, 9: [{1: 4, 2: 1, 4: {1: 2, 2: 1}}, {1: 5, 2: 1, 4: {1: 2, 2: 1}}], 10: ''}}
15:42:19  (2 bytes)  0802
  = {1: 2}
15:59:02  (2 bytes)  0802
  = {1: 2}
16:09:58  (2 bytes)  0802
  = {1: 2}
16:10:06  (736 bytes)  080112db051001180220014ad005080110021ac3050a04080710030a0408…  (whole in section 8)
```

### 7.2 `status/point_navi_plan_traj` (robot → cloud, broadcast)

```
15:10:35 to 15:13:59  117 messages
15:41:23 to 15:41:45  25 messages
15:59:22 to 16:03:53  222 messages
16:10:14 to 16:11:26  45 messages

per minute: 15:10 ×7  15:11 ×16  15:12 ×60  15:13 ×34  15:41 ×25  15:59 ×40  16:00 ×59  16:01 ×47  16:02 ×51  16:03 ×25  16:10 ×21  16:11 ×24
```

What ran at those times: 15:10 to 15:13 the two-room vacuum job; 15:41 the return to the dock
after the manual drive; 15:59 to 16:03 the cruise; 16:10 to 16:11 the drawn-zone job. Nobody asked
for it: no request on this topic appears in the recording. First message of the cruise, cut:

```
15:59:22  status/point_navi_plan_traj  (1512 bytes)
0a0a0d70a3a3bd151d5c673e0a0a0dfc36bfbe1505e13abf0a0a0d07c22abf150ecdd7bf0a0a0d91e875bf158b1429c00a0a0d8d87a0bf15d04266c00a0a0dd21ac6bf158bb891c00a0a0d59aeebbf15…
  = {1: [{1: -0.07990157604217529, 2: 0.22593732178211212}, {1: -0.3734663724899292, 2: -0.7299960255622864}, {1: -0.6670231223106384, 2: -1.6859452724456787}, {1: -0.9605799317359924, 2: -2.641878843307495}, {1: -1.2541366815567017, 2: -3.597827911376953}, {1: -1.5476934909820557, 2: -4.55377721786499}, {1: -1.84125816822052, 2: -5 …
  126 points {1: x, 2: y}, float32
```

### 7.3 `status/streaming_info` (robot → cloud, while live video is viewed)

```
15:33:52  status/streaming_info  (9 bytes)
08ce14180130013802
  = {1: 2638, 3: 1, 6: 1, 7: 2}
15:33:53  status/streaming_info  (9 bytes)
08cf14180130013802
  = {1: 2639, 3: 1, 6: 1, 7: 2}
15:33:54  status/streaming_info  (9 bytes)
08d014180130013802
  = {1: 2640, 3: 1, 6: 1, 7: 2}

15:33:52 to 15:35:34  103 messages
15:35:52 to 15:37:26  95 messages
15:38:29 to 15:39:35  67 messages
15:41:23 to 15:44:00  158 messages

fields other than the counter (field 1), all messages: {3: 1, 6: 1, 7: 2} ×9; {3: 1, 4: 1, 6: 2, 7: 2} ×350; {3: 1, 4: 1, 5: 1, 6: 3, 7: 2} ×9; {7: 2} ×31; {3: 1, 4: 1, 6: 2, 7: 1} ×24
```

The video view was opened at 15:33:51 and closed at about 15:37:26; opened again at 15:38:28 for
the manual drive. The cloud recording has its gap from 15:39:35 to 15:41:20.

### 7.4 Map topics used by the app's editor and settings (content: [`MAP-FORMAT.md`](MAP-FORMAT.md))

```
map/check_map_update_info              ×1  first 15:02:15  0 bytes  (empty body)
map/check_map_update_info/response     ×1  first 15:02:15  15923 bytes  12b07c08011079183c209b01…
map/get_editable_map                   ×8  first 15:52:41  6 bytes  080110001800  = {1: 1, 2: 0, 3: 0}
map/get_editable_map/response          ×8  first 15:52:42  12699 bytes  0801128f6308011079183c20…
map/operation                          ×1  first 16:00:44  71 bytes  08011079189916223a223808…
map/operation/response                 ×1  first 16:00:45  12695 bytes  0801128f6308011079183c20…
map/enable_temp_map                    ×1  first 16:13:37  12 bytes  08011208080110d5b0b1ce06  = {1: 1, 2: {1: 1, 2: 1774999637}}
map/enable_temp_map/response           ×1  first 16:13:37  2 bytes  0802  = {1: 2}
```

### 7.5 Other requests the app sends by itself

```
task/get_continue_task                     ×2  bodies: (empty) ×2
task/get_continue_task/response            ×2  bodies: (empty) ×2
common/notify_app_event                    ×6  bodies: 0801 ×2, 0802 ×4
common/notify_app_event/response           ×6  bodies: 0801 ×6
consumable/get_consumable_info             ×5  bodies: (empty) ×5
consumable/get_consumable_info/response    ×5  bodies: 0a00 ×5
```

## 8. A drawn-zone job that ran to a normal end (2026-11-17 16:09 to 16:11)

In the app: a rectangle of about 0.7 × 1 m drawn in the Hallway, "Vacuum" ×1. The app showed "Area
cleaning in progress" and "Area1".

```
16:09:57  clean/start_clean  (758 bytes)
0af305080112e6050acb05080210011a04080710031a04081310031a0d081310f3ffffffffffffffff011a0d080710f3ffffffffffffffff012204080710032204080810032204080910032204080a10032204080b10032204080c10032204080d10032204080e10032204080f1003220408101003220408111003220408121003220408131003220408131002220408131001220408131000220d081310ffffffffffffffffff01220d081310feffffffffffffffff01220d081310fdffffffffffffffff01220d081310fcffffffffffffffff01220d081310fbffffffffffffffff01220d081310faffffffffffffffff01220d081310f9ffffffffffffffff01220d081310f8ffffffffffffffff01220d081310f7ffffffffffffffff01220d081310f6ffffffffffffffff01220d081310f5ffffffffffffffff01220d081310f4ffffffffffffffff01220d081310f3ffffffffffffffff01220d081210f3ffffffffffffffff01220d081110f3ffffffffffffffff01220d081010f3ffffffffffffffff01220d080f10f3ffffffffffffffff01220d080e10f3ffffffffffffffff01220d080d10f3ffffffffffffffff01220d080c10f3ffffffffffffffff01220d080b10f3ffffffffffffffff01220d080a10f3ffffffffffffffff01220d080910f3ffffffffffffffff01220d080810f3ffffffffffffffff01220d080710f3ffffffffffffffff01220d080710f4ffffffffffffffff01220d080710f5ffffffffffffffff01220d080710f6ffffffffffffffff01220d080710f7ffffffffffffffff01220d080710f8ffffffffffffffff01220d080710f9ffffffffffffffff01220d080710faffffffffffffffff01220d080710fbffffffffffffffff01220d080710fcffffffffffffffff01220d080710fdffffffffffffffff01220d080710feffffffffffffffff01220d080710ffffffffffffffffff012204080710002204080710012204080710021214080210011801200228013001380140014800500018011a04080028002801
  = {1: {1: 1, 2: {1: {1: 2, 2: 1, 3: [{1: 7, 2: 3}, {1: 19, 2: 3}, {1: 19, 2: 18446744073709551603}, {1: 7, 2: 18446744073709551603}], 4: [{1: 7, 2: 3}, {1: 8, 2: 3}, {1: 9, 2: 3}, {1: 10, 2: 3}, {1: 11, 2: 3}, {1: 12, 2: 3}, {1: 13, 2: 3}, {1: 14, 2: 3}, {1: 15, 2: 3}, {1: 16, 2: 3}, {1: 17, 2: 3}, {1: 18, 2: 3}, {1: 19, 2: 3}, {1: 19, 2: 2}, {1: 19, 2: 1}, {1: 19, 2: 0}, {1: 19, 2: 18446744073709551615}, {1: 19, 2: 18446744073709551614}, {1: 19, 2: 18446744073709551613}, {1: 19, 2: 18446744073709551612}, {1: 19, 2:  …
16:09:57  clean/start_clean/response  (2 bytes)
0801
  = {1: 1}
```

The zone, read out: `{1: 2, 2: 1, 3: [4 corners], 4: [56 outline points]}`; corners (7, 3) (19, 3) (19, -13) (7, -13); the outline
starts (7, 3) (8, 3) (9, 3) (10, 3) … and ends … (7, 0) (7, 1) (7, 2). A point with x or y = 0 omits that field.

Status, cloud:

```
16:09:50  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
16:09:57  field 3 = 08022008         {1: 2, 4: 8}                 field 11 = 2   field 1 empty
16:10:05  field 3 = 08022007         {1: 2, 4: 7}                 field 11 = 2   field 1 empty
16:10:06  field 3 = 08022007         {1: 2, 4: 7}                 field 11 = 1   field 1 empty
16:10:12  field 3 = 08022004         {1: 2, 4: 4}                 field 11 = 1   field 1 empty
16:11:15  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 1   field 1 empty
16:11:35  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 2   field 1 empty
16:11:40  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 3   field 1 empty
16:11:43  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
16:11:46  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 3   field 1 empty
16:11:47  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
```

Timeline, cloud push:

```
16:10:01  0a1208eec483f69efcbdf4181001200138014001
  = {1: {1: 1794957001252463214, 2: 1, 4: 1, 7: 1, 8: 1}}
16:10:05  0a120881dc97d4acfcbdf41810041a0208104001
  = {1: {1: 1794957004939587073, 2: 4, 3: {1: 16}, 8: 1}}
16:10:13  0a1e08d384c5dccbfcbdf41810041a0c08011208080210011801200238014002
  = {1: {1: 1794957013278605907, 2: 4, 3: {1: 1, 2: {1: 2, 2: 1, 3: 1, 4: 2}}, 7: 1, 8: 2}}
16:11:14  0a1c08fbf2c5fbaefebdf41810041a0c0802120808021001180220024002
  = {1: {1: 1794957074278480251, 2: 4, 3: {1: 2, 2: {1: 2, 2: 1, 3: 2, 4: 2}}, 8: 2}}
16:11:15  0a1208828ce3b2b1febdf41810041a02080b4002
  = {1: {1: 1794957074931172866, 2: 4, 3: {1: 11}, 8: 2}}
16:11:38  0a1408d2bbe4d489ffbdf41810062801320038014003
  = {1: {1: 1794957098624818642, 2: 6, 5: 1, 6: '', 7: 1, 8: 3}}
```

The readbacks while the job ran:

```
16:10:06  clean/current_clean_task/get/response  (742 bytes)
080112e105080112d6050ac705080210011a04080710031a04081310031a0d081310f3ffffffffffffffff011a0d080710f3ffffffffffffffff012204080710032204080810032204080910032204080a10032204080b10032204080c10032204080d10032204080e10032204080f100322040810100322040811100322040812100322040813100322040813100222040813100122020813220d081310ffffffffffffffffff01220d081310feffffffffffffffff01220d081310fdffffffffffffffff01220d081310fcffffffffffffffff01220d081310fbffffffffffffffff01220d081310faffffffffffffffff01220d081310f9ffffffffffffffff01220d081310f8ffffffffffffffff01220d081310f7ffffffffffffffff01220d081310f6ffffffffffffffff01220d081310f5ffffffffffffffff01220d081310f4ffffffffffffffff01220d081310f3ffffffffffffffff01220d081210f3ffffffffffffffff01220d081110f3ffffffffffffffff01220d081010f3ffffffffffffffff01220d080f10f3ffffffffffffffff01220d080e10f3ffffffffffffffff01220d080d10f3ffffffffffffffff01220d080c10f3ffffffffffffffff01220d080b10f3ffffffffffffffff01220d080a10f3ffffffffffffffff01220d080910f3ffffffffffffffff01220d080810f3ffffffffffffffff01220d080710f3ffffffffffffffff01220d080710f4ffffffffffffffff01220d080710f5ffffffffffffffff01220d080710f6ffffffffffffffff01220d080710f7ffffffffffffffff01220d080710f8ffffffffffffffff01220d080710f9ffffffffffffffff01220d080710faffffffffffffffff01220d080710fbffffffffffffffff01220d080710fcffffffffffffffff01220d080710fdffffffffffffffff01220d080710feffffffffffffffff01220d080710ffffffffffffffffff01220208072204080710012204080710021208080210012801400118011a0028013200
  = {1: 1, 2: {1: 1, 2: {1: {1: 2, 2: 1, 3: [{1: 7, 2: 3}, {1: 19, 2: 3}, {1: 19, 2: 18446744073709551603}, {1: 7, 2: 18446744073709551603}], 4: [{1: 7, 2: 3}, {1: 8, 2: 3}, {1: 9, 2: 3}, {1: 10, 2: 3}, {1: 11, 2: 3}, {1: 12, 2: 3}, {1: 13, 2: 3}, {1: 14, 2: 3}, {1: 15, 2: 3}, {1: 16, 2: 3}, {1: 17, 2: 3}, {1: 18, 2: 3}, {1: 19, 2:  …
16:10:06  clean/cur_plan/get/response  (736 bytes)
080112db051001180220014ad005080110021ac3050a04080710030a04080810030a04080910030a04080a10030a04080b10030a04080c10030a04080d10030a04080e10030a04080f10030a04081010030a04081110030a04081210030a04081310030a04081310020a04081310010a0208130a0d081310ffffffffffffffffff010a0d081310feffffffffffffffff010a0d081310fdffffffffffffffff010a0d081310fcffffffffffffffff010a0d081310fbffffffffffffffff010a0d081310faffffffffffffffff010a0d081310f9ffffffffffffffff010a0d081310f8ffffffffffffffff010a0d081310f7ffffffffffffffff010a0d081310f6ffffffffffffffff010a0d081310f5ffffffffffffffff010a0d081310f4ffffffffffffffff010a0d081310f3ffffffffffffffff010a0d081210f3ffffffffffffffff010a0d081110f3ffffffffffffffff010a0d081010f3ffffffffffffffff010a0d080f10f3ffffffffffffffff010a0d080e10f3ffffffffffffffff010a0d080d10f3ffffffffffffffff010a0d080c10f3ffffffffffffffff010a0d080b10f3ffffffffffffffff010a0d080a10f3ffffffffffffffff010a0d080910f3ffffffffffffffff010a0d080810f3ffffffffffffffff010a0d080710f3ffffffffffffffff010a0d080710f4ffffffffffffffff010a0d080710f5ffffffffffffffff010a0d080710f6ffffffffffffffff010a0d080710f7ffffffffffffffff010a0d080710f8ffffffffffffffff010a0d080710f9ffffffffffffffff010a0d080710faffffffffffffffff010a0d080710fbffffffffffffffff010a0d080710fcffffffffffffffff010a0d080710fdffffffffffffffff010a0d080710feffffffffffffffff010a0d080710ffffffffffffffffff010a0208070a04080710010a0408071002120408071003120408131003120d081310f3ffffffffffffffff01120d080710f3ffffffffffffffff012204080110015200
  = {1: 1, 2: {2: 1, 3: 2, 4: 1, 9: {1: 1, 2: 2, 3: {1: [{1: 7, 2: 3}, {1: 8, 2: 3}, {1: 9, 2: 3}, {1: 10, 2: 3}, {1: 11, 2: 3}, {1: 12, 2: 3}, {1: 13, 2: 3}, {1: 14, 2: 3}, {1: 15, 2: 3}, {1: 16, 2: 3}, {1: 17, 2: 3}, {1: 18, 2: 3}, {1: 19, 2: 3}, {1: 19, 2: 2}, {1: 19, 2: 1}, {1: 19}, {1: 19, 2: 18446744073709551615}, {1: 19, 2: 1 …
```

## 9. A cruise started by a schedule (2026-11-17 15:59 to 16:04)

A cruise schedule with three points in the Kitchen was saved in the app for one minute ahead (a
web call: [`CLOUD-API.md`](CLOUD-API.md)). No command to the robot appears in the cloud
recording between 15:57 and 15:59:01; the only requests near the start are the app's two reads:

```
15:59:01  clean/current_clean_task/get  (empty body)
15:59:01  clean/cur_plan/get  (empty body)
15:59:02  clean/current_clean_task/get/response  0802
15:59:02  clean/cur_plan/get/response  0802
```

Status, cloud (the robot was lifted on its way home at 16:02:57):

```
15:58:40  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
15:58:43  field 3 = 08011806         {1: 1, 3: 6}                 field 11 = 3   field 1 empty
15:59:01  field 3 = 0818b00101       {1: 24, 22: 1}               field 11 = 3   field 1 empty
15:59:06  field 3 = 0818b00104       {1: 24, 22: 4}               field 11 = 3   field 1 empty
15:59:08  field 3 = 0818b00104       {1: 24, 22: 4}               field 11 = 1   field 1 empty
15:59:12  field 3 = 0818b00101       {1: 24, 22: 1}               field 11 = 1   field 1 empty
15:59:20  field 3 = 0818b00103       {1: 24, 22: 3}               field 11 = 1   field 1 empty
16:02:32  field 3 = 08185001b00106   {1: 24, 10: 1, 22: 6}        field 11 = 1   field 1 empty
16:02:57  field 3 = 08185001b00106   {1: 24, 10: 1, 22: 6}        field 11 = 1   field 1 fault block
16:02:58  field 3 = 081810015001b00106 {1: 24, 2: 1, 10: 1, 22: 6}  field 11 = 1   field 1 fault block
16:02:59  field 3 = 081810015001b00106 {1: 24, 2: 1, 10: 1, 22: 6}  field 11 = 1   field 1 empty
16:03:33  field 3 = 08185001b00106   {1: 24, 10: 1, 22: 6}        field 11 = 1   field 1 empty
16:03:35  field 3 = 08185003b00106   {1: 24, 10: 3, 22: 6}        field 11 = 1   field 1 empty
16:03:40  field 3 = 08185001b00106   {1: 24, 10: 1, 22: 6}        field 11 = 1   field 1 empty
16:03:54  field 3 = 08185002b00106   {1: 24, 10: 2, 22: 6}        field 11 = 1   field 1 empty
16:04:02  field 3 = 08185002b00106   {1: 24, 10: 2, 22: 6}        field 11 = 2   field 1 empty
16:04:05  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
16:04:07  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 3   field 1 empty
16:04:18  field 3 = 08011801         {1: 1, 3: 1}                 field 11 = 2   field 1 empty
```

Timeline, cloud push:

```
15:59:03  0a1208a8e8a0da8be9bdf4181001200138014007
  = {1: {1: 1794956343258919976, 2: 1, 4: 1, 7: 1, 8: 7}}
15:59:06  0a1208c687b8f096e9bdf41810041a0208104007
  = {1: {1: 1794956346258228166, 2: 4, 3: {1: 16}, 8: 7}}
15:59:14  0a1208c390fed7b4e9bdf4181001200138014008
  = {1: {1: 1794956354260011075, 2: 1, 4: 1, 7: 1, 8: 8}}
16:02:57  (166 bytes)  0aa301089e92b5ecf1efbdf418100532900108b1…
  = {1: {1: <time>, 2: 5, 6: {1: 36765745, 2: 2, 3: <text as in section 2>}, 7: 1, 8: 9}}
     decoded head: {1: {1: 1794956576835848478, 2: 5, 6: {1: 36765745, 2: 2, 3: …
16:02:58  0a1208d1fbb9cbf5efbdf41810041a02081c4009
  = {1: {1: 1794956577840463313, 2: 4, 3: {1: 28}, 8: 9}}
```

`status/working_status` during the cruise: one form only, in which only field 20 changes. Field 7
is text:

```
15:59:01  status/working_status  (191 bytes)
3a9d017b227461736b223a225b783a202d33372e35383331383633363039363431395c6e793a202d3132302e34353531323434333636303539365c6e2c20783a202d33382e35363339383139373133383934315c6e793a202d3134382e3139373632383834353737375c6e2c20783a202d33362e3838323631383036373830333236345c6e793a202d3136342e35393039323639303537343137355c6e5d227d588c1568d08c0178d8049201009a0100a2010c08c1f7b2cc81e9bdf4181803
  7  = {"task":"[x: -37.58318636096419\ny: -120.45512443660596\n, x: -38.56398197138941\ny: -148.197628845777\n, x: -36.882618067803264\ny: -164.59092690574175\n]"}
  20 = {1: 1794956340545502145, 3: 3}
  other fields: 11: 2700, 13: 18000, 15: 600

field 20 at each change of 20.4, around the lift, and at the end:
  15:59:01  20 = {1: <start time>, 3: 3}
  16:01:57  20 = {1: <start time>, 2: 177, 3: 3, 4: 1}
  16:02:19  20 = {1: <start time>, 2: 198, 3: 3, 4: 2}
  16:02:32  20 = {1: <start time>, 2: 211, 3: 3, 4: 3}
  16:02:57  20 = {1: <start time>, 2: 236, 3: 3, 4: 3}
  16:03:33  20 = {1: <start time>, 2: 236, 3: 3, 4: 3}
  16:04:05  20 = {1: <start time>, 2: 269, 3: 3, 4: 3}
```

20.2 rose by one a second and stood still from 16:02:57 to 16:03:33 (the lift, until "Continue").
20.3 was 3 throughout (three points were set). 20.4 appeared as 1, 2, 3; the app showed "Cruise
point completed n/3".

"Continue" in the app after the lift:

```
16:03:32  task/resume  (0 bytes)
(empty body)
16:03:33  task/resume/response  (2 bytes)
0801
  = {1: 1}
```

`status/video_cruise_task_status` was subscribed and delivered nothing. `status/point_navi_plan_traj`
during the cruise: section 7.2.

## 10. `status/working_status` through 2026-11-17 (cloud)

Two messages a second while a client kept the stream alive and something was running. The app was
open and sending keep-alives from 14:38; the first `status/working_status` and the first
`map/display_map` of the day arrived at 15:10:06, one second after the job was started. Every
change in the set of fields present, with the message at that moment:

```
15:10:06  68d08c0178d8049201009a0100
  = {13: 18000, 15: 600, 18: '', 19: ''}
15:10:07  180168d08c0178d8049201009a0100
  = {3: 1, 13: 18000, 15: 600, 18: '', 19: ''}
15:10:12  18052a0208042a02080568d08c0178d8049201009a0100
  = {3: 5, 5: [{1: 4}, {1: 5}], 13: 18000, 15: 600, 18: '', 19: ''}
15:10:28  18152a0208042a020805300468d08c0178d8049201009a0100
  = {3: 21, 5: [{1: 4}, {1: 5}], 6: 4, 13: 18000, 15: 600, 18: '', 19: ''}
15:10:30  18182a0208042a0208053004600168d08c0178d8049201009a0100
  = {3: 24, 5: [{1: 4}, {1: 5}], 6: 4, 12: 1, 13: 18000, 15: 600, 18: '', 19: ''}
15:10:41  0d00000040157cf2b03d18232a0208042a0208053004600c68d08c0178d8049201009a0100
  = {1: 2.0, 2: 0.08640000224113464, 3: 35, 5: [{1: 4}, {1: 5}], 6: 4, 12: 12, 13: 18000, 15: 600, 18: '', 19: ''}
15:14:18  0d0000c8421558a825402a04080410012a0408051001300560da0168d08c0178d8049201009a0100
  = {1: 100.0, 2: 2.588399887084961, 5: [{1: 4, 2: 1}, {1: 5, 2: 1}], 6: 5, 12: 218, 13: 18000, 15: 600, 18: '', 19: ''}
15:14:23  60e00168d08c0178d8049201009a0100
  = {12: 224, 13: 18000, 15: 600, 18: '', 19: ''}
15:14:26  588c1560e20168d08c0178d8049201009a01020801
  = {11: 2700, 12: 226, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:14:27  5001588c1560e20168d08c0178d8049201009a01020801
  = {10: 1, 11: 2700, 12: 226, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:23:31  48d08c0150a104588c1560e20168d08c0178d8049201009a01020801
  = {9: 18000, 10: 545, 11: 2700, 12: 226, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:23:33  400148d08c0150a304588c1560e20168d08c0178d8049201009a01020801
  = {8: 1, 9: 18000, 10: 547, 11: 2700, 12: 226, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:25:03  50fd04588c1560e20168d08c0178d8049201009a01020801
  = {10: 637, 11: 2700, 12: 226, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:26:25  50cf05588c1568d08c0178d8049201009a01020801
  = {10: 719, 11: 2700, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:26:26  588c1568d08c0178d8049201009a01020801
  = {11: 2700, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
15:26:44  588c15600168d08c0178d8049201009a0100
  = {11: 2700, 12: 1, 13: 18000, 15: 600, 18: '', 19: ''}
15:28:20  588c1568d08c0178d8049201009a0100
  = {11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
15:28:46  588c15600168d08c0178d8049201009a0100
  = {11: 2700, 12: 1, 13: 18000, 15: 600, 18: '', 19: ''}
15:31:52  48d08c01588c15602b68d08c0178d8049201009a0100
  = {9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:31:52  400148d08c01588c15602b68d08c0178d8049201009a0100
  = {8: 1, 9: 18000, 11: 2700, 12: 43, 13: 18000, 15: 600, 18: '', 19: ''}
15:41:45  40b90348d08c01588c1568d08c0178d8049201009a0100
  = {8: 441, 9: 18000, 11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
15:41:45  588c1568d08c0178d8049201009a0100
  = {11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
16:09:59  1801588c1568d08c0178d8049201009a0100
  = {3: 1, 11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
16:10:14  18103001588c1568d08c0178d8049201009a0100
  = {3: 16, 6: 1, 11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
16:10:17  0d00001041159c33a23d18133001588c1568d08c0178d8049201009a0100
  = {1: 9.0, 2: 0.07919999957084656, 3: 19, 6: 1, 11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
16:11:39  0d0000c8421571ac4b3f3001588c1568d08c0178d8049201009a0100
  = {1: 100.0, 2: 0.7955999970436096, 6: 1, 11: 2700, 13: 18000, 15: 600, 18: '', 19: ''}
16:11:46  588c1568d08c0178d8049201009a01020801
  = {11: 2700, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
16:11:47  5001588c1568d08c0178d8049201009a01020801
  = {10: 1, 11: 2700, 13: 18000, 15: 600, 18: '', 19: {1: 1}}
```

Counters at known moments: field 10 read 1 at 15:14:27 (one second after the status went to
`{1: 14, 12: 6}`), 545 at 15:23:31, 637 at 15:25:03, 719 at 15:26:25: it counted on through the mop
drying of 15:23 to 15:25. Field 8 read 1 at 15:23:33 and 15:31:52 and 441 at 15:41:45, when the
robot was being recalled after the manual drive (the drive began about 15:38:30).

## 11. Consumable reset and volume (2026-11-16, 2026-11-13)

"Replaced (timer reset)" on the part "Replaceable insert bin" in "Accessory Management"; the app
then said "Reset successfully":

```
22:02:25  consumable/reset_consumable_info  (5 bytes)
0a03120118
  = {1: {2: '18'}}
22:02:26  consumable/reset_consumable_info/response  (2 bytes)
0801
  = {1: 1}
  body = {1: {2: [24]}}   (0x18 = 24, a packed list)
22:02:26  consumable/get_consumable_info  (0 bytes)
(empty body)
22:02:26  consumable/get_consumable_info/response  (2 bytes)
0a00
  = {1: ''}
```

Volume slider in the app, 2026-11-13 (the first three of 14 `config/set {1: n}` that day: 12
between 17:00:16 and 17:02:03 and two at 17:07; two more on 2026-11-14. `config/volume/set` was
subscribed and never seen on this unit, on any day):

```
17:00:16  config/set  (2 bytes)
0859
  = {1: 89}
17:00:20  config/set  (2 bytes)
0864
  = {1: 100}
17:00:36  config/set  (2 bytes)
083a
  = {1: 58}
17:00:17  config/set/response  (2 bytes)
0801
  = {1: 1}
```

## 12. The vacuum-only job of 2026-11-16 over the local socket

The capture behind the "confirmed over the local socket" passage already in `PROTOCOL.md` §11.
Local poll, every change:

```
local 18:07:35  field 3 = 08011806         {1: 1, 3: 6}                 field 11 = 2   field 1 empty
local 18:07:50  field 3 = 08022008         {1: 2, 4: 8}                 field 11 = 2   field 1 empty
local 18:07:55  field 3 = 0802200c         {1: 2, 4: 12}                field 11 = 2   field 1 empty
local 18:08:10  field 3 = 08022007         {1: 2, 4: 7}                 field 11 = 2   field 1 empty
local 18:08:15  field 3 = 08022007         {1: 2, 4: 7}                 field 11 = 1   field 1 empty
local 18:08:21  field 3 = 08022003         {1: 2, 4: 3}                 field 11 = 1   field 1 empty
local 18:09:25  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 1   field 1 empty
local 18:09:45  field 3 = 08022006         {1: 2, 4: 6}                 field 11 = 2   field 1 empty
local 18:09:50  field 3 = 0813900104       {1: 19, 18: 4}               field 11 = 2   field 1 empty
local 18:09:55  field 3 = 080e6006         {1: 14, 12: 6}               field 11 = 2   field 1 empty
```
