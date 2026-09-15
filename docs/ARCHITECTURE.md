# Architecture

## Practical split

```text
camera / microphone
        |
        v
Raspberry Pi capture and event filtering
        |
        +--> small local models (motion, lightweight detection, speech trigger)
        |
        +--> selected frame/audio/text --> desktop, LAN server, or cloud model
                                         |
                                         v
                              text or structured response
                                         |
                                         v
                              screen / speaker / local action
```

The Pi is the sensor and edge controller. It should capture media, decide when an event matters, run lightweight inference, and call larger models only when needed. This is more reliable and less expensive than forcing every model onto the Pi.

## Shared boundaries

- `camera`: capture frames and provide metadata without knowing which model consumes them.
- `audio`: record/play audio and later host speech-to-text/text-to-speech adapters.
- `inference`: define local, LAN, and cloud model adapters.
- `telemetry`: record latency, memory, temperature, and errors without retaining private media.
- `apps`: compose those pieces into user-facing experiments.

## Deployment stages

1. Develop with recorded test images on a laptop.
2. Run camera capture on the Pi.
3. Run lightweight inference on the Pi.
4. Add a LAN or cloud model only when the local hardware cannot meet the requirement.
5. Add a `systemd` service after the command-line workflow is proven.

