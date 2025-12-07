# Bible CLI Tool

A command-line interface for reading the Bible in Greek (N1904), English, and French (TOB).

## Post-installation

Add gnt to your $PATH in your shell config file (e.g. .zshrc, .bashrc, .bash_profile):
```sh
export PATH=$PATH:[YOUR-PATH-TO]/biblecli/bin
```

## Usage

You can use the `gnt` script to execute commands. It will automatically set up the environment if needed. The project requires Python 3 and the `text-fabric` library.
`gnt` manages the virtual environment and dependencies automatically.


Display a verse
```sh
gnt "Jn 1:1" 

Ἐν ἀρχῇ ἦν ὁ Λεγος, καὶ ὁ Λεγος ἦν πρὸς τὸν Θεον, καὶ Θεος ἦν ὁ Λεγος. 
Au commencement était le Verbe, et le Verbe était tourné vers Dieu, et le Verbe était Dieu.
```

Greek+French is default, but `--tr [fr/gr]` gives you one translation:

```sh
gnt "Marc 1:1-2" --tr fr
gnt "Mk 4" --tr gr
```

Can look up ranges of verses:

```sh
gnt "Mt 5:1-10"
```

Entire chapters:

```sh
gnt "Mt 5"
```

List Books

```bash
gnt list books
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
python3 main.py "Jn 3:16"
```
