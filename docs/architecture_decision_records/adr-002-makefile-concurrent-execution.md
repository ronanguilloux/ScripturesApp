# ADR 002: Concurrent Execution of GUI and CLI Services via Makefile

## Context

The project requires starting two blocking services for full local development and operation:
1. The macOS application (`swift run`), which launches a GUI but keeps the terminal blocked while running.
2. The `ngrok` tunnel (`ngrok http`), which launches a Terminal UI (TUI) and also blocks the terminal.

Initially, the `make run` target attempted to execute these sequentially:
```makefile
run:
	$(MAKE) macos
	$(MAKE) ngrok
```
Because `make macos` blocks the terminal and never returns the prompt (until the application is closed), `make ngrok` was never reached.

## Decision

We decided to use Make's native parallel job execution feature to run both targets concurrently. The `run` target in the `Makefile` was updated to:

```makefile
run:
	$(MAKE) -j 2 macos ngrok
```

## Consequences

### Positive
- Both the macOS application and the ngrok tunnel launch simultaneously with a single `make run` command.
- We avoid non-standard shell workarounds (like using `&` to background tasks), preserving standard signal propagation (e.g., `SIGINT` from `Ctrl+C` reliably kills the processes).
- Simplifies the developer experience.

### Negative
- Terminal output from the Swift build process (`swift build && swift run`) and the `ngrok` dashboard will interleave in the same session. This can cause the `ngrok` UI to look messy if Swift emits standard output during execution.
