# Bible CLI Tool

A command-line interface for reading Greek (N1904), Hebrew (BHSA), English, and French (TOB) verses.

## Post-installation

Add `biblecli` to your `$PATH` in your shell config file (e.g. `.zshrc`, `.bashrc`, `.bash_profile`):
```sh
export PATH=$PATH:[YOUR-PATH-TO]/biblecli/bin
```

## Data Setup

### 1. General Bible Data (N1904, LXX, BHSA)
The tool uses the Text-Fabric library to manage Bible datasets.
- **Automatic Download**: When you run the tool for the first time with an internet connection, it will automatically download the required datasets ([CenterBLC/N1904](https://github.com/CenterBLC/N1904), [CenterBLC/LXX](https://github.com/CenterBLC/LXX), [ETCBC/bhsa](https://github.com/ETCBC/bhsa)) to your home directory under `~/text-fabric-data`.
- **Location**: You can find these datasets in `~/text-fabric-data/github/...`. The expected structure is:

```
~/text-fabric-data/
└── github/
    ├── CenterBLC/
    │   ├── N1904/tf/[version]/   # Greek New Testament
    │   └── LXX/tf/[version]/     # Septuagint
    └── ETCBC/
        └── bhsa/tf/[version]/    # Hebrew Masoretic Text
```

### 2. French TOB Data (Manual Setup and  Required)
Due to copyright restrictions, the **Traduction Œcumenique de la Bible (TOB)** text is **not included** and cannot be automatically downloaded.

To view French text, you must:
1.  **Acquire a personal copy** of the TOB (e.g., from a personal PDF or e-book).
2.  **Convert it** to a Text-Fabric compatible format. Extract text using Python libraries like `PyPDF` or `BeautifulSoup`. Use a tool like **TF Fabricator** to parse your source text and generate the TF files.
3.  **Install it locally**:
    -   Create a directory: `mkdir -p ~/text-fabric-data/TOB/1.0`
    -   Place your generated TF files (e.g., `otype.tf`, `book.tf`, `chapter.tf`, `verse.tf`, `text.tf`, etc.) into this directory.

The expected structure is:
```
~/text-fabric-data/TOB/1.0/
    ├── otype.tf
    ├── book.tf
    ├── chapter.tf
    ├── verse.tf
    ├── text.tf
    └── ...
```

## Usage

You can use the `biblecli` script to execute commands. It will automatically set up the environment if needed.

### Basic Commands

Display a verse (Greek and French are default):
```sh
biblecli "Jn 1:1"
```

Display a New Testament verse from (as default)
- Greek New Testament (Nestle 1904),
- and French TOB:
```sh
biblecli "Mc 1:1"
```
Output:
```
Marc 1:1
Ἀρχὴ τοῦ εὐαγγελίου Ἰησοῦ Χριστοῦ (Υἱοῦ Θεοῦ). 
Commencement de l'Evangile de Jésus Christ Fils de Dieu:
```

Display an Old Testament verse from (as default)
- the Masoretic Hebrew (Biblia Hebraica Stuttgartensia),
- the Greek Old testament (Septuaginta, 'LXX'),
- and French TOB:
```sh
biblecli "Gn 1:1"
```
Output:
```
Genèse 1:1
בְּ רֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַ שָּׁמַ֖יִם וְ אֵ֥ת הָ אָֽרֶץ
ἐν ἀρχῇ ἐποίησεν ὁ θεὸς τὸν οὐρανὸν καὶ τὴν γῆν 
Au commencement, Dieu créa le ciel et la terre.
```

Display a verse range:
```sh
biblecli "Mt 5:1-10"
```

Display an entire chapter:
```sh
biblecli "Mt 5"
```

List all available books:
```sh
biblecli list books
```

### Translations

Use the `-t` or `--tr` option to specify translations. Supported: `en` (English), `fr` (French TOB), `gr` (Greek N1904).

Show only English:
```sh
biblecli "Jn 3:16" -t en
```

Show both English, French and ancient Greek:
```sh
biblecli "Jn 3:16" -t en fr gr
```

### Cross-references

The tool supports verse-level cross-references from OpenBible data.

Show cross-reference list:
```sh
biblecli "Jn 1:1" -c
```

Show cross-references with full verse text:
```sh
biblecli "Jn 1:1" -f
```

Filter cross-references by source (e.g., only TOB notes):
```sh
biblecli "Mk 1:1" -f -s tob
```

### Adding Personal References

You can add your own cross-references and notes to a personal collection (stored as a JSON file in `data/`).

Command syntax:
```sh
biblecli add -c [COLLECTION_NAME] -s [SOURCE_REF] -t [TARGET_REF] --type [TYPE] -n [NOTE]
```

**Parameters:**
- `-c, --collection`: Name of your collection (e.g., `my_notes`). The file will be named `references_nt_[collection].json`.
- `-s, --source`: The source verse (e.g., "Jn 1:1").
- `-t, --target`: The target verse or note reference (e.g., "Gn 1:1").
- `--type`: Type of relation `(parallel, allusion, quotation, other)`. Default is `other`.
- `-n, --note`: Your personal note or comment.

**Example:**
Add a connection between John 1:1 and Genesis 1:1 with a note:
```sh
biblecli add -c personal -s "Jn 1:1" -t "Gn 1:1" --type parallel -n "Echoes of creation"
```

This will automatically create/update `data/references_nt_personal.json`.

### Shortcuts

For convenience, you can use the `tob` command to quickly access the TOB French translation and notes. It is equivalent to `biblecli ... -f -s tob`.

```sh
tob "Mk 1:1"
```

### Abbreviations

Many common abbreviations are supported in both English and French:
- `Gn`, `Gen`, `Genèse`, `Genesis`
- `Mt`, `Matt`, `Matthieu`, `Matthew`
- `Jn`, `Jean`, `John`
- etc.

## Manual Setup

If you prefer to run `src/main.py` directly, you must install the dependencies:

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

## Development

### Testing

This project uses `pytest` for unit testing. To run the tests, first ensure you have installed the dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
```bash
pytest
```

## Lazy Loading Logic

Optimization Complete!

I have implemented the smart OT/NT lazy loading and default behaviors.

### Key Achievements

**Smart Defaults**: `tob "Gn 1:1"` now automatically displays Hebrew, Greek (LXX), and French. `tob "Mc 1:1"` displays Greek (N1904) and French, effectively skipping the Hebrew load.

**Selective Loading**:
*   **NT Queries**: `N1904` + `TOB` are loaded. `BHSA` and `LXX` are skipped.
*   **OT Queries**: `LXX` + `BHSA` + `TOB` are loaded. `N1904` is skipped.

**Performance Improvement (User CPU)**:
*   `Mc 1:1`: **2.36s** (down from 3.71s, **36% faster**).
*   `Gn 1:1`: **5.87s** (down from 8.26s, **29% faster**).

## Performance

The following tables compare the execution duration for different translation options (measured on M-series Mac).

### New Testament (NT)
Measured using reference: **Mc 1:1**

| Command | Time | Notes |
| :--- | :--- | :--- |
| `tob "Mc 1:1"` (Default) | **~3.7s** | Baseline (Python startup + N1904 load) |
| `tob "Mc 1:1" --tr fr` | **~3.7s** | Minimal overhead (Lazy loading) |
| `tob "Mc 1:1" --tr gr` | **~3.7s** | Minimal overhead |

### Old Testament (OT)
Measured using reference: **Gn 1:1**

| Command | Time | Notes |
| :--- | :--- | :--- |
| `tob "Gn 1:1"` (Default) | **~4.0s** | **+0.3s vs NT** (Lazy loads LXX dataset) |
| `tob "Gn 1:1" --tr fr` | **~4.0s** | Same as Default |
| `tob "Gn 1:1" --tr hb` | **~9.7s** | **+5.7s overhead** (Loads BHSA dataset) |
| `tob "Gn 1:1" --tr en fr gr hb` | **~9.4s** | **+5.4s overhead** |

**Key Findings:**
- **Baseline**: ~3.7s startup time.
- **Lazy Loading**: Accessing French or Greek (NT) adds negligible overhead. Accessing OT adds ~0.3s for LXX.
- **Hebrew Cost**: Accessing Hebrew (`--tr hb`) consistently adds ~6s to load the `ETCBC/bhsa` dataset.

