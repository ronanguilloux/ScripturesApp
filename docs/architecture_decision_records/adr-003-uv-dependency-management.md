# ADR 003: Migrate Dependency Management from pip to uv

## Context

The `Makefile` used a circular bootstrap pattern that made `make macos`
fail on a fresh checkout:

```makefile
PYTHON = $(VENV_DIR)/bin/python   # Points inside the venv

setup: clean
    $(PYTHON) -m venv $(VENV_DIR) # Uses venv Python to create itself
```

Because `.venv/bin/python` does not exist before the venv is created,
this call always fails with:

```text
make[1]: .venv/bin/python: No such file or directory
make[1]: *** [setup] Error 1
```

The project also depends on a HuggingFace-hosted spaCy model wheel
(`grc_odycy_joint_sm-any-py3-none-any.whl`) whose filename violates
PEP 427: the version field is the literal string `any` instead of a
digit-prefixed version number.

## Options Considered

### Option A: Fix the circular reference using the system Python

Replace `$(PYTHON) -m venv` with `python3 -m venv`. Simple, but keeps
`pip` as the package manager — slow resolution, and still requires
pinning `pip` below 25.0 to avoid compatibility noise with the
HuggingFace wheel.

**Rejected** because it solves only the bootstrap bug while retaining
the performance and compatibility issues of pip.

### Option B: Migrate to uv (chosen)

`uv` (already installed at `/opt/homebrew/bin/uv`) unifies venv creation
and package installation in a single binary. It has no circular bootstrap
problem: `uv venv .venv` uses its own bundled Python resolver and does
not depend on an already-existing venv.

For the non-conforming HuggingFace wheel, `uv pip install` rejects the
filename at parse time because it enforces PEP 427. The workaround is to
seed the venv with a real pip binary (`uv venv --seed`) and delegate only
that one package to `.venv/bin/pip`, which is lenient about non-standard
version strings.

### Option C: Vendor the wheel locally and rename it

Download the wheel, rename
`grc_odycy_joint_sm-any-py3-none-any.whl` →
`grc_odycy_joint_sm-0.0.1-py3-none-any.whl`, commit it to the
repository, and install from disk. This would let `uv pip install` handle
the full install without pip fallback.

**Rejected** because vendoring a 200 MB+ spaCy model wheel in git is
impractical, and renaming the file while the embedded `METADATA` still
declares version `any` could confuse package introspection tools.

## Decision

Migrate `setup` and `install` targets to `uv`, with a targeted pip
fallback for the non-conforming wheel:

```makefile
UV = uv

setup: clean
    $(UV) venv --seed $(VENV_DIR)

install: setup
    $(UV) pip install -r requirements.txt
    $(VENV_DIR)/bin/pip install --no-deps "grc_odycy_joint_sm @ https://huggingface.co/chcaa/grc_odycy_joint_sm/resolve/main/grc_odycy_joint_sm-any-py3-none-any.whl"
```

The `--seed` flag ensures `.venv/bin/pip` is available; `uv pip install`
handles all conforming packages; the venv pip handles the one
non-conforming wheel.

## Consequences

### Positive

- The circular bootstrap is eliminated: `uv venv` does not depend on
  the venv being created first.
- Dependency resolution for `requirements.txt` is 10–100× faster than
  pip.
- The pip version-pin workaround (`"pip<25.0"`) is no longer needed.
- The venv path and structure are unchanged (`.venv/`), so `test`,
  `macos`, and all other targets need no modification.

### Negative

- `uv` must be installed on the developer's machine. On macOS with
  Homebrew, `brew install uv` suffices. This adds one external tool
  dependency that was not previously documented.
- The HuggingFace wheel install still uses pip (via `--seed`), so the
  speed benefit does not apply to that one package.
- If the upstream wheel is eventually fixed to use a valid version
  string, the pip fallback line can be replaced with a standard
  `$(UV) pip install --no-deps "..."`.
