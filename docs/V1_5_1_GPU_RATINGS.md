# Engine Arena 1.5.1 — GPU ratings

Private installation candidate. Designed by Mark Young; programmed by OpenAI Codex.

Rating Center now identifies GPU configurations by recorded GPU model and count,
computing backend, engine version, network fingerprint and engine settings. CPU
support threads remain part of the configuration and appear in the entry details.
The list can compare CPU and GPU engines together. It does not convert GPU power
into CPU threads or normalize hardware speed.

For example: `Lc0 v0.32.1 · net a1b2c3d4e5f6 · GeForce RTX 5080 ×1 · cuda-fp16`.
The network abbreviation is the start of its SHA-256 fingerprint, not a network
version guessed from a filename. Open the entry for the complete fingerprint,
hardware, backend, supporting threads, history and saved configuration. Text,
CSV and JSON exports include GPU identity; hardware filters also name available
GPUs. CPU-only Lc0 backends retain CPU thread labels.

## Evidence and hardware limits

The engine must report its GPU model. Single GPU backends use that report;
supported explicit CUDA multi-GPU configurations also reconcile distinct device
indices with the saved hardware inventory. Repeated backend instances on the
same device do not increase the GPU count. Composite backend identity is retained
instead of being replaced by the last child's announcement.

Scheduler GPU groups and slots are resource reservations, not a measurement or
selection of physical devices. Available hardware alone does not prove which GPU
an engine used. Unresolved device selections remain **GPU unverified**, separated
from verified entries and scoped to their tournament. Unsupported/ambiguous
multi-GPU configurations remain unverified rather than assigning a guessed count.
Backend and network options still distinguish those configurations. Automatic
hardware inventory currently uses the existing NVIDIA provider; other vendors
require sufficient engine-reported evidence.

## Existing ratings and upgrades

Existing CPU identity keys, results, anchors and thread distinctions remain
unchanged. No automatic import or large database migration runs at startup.

Detectable GPU entries collected before 1.5.1 keep their original IDs, games,
pairing and anchors, and display **legacy GPU configuration unverified**. They
are never silently relabeled as a particular GPU. If tournament history is still
available, **Manage contributions → Import** rebuilds its official contributions
from saved engine evidence, without replaying games or duplicating contributions.
If that evidence is insufficient, the resulting entry remains unverified. Compact
records retained after tournament deletion cannot recover missing observations.

An existing anchor stays pinned to its exact original entry, including a legacy
entry after reimport. Select a verified replacement anchor explicitly if desired.
New engine/network/hardware versions do not inherit measured games or confidence.
GPU predecessor links require matching verified devices, backend and support
threads. Unknown GPU configurations cannot be treated as compatible predecessors.
Old exclusions continue to apply when their GPU history is reimported; resets
and deletions still scrub rotating recovery copies.

Paired estimates require matching configurations in both legs. A GPU change or
unverified configuration in one leg cannot silently become a complete sample for
another configuration. Unpaired games remain individual observations. Official
replacement, diagnostic replay, time categories and Elo/CI/LOS math are unchanged.

Also included: the 1.5.0 stale tournament-selection correction that prevents a
deleted selection from falsely flashing the hardware display as unavailable.

## Installing

Pause and drain active tournaments, close Engine Arena, then run
`EngineArenaSetup-1.5.1-win-x64.exe` over the existing installation. Resume the
existing event after reopening. This update does not change its engines, rules,
openings or completed results. It has not been published on GitHub.

Reference for Lc0 backend syntax:
https://lczero.org/blog/2019/04/backend-configuration/
