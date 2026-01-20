# Adding a New Translation to an Existing Text-Fabric Project

This document describes the way to add a new translation to an existing Text-Fabric-based project, such as the `biblecli` command.
Typically, to add your personal copy of the 'Bible de Jérusalem' or 'Bible Segond', the Peshita or any other source, you'll follow these steps in order to complete the ancient greek or the ancient hebrew text this current `biblecli` project already depends on.

# How to Add a New Translation

**The principles:**

Adding a translation from paid digital copy of the TOB or BJ consists in transforming the related EPUB to a Text-Fabric compatible format.

The EPUB digital copies of these Bibles you can acquire online are DRM-free, so good to work with - they're not encrypted. 
Use the CLI version of `unzip` as macOS native unzip from the UI won't help.


We provide scripts in the `converters/` directory to convert these unzipped EPUB to a compatible format. These scripts leverage the fact that EPUBs unzipped contents are well structured into books, chapters and verses so that the TF Walker API can parse and transform it into a Text-Fabric compatible format (*[explain me what is that](#tf)*).


The expected input structure, at first, should look like this:
```
./epubs/input/TOB/
    └── tob.epub.zip
./epubs/input/BJ/
    └── bj.epub.zip
./epubs/input/NAV
    └── ar-Aranav-New-Arabic-Ketab-el-hayat.xml
```

The expected input structure, after unzipping, should look like this:

**For TOB:**
```
./epubs/input/TOB/
├── tob.epub.zip
├── mimetype
├── META-INF/
│   └── container.xml
└── OPS/
    ├── css/
    ├── images/
    ├── epb.ncx
    ├── toc.xml
    └── [Book].xml (e.g., Gen.xml, Gen-1.xml...)
```

**For BJ:**
```
./epubs/input/BJ/
├── BJ.epub.zip
├── mimetype
├── META-INF/
│   ├── container.xml
│   └── calibre_bookmarks.txt
└── OEBPS/
    ├── content.opf
    ├── toc.ncx
    ├── Images/
    ├── Styles/
    └── Text/
        └── [Page].xhtml (e.g., PL1.xhtml, Section0001.xhtml...)
```

The expected output structure for all TOB, BJ or NAV once converted should all look like this (TOB example):
```
./epubs/output/TOB/1.0/
    ├── otype.tf
    ├── book.tf
    ├── chapter.tf
    ├── verse.tf
    ├── text.tf
    └── ...
```

> [!TIP for hackers]
> Since you don't need word-level analysis, the converter scripts make the "slot" (the smallest unit) a full **verse**. This simplifies the script significantly as you don't need to split text and manage trailing spaces. Note that Text-Fabric could be used to create a word-level analysis, but it is not required for the `biblecli` command.

## 1. Traduction Œcumenique de la Bible (TOB)

Due to copyright, you must provide your own copy.

1. **Acquire a TOB Bible EPUB version** [here](https://e-librairie.leclerc/product/9782853002011_9782853002011_2/la-traduction-oecumenique-de-la-bible-tob-a-notes-essentielles) as your personal digital copy for private usage.
2. **Rename** the EPUB file so that its extention becomes `.zip` - like: from `tob.epub` to `tob.zip`. These EPUBs are usually DRM-free.
3.  **Unzip** the EPUB archive in the same place. Note that unzippping from macOS using the native right-click tool won't help here. You'll need to use the command line tool `unzip`.
    *  `unzip [EPUB_FILE]`
    *  This extracts all files in the same directory as the ZIP file: `./epubs/input/TOB/`
3.  **Convert**:
    * Run the provided script `converters/convert_tob_epub.py` - The script assumes the unzipping of the EPUB has already created a `epubs/input/TOB/OPS` folder.
    *   The script generates files in: `./epubs/output/TOB/1.0/`
3.  **Install**:
    *   Manually copy, or move, the generated files to their final destination `~/text-fabric-data/TOB/1.0/`.

## 2. Bible de Jérusalem (BJ)

Exact same process, follow all steps as above, with the following differences:

- **Acquire a Bible de Jerusalem EPUB version** [here](https://www.fnac.com/livre-numerique/a7929034/CTAD-LA-BIBLE-DE-JERUSALEM) as your personal digital copy for private usage.
- **Use the proper converter script**: `converters/convert_bj_epub.py`
- **The output directory is** `./epubs/output/BJ/1.0/` and the final destination is `~/text-fabric-data/BJ/1.0/`.

## 3. New Arabic Version (NAV), 'Ketab El Hayat' (كتاب الحياة)

The Arabic Bible®, under NAV Copyright (1988 Biblica), called the New Arabic Version™ (NAV), is commonly known as Ketab El Hayat (كتاب الحياة). It is available for personal use. The copyright holder, Biblica, has made the text [widely available for personal study, reading, and devotion](https://thebible.org/gt/notices/nav.html)

We provide a converter script for the Zefania XML version of it, found on Github.

1.  **Download**: The XML file `ar-Aranav-New-Arabic-Ketab-el-hayat.xml` is [made available online here](https://github.com/kohelet-net-admin/zefania-xml-bibles/tree/master/Bibles/ARA/New%20Arabic%20Version%20(Ketab%20El%20Hayat)).
2.  **Convert**:
    *   Place the XML file in `epubs/input/NAV/`.
    *   Run `python3 converters/convert_nav_xml.py`.
3.  **Install**:
    *   Move the output directory content from `epubs/output/NAV/1.0` into `~/text-fabric-data/NAV/1.0`.

# <a name="tf">Explain me Text-Fabric</a>

Text-Fabric is a specialized Python-based research environment designed specifically for "text-as-data." Unlike a standard text editor or a flat PDF, Text-Fabric treats a corpus—like the Hebrew Bible or the Septuagint—as a richly annotated graph. In this model, every word, phrase, and verse is a unique "node," and every piece of information about those nodes (the Greek lexeme, the morphological case, or the actual text string) is a "feature" tied to it. This allows scholars to perform complex linguistic queries, such as "Find all occurrences of a specific verb in the Septuagint that are translated with a specific noun in a French version."

Adding an additional translation to an existing Text-Fabric project is a powerful way to conduct comparative and intertextual research. Since Text-Fabric datasets for the Bible (like the bhsa or LXX) use a standardized system of "slots" (representing the base units of the text), you can "map" your own translation—like a French JSON file—onto these existing structures. By converting your JSON into a new TF dataset, you essentially create a parallel track that lives alongside the original Hebrew or Greek. This enables you to use Text-Fabric's search and display tools to view the ancient and modern texts side-by-side, perfectly synchronized by their chapter and verse markers.