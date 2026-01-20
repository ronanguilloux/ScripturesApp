# Bible CLI Tool

A command-line interface for reading verses in Greek (N1904 or LXX), Hebrew (BHSA), English (Berean Interlinear Bible), French (TOB or BJ) and Arabic (Ketab al-Nabi).

# In a nutshell

Example: Display a verse with
- the Masoretic Hebrew (Biblia Hebraica Stuttgartensia),
- plus the Greek *Septuaginta* (LXX),
- plus the French TOB:

```sh
biblecli "Gn 1:1-3" --tr gr hb fr -k
```

Output:
```
Genèse 1:1-3
v1. בְּ רֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַ שָּׁמַ֖יִם וְ אֵ֥ת הָ אָֽרֶץ
    ἐν ἀρχῇ ἐποίησεν ὁ θεὸς τὸν οὐρανὸν καὶ τὴν γῆν 
    Commencement de la création par Dieu du ciel et de la terre.
v2. וְ הָ אָ֗רֶץ הָיְתָ֥ה תֹ֨הוּ֙ וָ בֹ֔הוּ וְ חֹ֖שֶׁךְ עַל פְּנֵ֣י תְהֹ֑ום וְ ר֣וּחַ אֱלֹהִ֔ים מְרַחֶ֖פֶת עַל פְּנֵ֥י הַ מָּֽיִם
    ἡ δὲ γῆ ἦν ἀόρατος καὶ ἀκατασκεύαστος καὶ σκότος ἐπάνω τῆς ἀβύσσου καὶ πνεῦμα θεοῦ ἐπεφέρετο ἐπάνω τοῦ ὕδατος 
    La terre était déserte et vide, et la ténèbre à la surface de l'abîme ; le souffle de Dieu planait à la surface des eaux,
v3. וַ יֹּ֥אמֶר אֱלֹהִ֖ים יְהִ֣י אֹ֑ור וַֽ יְהִי אֹֽור
    καὶ εἶπεν ὁ θεός γενηθήτω φῶς καὶ ἐγένετο φῶς 
    et Dieu dit : « Que la lumière soit ! » Et la lumière fut.
```

# Installation

```sh
git clone git@github.com:ronanguilloux/biblecli.git
cd biblecli
make install
bin/biblecli "Mk 1:1" # A simple query to test the installation
```

## Post-installation

Add `biblecli`, `tob` and `bj` to your `$PATH` in your shell config file (e.g. `.zshrc`, `.bashrc`, `.bash_profile`):
```sh
export PATH=$PATH:[YOUR-PATH-TO]/biblecli/bin
```

## Data Setup

### 1. General Bible Data (N1904, LXX, BHSA)

The tool uses the Text-Fabric library to manage Bible datasets.

**Automatic Download**

When you run the tool for the first time with an internet connection, it will automatically download the required datasets ([CenterBLC/N1904](https://github.com/CenterBLC/N1904), [CenterBLC/LXX](https://github.com/CenterBLC/LXX), [ETCBC/bhsa](https://github.com/ETCBC/bhsa)) to your home directory under `~/text-fabric-data`. You can find these datasets in `~/text-fabric-data/github/...`. The expected structure is:


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

To add and display the TOB French text, you must
1. **Acquire an EPUB version** of the TOB [here](https://e-librairie.leclerc/product/9782853002011_9782853002011_2/la-traduction-oecumenique-de-la-bible-tob-a-notes-essentielles)
2. **Follow the instructions** in [ADD_SOURCES.md](ADD_SOURCES.md) and use the `converters/convert_tob_epub.py` script.

### 3. French BJ Data (Manual Setup, personal copy required)
Similar to the TOB, the **Bible de Jérusalem (BJ)** is not included.

To add the BJ text:
1.  **Acquire the EPUB** version of the Bible de Jérusalem [here](https://www.fnac.com/livre-numerique/a7929034/CTAD-LA-BIBLE-DE-JERUSALEM).
2.  **Convert it** using the provided script:
    *   Unzip your EPUB file.
    *   Run `converters/convert_bj_epub.py` (you may need to adjust paths in the script).
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


Use the `-t` or `--tr` option to specify translations. Supported: `en` (Berean Interlinear Bible English translation), `fr` (French TOB by default, or BJ), `gr` (Greek N1904), `ar` (Arabic NAV).
When no translation is specified, the default depends on the book (usually Greek/Hebrew + French TOB).
Use `-b` to select the text version (e.g. `-b bj` for Bible de Jérusalem). Default is TOB. 

Show only English:
```sh
biblecli "Jn 3:16" -t en
```

Show Arabic (NAV):
```sh
biblecli "Gen 1:1" --tr ar
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

For convenience, you can use the `tob` command to quickly access the TOB French translation. It is equivalent to `biblecli ... -b tob`.

```sh
tob "Mc 1:1" # equivalent to `biblecli "Mk 1:1" -b tob` - displays French TOB
```

You can also use the `bj` command for the Bible de Jérusalem:

```sh
bj "Mc 1:1" # equivalent to `biblecli "Mk 1:1" -b bj` - displays French BJ
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
pytest
```

## Lazy Loading Logic

We have implemented the smart OT/NT lazy loading and default behaviors.

Indeed the datasets are loaded in the following order:
- `N1904` (Greek New Testament)
- `LXX` (Greek Ancien Testament)
- `BHSA` (Hebrew Ancien Testament)
- `TOB` (Entire *TOB* Bible in French)
- `BJ` (Entire *Bible de Jérusalem* in French)

The lazy loading logic consists in loading the minimal number of datasets based on the reference:

- Query `Mc 1:1` without flags -> Loads `N1904` and `TOB`. Skips `BHSA`.
- Query `Mc 1:1 --tr fr` -> Loads `N1904` and `TOB`. Skips `BHSA`.
- Query `Mc 1:1 --tr en` -> Loads `N1904` only. Skips `TOB` and `BHSA`.
- Query `Mc 1:1 --tr en fr` -> Loads `N1904` and `TOB`. Skips `BHSA`.

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
| `tob "Mc 1:1"` (Default) | **~4.0s** | Baseline (Python startup + N1904 + TOB) |
| `tob "Mc 1:1" --tr fr` | **~3.7s** | Minimal overhead (Skips BHSA) |
| `tob "Mc 1:1" --tr gr` | **~3.7s** | Minimal overhead (Skips BHSA & TOB) |

### Old Testament (OT)
Measured using reference: **Gn 1:1**

| Command | Time | Notes |
| :--- | :--- | :--- |
| `tob "Gn 1:1"` (Default) | **~6.0s** | **+2.3s vs NT** (Loads LXX + BHSA + TOB) |
| `tob "Gn 1:1" --tr fr` | **~5.8s** | Forces Hebrew display (Loads LXX + BHSA + TOB) |
| `tob "Gn 1:1" --tr hb` | **~5.8s** | Loads LXX + BHSA |
| `tob "Gn 1:1" --tr en fr gr hb` | **~10.9s** | Full load (System overhead) |

**Key Findings:**
- **Baseline**: ~3.7-4.0s startup time for NT.
- **Lazy Loading**: Accessing OT adds ~2s (LXX + BHSA).
- **Hebrew**: For OT queries, Hebrew is displayed by default, incurring the BHSA load cost (`~2s`). For NT queries, it is skipped, saving that time.

## Reference Sources

### OpenBible.info (Cross-References)

The data provided by **OpenBible.info** is indeed a modernized, evolution of the classic **Treasury of Scripture Knowledge (TSK)**, one of the most comprehensive sets of cross references ever compiled

The OpenBible.info site’s creator, Sean Boisen, cleaned and expanded the dataset, blending it with other data. While TSK is often cited as having 500,000 references, the OpenBible creator noted that after extracting the references from available public domain digital copies, he only counted approximately 380,000 unique references, which formed the "seed" for the OpenBible project.

The raw TSK is notoriously "noisy" when converted to machine-readable formats. OpenBible performed several processing steps:

*   **De-duplication**: The original TSK contains many redundant links. OpenBible filtered these to ensure a cleaner mapping.
*   **Merging Adjacent Verses**: In the original TSK, a reference might point to John 1:1, John 1:2, and John 1:3 separately. OpenBible’s cleaning process combined these into ranges or grouped them to make the data more readable for digital interfaces.
*   **Reference Extraction**: The raw TSK often lists references in archaic or inconsistent abbreviations. The creator used regular expressions (regex) and normalize these into a standard `Book Chapter:Verse` format that a computer can reliably parse.