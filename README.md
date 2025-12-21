# Bible CLI Tool

A command-line interface for reading the Bible in Greek (N1904), English, and French (TOB).

## Post-installation

Add `biblecli` to your `$PATH` in your shell config file (e.g. `.zshrc`, `.bashrc`, `.bash_profile`):
```sh
export PATH=$PATH:[YOUR-PATH-TO]/biblecli/bin
```

## Usage

You can use the `biblecli` script to execute commands. It will automatically set up the environment if needed. The project requires Python 3 and the `text-fabric` library.
`biblecli` manages the virtual environment and dependencies automatically.


Display a verse
```sh
biblecli "Jn 1:1" 

Jean 1:1
Ἐν ἀρχῇ ἦν ὁ Λόγος, καὶ ὁ Λόγος ἦν πρὸς τὸν Θεόν, καὶ Θεὸς ἦν ὁ Λόγος. 
Au commencement était le Verbe, et le Verbe était tourné vers Dieu, et le Verbe était Dieu.
```

Greek+French is default, but `--tr [fr/gr]` gives you one translation:

```sh
biblecli "Marc 1:1-2" --tr fr
biblecli "Mk 4" --tr gr
```

Can look up ranges of verses:

```sh
biblecli "Mt 5:1-10"
```

Entire chapters:

```sh
biblecli "Mt 5"
```

List Books

```bash
biblecli list books
```

## Manual Setup

If you prefer to run `main.py` directly, you must install the dependencies:

```bash
pip install -r requirements.txt
```

Or use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/main.py "Jn 3:16"
```
