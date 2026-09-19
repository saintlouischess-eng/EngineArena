# Hardware display

Open **Hardware display…** below the page heading. Check the measurements to display, use the arrows to order them from left to right, choose the refresh target and temperature unit, then save. **Hide readings** keeps the configuration button accessible. Changes apply to this workspace's data directory and survive restart.

| Group | Choices |
| --- | --- |
| Processor | Average CPU utilization, busiest logical processor, nominal CPU frequency, live fastest-core frequency, CPU temperature when exposed |
| Memory | Used, available and total RAM, RAM percentage, page-file usage |
| Storage/network | Data-drive free space and capacity used, aggregate disk reads/writes, aggregate network receive/send |
| Session | System uptime, worker working-set memory, active tournament games |
| NVIDIA GPU | Utilization, VRAM used/total/percentage, temperature, power draw and limit, graphics/memory clocks, fan percentage |

The default remains CPU load and RAM used. Presets provide starting selections. The configuration shows detected CPU identity and physical/logical counts. Select one GPU by its stable driver UUID, or use the first detected NVIDIA GPU. A missing selected GPU shows unavailable values; it does not silently switch to another adapter.

Measurements use [psutil's documented OS counters](https://psutil.readthedocs.io/stable/) and the installed [NVIDIA System Management Interface](https://docs.nvidia.com/deploy/nvidia-smi/). GPU queries are read-only and run without a console window. Normal monitoring does not change driver configuration, fans, power limits or clocks. CPU temperatures additionally require the explicitly installed driver and session reader described below.

## CPU temperature setup

1. In **Hardware display…**, open **CPU sensor setup…** and use the official signed [PawnIO driver](https://pawnio.eu/). Install it once; Windows requires administrator approval. Keep Windows security protections enabled and use the signed edition.
2. Choose **Enable CPU readings for this session** and approve the Windows prompt for `ArenaSensors.exe`. Only this CPU reader is elevated. Engine Arena and the engines continue with their existing normal permissions.
3. Select **CPU temperature** and/or **Fastest CPU core**, choose temperature sensor and units as needed, then **Save hardware display**. Automatic selection prefers the CPU die/package and uses the hottest package if multiple packages are available. Missing saved sensors show unavailable rather than switching silently.

The reader must be enabled again for each new app session. Sensor selection, display order and units persist. Cancelling permission leaves temperatures unavailable and games continue. **Check sensors again** refreshes detection. Browser-only use can display temperatures after the reader is enabled in the corresponding desktop window.

The CPU reader uses [LibreHardwareMonitor 0.9.6](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/tag/v0.9.6), CPU hardware only. Its session-specific named pipe sends temperature and core-clock JSON to clients, grants the desktop user read access, accepts no commands or file paths, and performs no fan/clock/voltage changes. It samples only when requested, at most once every two seconds. It watches the original desktop process and exits after normal closure or forced termination. It is not installed as a persistent service. Missing drivers, denied permission, unavailable hardware and timeouts have separate messages.

The pinned upstream source and license notices are included in `ThirdParty/LibreHardwareMonitor`. Beta setup includes the unmodified signed PawnIO installer for optional offline installation, plus its source and notices under `ThirdParty/PawnIO`. Portable packages without that optional installer open the official publisher's download page instead.

## Interpretation and availability

- CPU load averages logical processors; busiest-thread load is their maximum. The initial utilization/throughput sample needs a baseline.
- Windows CPU frequency is usually nominal, as documented by psutil, and is labelled accordingly. CPU temperatures come from processor sensors through the bundled LibreHardwareMonitor reader, not generic ACPI zones. Available names depend on the processor; this Threadripper exposes Core (Tctl/Tdie).
- **Fastest CPU core** is the maximum current per-core operating clock reported by LibreHardwareMonitor, converted from MHz to GHz. Hover help identifies the sampled core. Bus clocks, averages and effective-clock averages are excluded. Individual core operating clocks and Windows interval-average speed estimates can differ. This is a sampled reading at the chosen interval, so short boost peaks between samples can be missed. It does not retain a historical maximum or substitute the nominal clock when readings are missing. Initial counter warmup may need a second refresh.
- This GPU provider supports NVIDIA. AMD/Intel GPU sensors and motherboard temperatures/fans/power need additional provider work. NVIDIA fields also depend on the device and driver; unavailable output is retained as missing data.
- GPU power is not whole-computer power. Fan percentage is not RPM. Memory clock is the driver's reported clock, not an invented effective data rate.
- RAM/VRAM capacity uses GiB, worker memory uses MiB, and byte rates use MiB/s. Disk capacity refers to the tournament data drive; disk activity is summed across all disks. Network counters include all reported interfaces, including virtual interfaces where present.
- Worker working set excludes engine and desktop processes. System uptime is time since boot.
- The top strip shows the sample age. Readings become unavailable when stale or disconnected; a valid numeric zero remains zero.

## Execution and validation

Sampling is serialized on one dedicated thread, independent of the UCI event loop and the storage writer. The interface reads cached results. Refresh targets are 2/5/10/30 seconds and may be delayed by sensor execution or UI polling. CPU helper queries have a five-second timeout and GPU queries have a three-second timeout; a failure does not mark the tournament as failed. CPU/GPU queries are skipped when their respective readings are not selected, except for an explicit configuration-panel probe. Shutdown waits for an in-flight sample to finish.

Tests cover parser units and missing data, multiple GPU identities, invalid settings, initial/reset throughput counters, stale/disconnected rendering, driver timeout, caching/no overlapping collection, and results committing while a sensor read is deliberately stalled. Development checks combined actual Threadripper/RTX 5080 sensor polling with real node-only engine games. See [beta validation scope](BETA_VALIDATION.md) for release testing and remaining work. This is not a guarantee of zero monitoring overhead or support for every vendor sensor.
