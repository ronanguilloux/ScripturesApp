# Adding a New Translation to an Existing Text-Fabric Project

This document describes the way to add a new translation to an existing Text-Fabric-based project, such as the `biblecli` command.
Typically, to add your personal copy of the 'Bible de Jérusalem' or 'Bible Segond', the Peshita or any other source, you'll follow these steps in order to complete the ancient greek or the ancient hebrew text this current `biblecli` project already depends on.

Text-Fabric is a specialized Python-based research environment designed specifically for "text-as-data." Unlike a standard text editor or a flat PDF, Text-Fabric treats a corpus—like the Hebrew Bible or the Septuagint—as a richly annotated graph. In this model, every word, phrase, and verse is a unique "node," and every piece of information about those nodes (the Greek lexeme, the morphological case, or the actual text string) is a "feature" tied to it. This allows scholars to perform complex linguistic queries, such as "Find all occurrences of a specific verb in the Septuagint that are translated with a specific noun in a French version."

Adding an additional translation to an existing Text-Fabric project is a powerful way to conduct comparative and intertextual research. Since Text-Fabric datasets for the Bible (like the bhsa or LXX) use a standardized system of "slots" (representing the base units of the text), you can "map" your own translation—like a French JSON file—onto these existing structures. By converting your JSON into a new TF dataset, you essentially create a parallel track that lives alongside the original Hebrew or Greek. This enables you to use Text-Fabric's search and display tools to view the ancient and modern texts side-by-side, perfectly synchronized by their chapter and verse markers.

How to Create an Additional Text-Fabric Dataset
To transform your JSON file into a formal Text-Fabric dataset, you will use the Walker API. This tool "walks" through your data and builds the necessary nodes for books, chapters, and verses.

1. The Strategy: Slots and Nodes
In Text-Fabric, the smallest unit (the slot) is typically a word. Higher-level structures like verses are simply nodes that "contain" a range of these slots.

2. The Conversion Script Template
This Python script uses tf.convert.walker to ingest your JSON and generate the .tf binary files required for the TF browser and library.

## 1. Prepare your Data Structure

Assume your JSON (`my_bible.json`) looks like this:

```json
{
  "Genesis": {
    "1": {
      "1": "Au commencement, Dieu créa les cieux et la terre.",
      "2": "La terre était informe et vide..."
    }
  }
}
```

If you are importing a JSON, I recommend keeping it simple: it's sufficient to have a structured version of just the text of the verses. Just combining verses into chapters and chapters into books is usually enough. Make the "slot" (the smallest unit) a full **verse** instead of a word if you don't need word-level morphological tagging. This makes your JSON-to-TF script significantly easier to write.

## 2. The Conversion Script

This script uses `tf.convert.walker` to ingest your JSON and generate the `.tf` binary files.

```python
import os
import json
from tf.convert.walker import CV

# 1. SETUP: Point to your JSON and the destination folder
SOURCE_JSON = 'my_bible.json'
# We expand the user path (~) for robustness
TF_OUTPUT_DIR = os.path.expanduser('~/text-fabric-data/my_bible/1.0')

# 2. METADATA: Describe your dataset
slot_type = 'word'
generic_metadata = {
    'title': 'My Custom Bible Translation',
    'language': 'fra',
    'version': '1.0',
    'source': 'Personal Digital Copy',
    'description': 'A Text-Fabric version of my favorite translation.',
}

# 3. OTEXT: The "Contract"
# This tells Text-Fabric how to assemble words into verses and chapters
otext = {
    'fmt:text-orig-full': '{text}{after}', 
    'sectionTypes': 'book,chapter,verse',
    'sectionFeatures': 'title,number,number',
}

# 4. THE DIRECTOR: This function "walks" through your JSON hierarchy
def director(cv):
    with open(SOURCE_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for book_name, chapters in data.items():
        cur_book = cv.node('book')
        cv.feature(cur_book, title=book_name)
        
        for ch_num, verses in chapters.items():
            cur_chap = cv.node('chapter')
            cv.feature(cur_chap, number=int(ch_num))
            
            for v_num, v_text in verses.items():
                cur_verse = cv.node('verse')
                cv.feature(cur_verse, number=int(v_num))
                
                # Split verse string into individual word slots
                words = v_text.split()
                for i, w in enumerate(words):
                    s = cv.slot()
                    # Add a space after every word except the last one
                    cv.feature(s, text=w, after=' ' if i < len(words)-1 else '')
                
                cv.terminate(cur_verse)
            cv.terminate(cur_chap)
        cv.terminate(cur_book)

# 5. EXECUTION
cv = CV()
cv.walk(
    director, 
    slot_type, 
    otext=otext, 
    generic=generic_metadata, 
    outputDir=TF_OUTPUT_DIR
)
```

## 3. Metadata for Features

To make your dataset searchable and readable, you should define what each feature means. In the script above:
- **`text`**: The string of the word.
- **`after`**: The trailing whitespace.
- **`number`**: The chapter or verse number.
- **`title`**: The book name.

## 4. Loading the Dataset

Once the script finishes, you can load your custom dataset alongside others:

```python
from tf.app import use
# Use the local path (locations should point to the parent of the 1.0 folder)
A = use("my_bible", checkout="local", locations="~/text-fabric-data")
```

Alternatively, to load it as pure data (as done in `main.py` for TOB):

```python
from tf.fabric import Fabric
TF = Fabric(locations=["~/text-fabric-data/my_bible/1.0"])
api = TF.load("text title number")
```

## 5. Integrating with `biblecli`

To make your translation available in `biblecli`:
1. Ensure your TF files are in `~/text-fabric-data/my_bible/1.0`.
2. Update the `TOB_DIR` or add a similar configuration in `src/main.py` to point to your new directory.
3. Use the mapping tools in `src/book_normalizer.py` to align your book names with the internal codes.

> [!TIP]
> If you don't need word-level analysis, consider making the "slot" (the smallest unit) a full **verse**. This simplifies the script significantly as you don't need to split text and manage trailing spaces.

# Specific Guides for Supported French Translations

While the above guide is generic, here are specific instructions for the translations explicitly supported by `biblecli`'s logic.

## 1. Traduction Œcumenique de la Bible (TOB)

Due to copyright, you must provide your own copy.

1.  **Acquire**: A personal digital copy (PDF, EPUB, etc.).
2.  **Convert**: You need to extract the text and convert it to TF. You can use the generic strategy above or write a custom parser (Google Antigravity would help).
3.  **Install**:
    *   Target Directory: `~/text-fabric-data/TOB/1.0/`
    *   Required Features: `text` (verse content), `book` (book name), `chapter` (number), `verse` (number).

## 2. Bible de Jérusalem (BJ)

We provide a helper script for the EPUB version of the Bible de Jérusalem (e.g. valid for the standard ebook edition).

1.  **Acquire**: The EPUB version of the Bible de Jérusalem.
2.  **Convert**:
    *   Unzip your EPUB file.
    *   Run the provided script `src/convert_bj_epub.py` (ensure you adjust the input path in the script to match your unzipped EPUB folder).
    *   `python3 src/convert_bj_epub.py`
3.  **Install**:
    *   The script generates files in `output/brand_new_bj/1.0`.
    *   Move these files to `~/text-fabric-data/BJ/1.0/`.

