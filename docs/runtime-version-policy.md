# Runtime version policy

`app/services/runtime_versions.json` is the release-owned source of truth for llama.cpp, llama-swap and oMLX. Installation never resolves `latest`, invokes a package-manager upgrade, or modifies the user's existing runtime installation. Downloads must match the recorded SHA-256. New installations use isolated version directories; a single atomic manifest change activates the completed installation. Existing directories remain available for rollback. A failed or cancelled installation leaves the active manifest unchanged.

The initial pins are the latest stable upstream releases checked on 2026-09-14: llama.cpp v0.4.0 (the upstream release's `nightly-tag.txt` selects b10809), llama-swap v255, and oMLX v0.6.4. These are **selected installation versions**, not a claim that Vyact has validated them on every supported machine.

## Version changes and user consent

The version shipped in `runtime_versions.json` is the update target. There is no separate approval list or review-record requirement. Change the pin (and its corresponding immutable URLs, checksums and source commit) and ship Vyact. On the next startup, a differing installed version prompts the user to update. Accepting installs that pinned target; declining keeps the current version. Equal versions do not prompt. When the shipped numeric build/release tag is lower, the prompt explicitly asks for a downgrade and shows the installed and target versions. Opaque/unrelated tag formats use a generic version-change prompt. Older runtime directories are retained; they are not automatically deleted or automatically reused. A downgrade installs the target into its own directory and switches the active record only after installation succeeds. This behavior applies to Vyact releases containing this version-management code; it cannot retrofit a previously released app that lacks it. Release QA remains a developer responsibility, not an in-app gate.

Existing local-model users without a managed installation receive a separate initial-migration prompt. Accepting installs the pinned runtime before loading the model. Existing Homebrew/WinGet installations are preserved. Failed installations are retryable and do not overwrite the active installation.

## Platform details and limits

- macOS GGUF: official arm64/x64 binaries and their adjacent libraries remain together.
- Windows x64: official Vulkan distribution, including its CPU backends. ARM64 has no matching upstream llama-swap package in this manifest and is not silently mapped to x64. Actual Windows GPU/driver and runtime prerequisites still require installation QA.
- Linux: packaged builds compile the pinned llama.cpp commit on the existing supported build baseline and bundle the pinned llama-swap version. The build reads the same manifest and includes it with the runtime. When available, the shipped bundle is reused for the exact target version. Download installations also include a checksum-pinned OpenMP library in the private runtime directory; the host package manager is not invoked.
- oMLX: an isolated venv uses the app's Python and the exact upstream wheel. The selected release requires Apple Silicon, macOS 15+, and Python 3.11–3.13. Its Git-based dependencies require Git. The wheel pins some core dependencies, but its complete transitive Python dependency graph is **not locked by this change**. Full dependency reproducibility requires a separately reviewed lock or a bundled environment.

The installer runs `--version` before publishing a runtime. This detects basic launch failures but does not validate model behavior. Automated tests cover checksum rejection, unsafe archive paths, atomic activation and failure/cancellation recovery, and version-change/consent gating. Actual installed-app QA remains a release step.
