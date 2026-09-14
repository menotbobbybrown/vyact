# Desktop shutdown safety

The main window remains visible. Both Cmd+Q and `install-app-update` call
`performShutdown`. The backend must approve `/api/shutdown/prepare` before
Electron kills its Python process and managed runtimes. Elasticsearch still
uses the existing owned-runtime lifecycle stop. A failed or timed-out check
blocks shutdown; the five-second HTTP deadline is never a kill deadline.

The request carries a per-desktop-session secret and an attempt ID. Admission
and active-operation counting share one thread lock. Approval seals admission;
late HTTP requests and already-running workers cannot enter a protected
mutation. Cancellation reopens admission, and a cancelled attempt cannot later
seal it. The backend PID must match the Electron-owned child. The legacy
`/api/shutdown` endpoint is retained for IDE-backend handoff: it checks active
work and uses Uvicorn's graceful draining, without a forced timeout.

## Boundaries checked in source

| Operation | Handling and reason |
| --- | --- |
| Backup restore | Entire restore is protected: existing files are overwritten and ES records are restored in multiple steps. |
| Document indexing/deletion, memo saving/attachments, conversation saving/deletion | Protected across related file/index updates, including detached `to_thread` work. |
| Code edit/create/patch/undo/move/delete and declared project tasks | Protected across user-file mutations and commands that can write files. |
| Model storage relocation | Protected through copy, config switch, cleanup and rollback; worker protection outlives a disconnected request. The existing atomic config replacement is retained. |
| Plugin installation/removal | Protected through final-directory copy/removal, dependency installation and state updates. |
| Python/runtime/Playwright/eSpeak/UniDic installation and runtime updates | Protected while modifying an installed environment; installer subprocesses retain registration until they exit. A disconnected protected stream continues draining its installer. |
| Desktop Python environment preparation | Electron blocks quit while preparing/updating its venv. |
| Model process transitions | Protect config/spawn/PID publication and runtime stop, not the subsequent health/readiness polling. This prevents a new model process or PID removal racing with termination. |
| GGUF download | `.part` file followed by final replacement; download remains interruptible. |
| MLX snapshot download | Hub-managed download remains interruptible; completion manifest is now written by atomic replacement under the barrier. Association metadata writes are protected. |
| Kokoro cache download | Existing completion marker is cleared before download and created only on success. Remains interruptible; its separate process group/tree is reported for cleanup. |
| ES archive download | Retry overwrites the archive; download remains interruptible. Extraction, config writes and ES process start are protected separately. Persistent ES data lives outside the binary installation directory. |
| Generated artifacts and imported Drive/browser files | Final file writes use a protected temporary-file replacement. |
| Individual ES document writes, cache refreshes and inference | ES commits accepted operations independently; normal ES stop remains responsible for its storage. These are not globally classified as dangerous merely because a request is active. Multi-step local transactions above are explicitly protected. |

Windows managed model roots are verified using CIM, then killed with
`taskkill /T /F`. Unix managed roots are verified using `ps`, then their isolated
process groups are killed. An unexpected non-isolated group blocks termination
rather than leaving its workers behind. Python is killed only after managed
runtime termination has been requested. No user-owned ES process is forcibly
killed by these routines.

New background mutations must enter `protected(reason)` or `guard.operation`
in the actual worker, not just the HTTP handler that schedules it. New plugin
code must also follow this contract for its own persistent writes; arbitrary
third-party plugin background work is not automatically introspected.

## Verification boundary

Automated tests exercise admission races, cancellation, restore registration,
installer and cache-download lifetimes, repeated quit, update quit, timeout
handling and platform termination command construction. They use temporary
files and mocked process commands. They do not prove installed-app behavior or
actual Windows process cleanup. No live user-data restore is part of this test.
