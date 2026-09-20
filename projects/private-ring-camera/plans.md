# Private Ring-Style Raspberry Pi Camera Plan

This initiative builds a private, local-first camera system using the existing Raspberry Pi 5, Raspberry Pi camera, home Wi-Fi, and Mac. The first complete milestone is deliberately focused: securely sign in from a phone or laptop, watch live video, and review a rolling 24-hour recording history. Person and vehicle detection come immediately afterward.

## Initiative status

- **Roadmap capability:** `P040 Private Ring-style camera`
- **Current phase:** Phases 1–3 running on the home LAN; retention, restart, and phone acceptance remain in progress
- **Target network:** home LAN first; home VPN later
- **Deployment principle:** no router port forwarding and no publicly exposed camera service
- **Hardware upgrade policy:** prove a measured limit before buying a HAT or accelerator

## Decisions locked so far

- [x] Raspberry Pi 5 is the camera and edge-processing device.
- [x] The Pi connects independently to the home Wi-Fi.
- [x] Ethernet may remain available as a recovery and administration path.
- [x] A phone-friendly web app is the first client; no app-store application is required.
- [x] Version 1 includes authentication, live video, recording, and playback.
- [x] The Mac is the authoritative store for a rolling 24-hour archive.
- [x] The Pi keeps a short circular buffer so temporary Mac or network loss does not immediately lose video.
- [x] Initial access is restricted to the home LAN.
- [x] Later remote access uses a home VPN, not camera port forwarding.
- [x] Version 1 records continuously in short segments; motion creates timeline markers rather than deciding whether video exists.
- [x] Record at 1080p, 15 FPS, H.264, approximately 2–3 Mbps; provide a separate 720p live view targeting less than two seconds of delay.
- [x] The Mac display may sleep, but the plugged-in Mac remains awake while providing archive, API, and web services.
- [x] The Pi outage buffer defaults to one hour with a 2 GB hard ceiling; both are configurable, and the oldest local segments are removed first.
- [x] Version 1 has one administrator account; the data model must permit separate household accounts later.
- [x] Store the Mac archive outside Git and iCloud at `~/Library/Application Support/StratiosAI/edge-ai-camera/archive/` by default; allow a configurable external-storage path later.
- [x] Version 1 is video-only; microphone capture, listening, audio recording, and two-way talk are deferred.
- [x] Administrator sessions expire after seven days by default and support manual logout plus a `log out all devices` action.
- [x] Version 1 password recovery requires a local reset command on the Mac; no email or cloud recovery service is used.
- [x] Push notifications are excluded from the core Version 1 gate and begin with person/vehicle detection; V1 shows health in the web app.
- [x] The administrator can manually delete selected recording segments before expiry; deletion requires confirmation and verified removal of media and timeline metadata.
- [x] The administrator can explicitly export a selected time range; recordings are never automatically copied to Photos, iCloud, or another cloud service.
- [x] Prove Version 1 indoors against a controlled test area before aiming through a window or deploying toward a street or driveway.
- [x] The first continuous test scene is a controlled workspace or unused corner that excludes bedrooms, bathrooms, screens, private paperwork, and non-consenting people.
- [x] Person and vehicle detection begin after the Version 1 media path works end to end.

## Definition of Version 1 success

Version 1 is complete only when all of these are demonstrated from a real phone and laptop:

- [ ] Sign in with an authorized household account.
- [ ] Open a live camera view with acceptable delay and stable playback.
- [ ] See camera, Pi, network, and storage health.
- [ ] Browse a timeline covering the available portion of the last 24 hours.
- [ ] Play a selected recording segment.
- [ ] Manually delete a selected segment and verify its media and timeline metadata are gone.
- [ ] Export a selected time range and verify no automatic cloud or Photos copy occurs.
- [ ] Confirm recordings expire automatically after 24 hours.
- [ ] Reboot the Pi and recover without manually restarting the application.
- [ ] Disconnect the Mac temporarily, continue buffering on the Pi, then reconcile after reconnection.
- [x] Confirm an unauthenticated device cannot view the stream or recordings. (Live and segment API requests without a session returned HTTP 401 against the deployed HTTPS service on 2026-09-20.)

Object detection and notifications are intentionally not required to pass this first gate.

## Proposed system boundary

```text
Raspberry Pi Camera
        |
        v
Pi capture service ----> Pi circular outage buffer
        |
        +----> authenticated low-latency live stream
        |
        +----> recording segments ----> Mac rolling 24-hour archive
                                           |
Phone/laptop PWA <---- authenticated API ---+
```

### Raspberry Pi responsibilities

- Capture the camera stream.
- Produce a lower-resolution live stream and appropriately sized recording stream.
- Maintain a one-hour circular buffer with a 2 GB hard ceiling during Mac or network interruption, removing the oldest local segments first.
- Report camera, temperature, disk, stream, and connection health.
- Later run motion filtering and lightweight person/vehicle detection.

### Mac responsibilities

- Store the authoritative rolling 24-hour media archive in the private application-data directory `~/Library/Application Support/StratiosAI/edge-ai-camera/archive/` by default.
- Run the application API, authentication, timeline index, and web UI initially.
- Enforce retention and expose only authenticated media routes.
- Receive buffered segments when the Pi reconnects.
- Remain awake while plugged into power and operating the camera system; display sleep is allowed.
- Permit a configured external-storage path later without changing media identifiers or API behavior.

### Phone and laptop responsibilities

- Use the responsive progressive web application.
- Sign in before accessing live video, recordings, or system status.
- Stay on the home LAN for Version 1; use the approved VPN in a later milestone.

## Repository structure for this initiative

```text
projects/private-ring-camera/
├── plans.md                    # Decisions, phases, gates, and initiative checklist
├── README.md                   # Setup and operator instructions once implementation starts
├── pi/
│   ├── capture/                # Camera capture, stream generation, and segment writing
│   ├── buffer/                 # Bounded outage buffer and reconciliation
│   └── health/                 # Device and camera health reporting
├── server/
│   ├── api/                    # Authentication, live/events/timeline/media endpoints
│   ├── retention/              # Rolling deletion and storage safeguards
│   └── index/                  # Recording/event metadata
├── web/                        # Responsive phone/laptop PWA
├── configs/                    # Safe example configuration; never credentials
├── containers/                 # ARM64 Pi and Mac/server container definitions
├── infra/
│   ├── systemd/                # Pi service units
│   ├── compose/                # Mac/server composition
│   └── vpn/                    # Later VPN guidance; never keys
├── tests/
│   ├── replay/                 # Recorded and synthetic camera inputs
│   ├── integration/            # Pi/server/API/media path tests
│   └── acceptance/             # Phone, retention, outage, restart, and access tests
└── docs/
    ├── architecture.md
    ├── threat-model.md
    ├── privacy.md
    └── runbook.md
```

Create these implementation folders only as their milestone begins; do not add empty scaffolding merely to make the tree look complete.

## Sequential delivery checklist

### Phase 0 — prove the hardware

- [x] Identify the Pi as a Raspberry Pi 5 with 4 GB RAM.
- [x] Install Raspberry Pi OS Lite 64-bit and enable SSH key authentication.
- [x] Connect the Pi to the home Wi-Fi and verify SSH over Wi-Fi.
- [x] Detect the attached camera with `rpicam-hello --list-cameras`.
- [x] Capture a real still image.
- [x] Record and decode a short real video.
- [x] Record camera model, port, resolution, frame rate, temperature, and throttling state.
- [ ] Confirm the physical ribbon-cable orientation during the next hands-on inspection.
- [x] Aim the camera only at the agreed indoor test area during Version 1 development.

**Gate:** a documented command repeatedly captures valid media after a reboot.

### Phase 1 — reliable local media pipeline

- [x] Build the Pi capture service using the supported Raspberry Pi camera stack.
- [ ] Produce a 720p live-view stream suitable for a phone on the LAN with a target delay under two seconds. (Running and rendered at 1280×720; glass-to-glass latency remains to be measured.)
- [x] Record 1080p at 15 FPS using H.264 at approximately 2–3 Mbps.
- [x] Segment recordings into small files so interruption does not corrupt a full day.
- [x] Add a configurable Pi circular buffer defaulting to one hour with a 2 GB hard ceiling.
- [x] Add health and performance telemetry without logging private frames.
- [ ] Run capture under `systemd` with restart limits and useful logs. (Units are staged but disabled because user lingering is not enabled; detached manual services keep the test capture running until an administrator runs `loginctl enable-linger stratiosai`.)

**Gate:** the Pi streams and records for two hours without unbounded memory, disk, or temperature growth.

### Phase 2 — authenticated web application

- [x] Build the Mac-hosted API and responsive PWA.
- [x] Require authentication for the UI, API, live stream, and recordings.
- [x] Use secure session cookies and protect state-changing requests.
- [x] Expire sessions after seven days by default; implement manual logout and administrator revocation of all sessions.
- [x] Provide a local Mac command that resets the administrator password and revokes existing sessions without printing credentials.
- [x] Show live video, connection state, recording state, disk use, and camera health.
- [ ] Do not expose Pi or Mac service ports through the home router.

**Gate:** an authorized phone can view live video, while an unauthenticated browser is denied.

### Phase 3 — rolling 24-hour archive and playback

- [x] Transfer recording segments from Pi to Mac with integrity metadata.
- [x] Index segment start/end times and availability.
- [x] Build a timeline and playback control in the PWA.
- [x] Provide both a table/list and a day-based visual time scrubber with private preview thumbnails.
- [x] Delete expired recordings automatically after 24 hours (enforced at service start and every 15 minutes; configurable for future testing).
- [ ] Support confirmed administrator deletion of selected segments before expiry and verify removal from storage and the timeline index.
- [x] Add disk high-water protection so retention failure cannot fill the Mac.
- [x] Provide explicit selected-time-range export before expiry without automatic Photos or cloud copying.
- [ ] Test time zones, restart recovery, partial files, and clock drift.

**Gate:** a phone can play a chosen time from the last 24 hours and expired content is verifiably removed.

### Phase 4 — outage recovery and Version 1 acceptance

- [ ] Simulate Mac shutdown while Pi capture continues.
- [x] Reconnect and reconcile the buffered segments without duplicates. (A controlled Mac receiver outage retained Pi segments, then uploaded each once after recovery.)
- [ ] Simulate Wi-Fi interruption and recovery.
- [ ] Reboot Pi and Mac in different orders.
- [x] Verify least-privilege file access and authentication failure behavior. (Mac archive/runtime and Pi secrets, buffer, and logs are owner-only; unauthenticated live and segment API requests return HTTP 401.)
- [ ] Complete every Version 1 success check above.

**Gate:** Version 1 is accepted and `P040` may be marked complete for its core Ring-style capability.

### Phase 5 — person and vehicle intelligence

- [ ] Start with motion zones to avoid continuous inference.
- [ ] Benchmark at least two small person/vehicle detectors on the actual Pi.
- [ ] Track objects temporarily to avoid counting the same object in every frame.
- [ ] Add configurable crossing lines and approach/departure direction.
- [ ] Add event thumbnails, clips, class, confidence, zone, and count.
- [ ] Display live boxes and counts without baking overlays into original evidence video.
- [ ] Measure false alerts during daylight, darkness, rain, glare, shadows, and partial occlusion.
- [ ] Retain an `unknown` outcome rather than forcing weak detections into a class.
- [ ] Add deduplicated person/vehicle notifications only after event accuracy is measured.

**Gate:** replay and live tests meet documented counting and alert accuracy targets.

### Phase 6 — notifications and VPN access

- [ ] Add minimal notification metadata with no private thumbnail by default.
- [ ] Link notifications to the authenticated application.
- [ ] Deploy a home VPN and verify phone access away from home.
- [ ] Confirm no camera, API, database, or media port is publicly reachable.
- [ ] Document credential rotation, device loss, and account revocation.

**Gate:** remote viewing works only through the VPN and passes the same authentication tests as LAN access.

### Deferred capabilities

- [ ] One-way listening and synchronized audio recording after adding a compatible microphone and completing consent and privacy testing.
- [ ] Two-way talk after adding a speaker and completing echo and feedback testing.
- [ ] Multiple cameras after one camera is stable.
- [ ] Facial identification only as a separate consent-based biometric initiative.
- [ ] Cloud storage only after an explicit privacy, cost, and threat-model decision.
- [ ] AI HAT or accelerator only after Pi benchmarks prove it is needed.

## Security and privacy requirements

- Keep all media private and local by default.
- Never commit passwords, session secrets, VPN keys, or captured household media.
- Require authentication even on the trusted home LAN.
- Prefer encrypted transport; document any temporary local-development exception.
- Store password verifiers, never plaintext passwords.
- Rate-limit sign-in attempts and log security events without logging credentials.
- Use opaque media identifiers rather than exposing filesystem paths.
- Define privacy masks before outdoor deployment to avoid unnecessary neighboring-property capture.
- Make recording status visible to household members and visitors where appropriate.
- Support verified deletion and explicit export.
- Do not enable facial recognition as an incidental extension of person detection.

## Performance and reliability measurements

Record these for each milestone on the real Pi:

- Capture resolution and frame rate
- Live-view glass-to-glass latency
- Dropped frames and stream reconnect time
- Pi CPU, RAM, temperature, throttling, and disk use
- Mac storage growth per hour and retention deletion rate
- Pi buffer duration at its configured disk limit
- Segment transfer latency and retry count
- Person/vehicle detector latency, precision, recall, and counting error when added

## Remaining decisions for the grill-me interview

- [x] Account model: one Version 1 administrator, with a schema that supports multiple household accounts later.
- [x] Media profile: 1080p/15 FPS H.264 recording at approximately 2–3 Mbps; 720p live view targeting less than two seconds of delay.
- [x] Pi outage buffer: configurable, defaulting to one hour with a 2 GB hard ceiling and oldest-first removal.
- [x] Mac archive: private, outside Git and iCloud, defaulting to `~/Library/Application Support/StratiosAI/edge-ai-camera/archive/`; path configurable later.
- [x] Mac power behavior: display sleep allowed; system remains awake while plugged in and archiving.
- [x] Recording mode: continuous short segments with motion markers on the timeline.
- [x] Initial field-of-view boundary: controlled workspace or unused corner; exclude bedrooms, bathrooms, screens, private paperwork, and non-consenting people.
- [ ] Confirm the physical camera position and privacy mask from a real preview before continuous recording begins.
- [x] Placement sequence: controlled indoor test area first; window, driveway, or outdoor deployment only after Version 1 acceptance.
- [x] Audio boundary: Version 1 is video-only; all audio capabilities are deferred.
- [x] Notification scope: excluded from the core Version 1 gate and introduced with person/vehicle detection.
- [ ] Notification rules and quiet hours for the later detection phase.
- [ ] VPN choice and account recovery policy.
- [ ] Measured acceptance targets for detection and vehicle counting.

## Initiative completion rule

Do not check off `P040` in the root roadmap merely because files or services exist. Check it off only after the Version 1 acceptance gate is demonstrated. Track partial progress using the linked sub-checklist in the roadmap.
