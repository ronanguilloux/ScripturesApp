# Bible CLI Tool

A command-line interface for reading Greek (N1904), Hebrew (BHSA), English, and French (TOB) verses.

# In a nutshell

Display a verse from (as default)
- the Masoretic Hebrew (Biblia Hebraica Stuttgartensia),
- plus the Greek *Septuaginta* (LXX),
- plus the French TOB:

```sh
biblecli "Gn 1:1-3" --tr gr hb fr
```

Output:
```
Genèse 1:1
בְּ רֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַ שָּׁמַ֖יִם וְ אֵ֥ת הָ אָֽרֶץ
ἐν ἀρχῇ ἐποίησεν ὁ θεὸς τὸν οὐρανὸν καὶ τὴν γῆν 
Au commencement, Dieu créa le ciel et la terre.

Genèse 1:2
וְ הָ אָ֗רֶץ הָיְתָ֥ה תֹ֨הוּ֙ וָ בֹ֔הוּ וְ חֹ֖שֶׁךְ עַל פְּנֵ֣י תְהֹ֑ום וְ ר֣וּחַ אֱלֹהִ֔ים מְרַחֶ֖פֶת עַל פְּנֵ֥י הַ מָּֽיִם
ἡ δὲ γῆ ἦν ἀόρατος καὶ ἀκατασκεύαστος καὶ σκότος ἐπάνω τῆς ἀβύσσου καὶ πνεῦμα θεοῦ ἐπεφέρετο ἐπάνω τοῦ ὕδατος 
La terre était déserte et vide, et la ténèbre à la surface de l'abîme; le souffle de Dieu planait à la surface des eaux,

Genèse 1:3
וַ יֹּ֥אמֶר אֱלֹהִ֖ים יְהִ֣י אֹ֑ור וַֽ יְהִי אֹֽור
καὶ εἶπεν ὁ θεός γενηθήτω φῶς καὶ ἐγένετο φῶς 
et Dieu dit: «Que la lumière soit!» Et la lumière fut.
```

# Installation

```sh
git clone git@github.com:ronanguilloux/biblecli.git
cd biblecli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bin/biblecli "Mk 1:1" # A simple query to test the installation
```

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

### 2. French TOB Data (Manual Setup, personal copy required)
Due to copyright restrictions, the **Traduction Œcumenique de la Bible (TOB)** text is **not included** and cannot be automatically downloaded.

To add and display the TOB French text, you must:
1.  **Acquire an EPUB version** of the TOB [here](https://e-librairie.leclerc/product/9782853002011_9782853002011_2/la-traduction-oecumenique-de-la-bible-tob-a-notes-essentielles)
2.  **Convert it** to a Text-Fabric compatible format. Unzip the EPUB and use a tool like the native [**TF Converter**](ADD_SOURCES.md) to parse your source text and generate the TF files.
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

### 3. French BJ Data (Manual Setup, personal copy required)
Similar to the TOB, the **Bible de Jérusalem (BJ)** is not included.

To add the BJ text:
1.  **Acquire the EPUB** version of the Bible de Jérusalem [here](https://www.fnac.com/livre-numerique/a7929034/CTAD-LA-BIBLE-DE-JERUSALEM).
2.  **Convert it** using the provided script:
    *   Unzip your EPUB file.
    *   Run `src/convert_bj_epub.py` (you may need to adjust paths in the script).
3.  **Install it locally**:
    *   `mkdir -p ~/text-fabric-data/BJ/1.0`
    *   Copy the generated TF files to this directory.

Structure:
```
~/text-fabric-data/BJ/1.0/
    ├── otype.tf
    ├── ...
```

## Usage

You can use the `biblecli` script to execute commands. It will automatically set up the environment if needed.

For a comprehensive guide, see [MANUAL.md](MANUAL.md) or run `biblecli --help`.

### Basic Commands

Display a New Testament verse from
- Greek New Testament (Nestle 1904),
- and Berean Interlinear Bible (English translation):
```sh
biblecli "Mk 1:1" --tr en gr
```

Output:
```
Mark 1:1
Ἀρχὴ τοῦ εὐαγγελίου Ἰησοῦ Χριστοῦ (Υἱοῦ Θεοῦ). 
[The] beginning of the gospel of Jesus Christ Son of God
```

### Verses, Ranges, Chapters

Display a verse (Greek, French is displayed by default):
```sh
biblecli "Jn 1:1"
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


Use the `-t` or `--tr` option to specify translations. Supported: `en` (Berean Interlinear Bible English translation), `fr` (French TOB by default, or BJ), `gr` (Greek N1904).
When no translation is specified, the default depends on the book (usually Greek/Hebrew + French TOB).
When `-t fr` is used without a source, **TOB** is the default French text. Use `-s bj` to select Bible de Jérusalem. 

Show only English:
```sh
biblecli "Jn 3:16" -t en
```

Show both English, French and ancient Greek:
```sh
biblecli "Jn 3:16" -t en fr gr
```

### Cross-references

The tool supports verse-level cross-references from [OpenBible data](https://www.openbible.info/labs/cross-references/).

Show cross-reference list:
```sh
biblecli "Mc 7:8" -c
```

Output:
```
"Marc 7:8
ἀφέντες τὴν ἐντολὴν τοῦ Θεοῦ κρατεῖτε τὴν παράδοσιν τῶν ἀνθρώπων. 
Vous laissez de côté le commandement de Dieu et vous vous attachez à la tradition des hommes.»

––––––––––
    Other: 
        Is 1:12
        Mc 7:3-4
```

Show cross-references with full verse text:
```sh
biblecli "Mc 7:8" -f
```

Output:
```
Marc 7:8
ἀφέντες τὴν ἐντολὴν τοῦ Θεοῦ κρατεῖτε τὴν παράδοσιν τῶν ἀνθρώπων. 
Vous laissez de côté le commandement de Dieu et vous vous attachez à la tradition des hommes.»

––––––––––
    Other: 
        Is 1:12
            Quand vous venez vous présenter devant moi, qui vous demande de fouler mes parvis?
        Mc 7:3-4
            En effet, les Pharisiens, comme tous les Juifs, ne mangent pas sans s'être lavé soigneusement les mains, par attachement à la tradition des anciens;
            en revenant du marché, ils ne mangent pas sans avoir fait des ablutions; et il y a beaucoup d'autres pratiques traditionnelles auxquelles ils sont attachés: lavages rituels des coupes, des cruches et des plats.
```

Filter cross-references by source (e.g., only TOB notes):
```sh
biblecli "Mk 1:1" -f -s tob
```

Output:
```
Marc 1:1
Ἀρχὴ τοῦ εὐαγγελίου Ἰησοῦ Χριστοῦ (Υἱοῦ Θεοῦ). 
Commencement de l'Evangile de Jésus Christ Fils de Dieu:

––––––––––
    Notes:
        Evangile 1.14 ; 8.35 ; 10.29 ; 13.10 ; 14.9 ; 16.15 ; Rm 1.1 ; 15.19 ; 16.25.–Christ 8.29-30 ; 14.61-62.–Fils de Dieu 1.11 ; 3.11 ; 5.7 ; 9.7 ; 14.61-62 ; 15.39 ; voir Mt 14.33+.

    Parallel: 
        Mc 1:14
            Après que Jean eut été livré, Jésus vint en Galilée. Il proclamait l'Evangile de Dieu et disait:
        Mc 8:35
            En effet, qui veut sauver sa vie...
...
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

For convenience, you can use the `tob` command to quickly access the TOB French translation and notes. It is equivalent to `biblecli ... -s tob`.

```sh
tob "Mc 1:1" # equivalent to `biblecli "Mk 1:1" -s tob` - displays French TOB
```

You can also use the `bj` command for the Bible de Jérusalem:

```sh
bj "Mc 1:1" # equivalent to `biblecli "Mk 1:1" -s bj` - displays French BJ
```

### Abbreviations

Many common abbreviations are supported in both English and French:
- `Gn`, `Gen`, `Genèse`, `Genesis`
- `Mt`, `Matt`, `Matthieu`, `Matthew`
- `Jn`, `Jean`, `John`
- etc.

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

