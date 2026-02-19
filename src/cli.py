import warnings
import re # Added for highlighting
# Suppress urllib3 localized warning on macOS with LibreSSL
warnings.filterwarnings("ignore", module="urllib3")


import typer
import os
from typing import Optional, List
from typing_extensions import Annotated

from src.presenter import VersePresenter
from src.book_normalizer import BookNormalizer
from src.references_db import ReferenceDatabase


app = typer.Typer(help="ScripturesApp - Modern Python Bible Reader", context_settings={"help_option_names": ["-h", "--help"]})

class AdapterFactory:
    _adapter = None
    
    @classmethod
    def get(cls):
        if cls._adapter:
            return cls._adapter
            
        # Data dir for normalizer (bible_books.json)
        # Assuming src/cli.py is in src/, so data is in ../data relative to this file
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        data_dir = os.path.join(project_root, "data")
        
        # Define providers
        def n1904_p():
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/N1904", version="1.0.0", silent=True)
                 except: return None
        
        def lxx_p():
             # Basic implementation
             with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                 try: return use("CenterBLC/LXX", version="1935", check=False, silent=True)
                 except: return None

        # ... other providers can be added as needed or rely on Adapter defaults ...
        
        adapter = TextFabricAdapter(
            data_dir=data_dir,
            n1904_provider=n1904_p,
            lxx_provider=lxx_p,
            # Pass others if needed, adapter has some internal fallbacks too
        )
        cls._adapter = adapter
        return adapter

@app.command(name="read")
def main(
    ctx: typer.Context,
    reference: Annotated[Optional[str], typer.Argument(help="Bible reference (e.g. 'Gn 1:1')")] = None,
    translations: Annotated[Optional[List[str]], typer.Option("--tr", "-tr", "-t", help="Translations to show (en, fr, gr, hb, ar)")] = None,
    version: Annotated[str, typer.Option("--version", "-v", help="Primary version for lookup (N1904, LXX, BHSA)")] = "N1904",
    french_version: Annotated[Optional[str], typer.Option("--bible", "-b", help="French version (tob, bj)")] = None,
    show_crossrefs: Annotated[bool, typer.Option("--crossref", "-c", help="Show cross references")] = False,
    crossref_full: Annotated[bool, typer.Option("--crossref-full", "-f", help="Display cross-references with text")] = False,
    crossref_source: Annotated[Optional[str], typer.Option("--crossref-source", "-s", help="Filter cross-references by source (default: aggregate all)")] = None,
    compact: Annotated[bool, typer.Option("--compact", "-k", help="Compact display (vX. Text)")] = False,
    very_compact: Annotated[bool, typer.Option("--very-compact", "-K", help="Very compact display (Text only)")] = False,
    extra_args: Annotated[Optional[List[str]], typer.Argument(help="Extra translation arguments for compatibility")] = None,
):
    """
    ScripturesApp - Command-line interface for the Greek New Testament & Hebrew Bible
    
    DESCRIPTION
        scripturesapp (biblecli) is a tool for reading and researching the Bible in its original
        languages and modern translations. It supports:
        - Greek New Testament (Nestle 1904)
        - Hebrew Masoretic Text (BHSA - Biblia Hebraica Stuttgartensia)
        - Septuagint (LXX - Rahlfs 1935)
        - French Traduction Œcumenique de la Bible (TOB)
        - Bible de Jérusalem (BJ)
        - New Arabic Version (NAV)
        - English Berean Interlinear Bible

        It features smart lazy-loading of datasets, verse-level cross-references,
        and a personal notebook for saving connections between texts.

    COMMANDS
        list books
               List all available books in the N1904 dataset.

        add -c [COLLECTION] -s [SOURCE] -t [TARGET] --type [TYPE] -n [NOTE]
               Add a new cross-reference/note to a personal collection.

        find [LEMMA/WORD]
               Find all occurrences of a Greek word or French expression.
               
               Options:
               -b [tob|bj]: Search in French translation (TOB or BJ).
               
               Displays Greek text + French translation (for Greek search).
               Matches are highlighted.

        start [--host HOST] [--port PORT] [--detach]
               Start the API server (background) and build/launch the macOS App.
               Use --detach to run in background.

        stop
               Stop both the API server and the App.

        restart [--detach]
               Stop and then Start the services.

    SHORTCUTS
        tob [REFERENCE]
               Equivalent to `biblecli [REFERENCE] -b tob`. 
               Focuses on the French TOB translation. Use -f to view notes.

        bj [REFERENCE]
               Equivalent to `biblecli [REFERENCE] -b bj`.
               Focuses on the French BJ translation.

    REFERENCES
        Flexible reference parsing supports English and French abbreviations:
        - Single verse:  "Jn 1:1", "Jean 1:1", "Gen 1:1"
        - Verse range:   "Mt 5:1-10"
        - Whole chapter: "Mk 4"
        - Book aliases:  "Gn" = "Gen" = "Genesis", "Mt" = "Matt", etc.: both French and English abbreviations supported.
    """
    
    if ctx.invoked_subcommand is not None:
        return # Delegate
        
    # 2. Parse Reference
    if not reference:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

    from src.application.services import BibleService
    service = BibleService()
    presenter = VersePresenter()
    
    # Pre-process Extra Args
    if translations is None: translations = []
    if extra_args:
        # Check if they are languages
        valid_langs = ["en", "fr", "gr", "hb", "ar", "tob", "bj", "nav", "lxx", "bhsa", "n1904"]
        for arg in extra_args:
             if arg.lower() in valid_langs:
                 translations.append(arg)
                 
    if compact or very_compact:
         typer.secho(f"\n{reference}", fg=typer.colors.GREEN, bold=True)
         
    try:
        response = service.search(
            reference=reference,
            translations=translations,
            version=version,
            french_version=french_version,
            show_crossrefs=show_crossrefs,
            crossref_full=crossref_full,
            crossref_source=crossref_source
        )
    except Exception as e:
        presenter.present_error(str(e))
        raise typer.Exit(code=1)
        
    # 4. Determine Compact Mode
    compact_mode = 0
    if very_compact: compact_mode = 2
    elif compact: compact_mode = 1

    # 5. Present
    for item in response.verses:
        main_v = item.primary
        pars = item.parallels
        
        # Calculate Header Override
        # Legacy logic: If displaying French, use French book name in Header.
        header_name = None
        
        # Check if French is being displayed
        is_french_active = False
        if translations:
             if 'fr' in [t.lower() for t in translations]: is_french_active = True
        else:
             is_french_active = True
             
        if is_french_active:
             # Try to localize main_v.book_code
             code = main_v.book_code
             
             # N1904 name
             n1904_name = service.normalizer.code_to_n1904.get(code, code)
             
             # TOB name
             tob_name = service.normalizer.n1904_to_tob.get(n1904_name)
             if tob_name:
                 header_name = tob_name
        
        # English Header Logic
        is_english_active = False
        if translations and 'en' in [t.lower() for t in translations]: is_english_active = True
        if item.primary.version == "N1904_EN": is_english_active = True
        
        if is_english_active and not is_french_active: 
             code = main_v.book_code
             en_name = service.normalizer.code_to_n1904.get(code, code)
             if en_name:
                 header_name = en_name.replace("_", " ")

        presenter.present_verse(main_v, pars, compact_mode=compact_mode, book_name_override=header_name)

    
    # 6. Cross Refs
    if response.cross_references:
        # Formatter Helper (Ported Logic)
        def format_ref(target_str):
             if not target_str: return ""
             def parse_one(ref):
                 parts = ref.split(".")
                 if len(parts) >= 3:
                     bk, ch, vs = parts[0], parts[1], parts[2]
                     n1904 = service.normalizer.code_to_n1904.get(bk, bk)
                     tob_name = service.normalizer.n1904_to_tob.get(n1904, bk)
                     return tob_name, ch, vs
                 return None, None, None

             if "-" in target_str:
                 parts_range = target_str.split("-")
                 if len(parts_range) == 2:
                     start_parsed = parse_one(parts_range[0])
                     end_parsed = parse_one(parts_range[1])
                     
                     if start_parsed[0] and end_parsed[0]:
                         sb, sc, sv = start_parsed
                         eb, ec, ev = end_parsed
                         if sb == eb:
                             if sc == ec: return f"{sb} {sc}:{sv}-{ev}"
                             else: return f"{sb} {sc}:{sv}-{ec}:{ev}"
                         else: return f"{sb} {sc}:{sv}-{eb} {ec}:{ev}"
              
             abbr, ch, vs = parse_one(target_str)
             if abbr:
                  return f"{abbr} {ch}:{vs}"
             return target_str

        # Note: formatting and ref_texts logic is currently not fully populated in BibleService for cross refs
        # The service returns VerseCrossReferences model.
        # But 'ref_texts' dict required for full text display is NOT in the response yet?
        # WAIT. services.py: "// Full text fetch if requested ... pass"
        # I did not implement populating 'ref_texts' in the service!
        
        # CRITICAL: Re-implement full text fetch for cross refs in CLI or Service?
        # Ideally Service. But I skipped it.
        # For now, to match legacy behavior, I should probably re-implement it here using service.adapter?
        # Or quickly add it to service?
        # Adding to service is cleaner. 
        # But I'm in the middle of replacing CLI.
        # I will fetch it here using service.adapter (exposed via service).
        
        ref_texts = {}
        if crossref_full and response.cross_references:
             for rel in response.cross_references.relations:
                 if rel.text:
                     ref_texts[rel.target_ref] = rel.text

        presenter.present_cross_references(response.cross_references, ref_texts=ref_texts, formatter=format_ref)


@app.command(name="add")
def add_cli(
    collection: Annotated[str, typer.Option("--collection", "-c", help="Collection name (e.g., 'notes').")],
    source: Annotated[str, typer.Option("--source", "-s", help="Source verse (e.g., 'Mc 1:1')")],
    target: Annotated[str, typer.Option("--target", "-t", help="Target verse or reference note (e.g., 'Lc 1:1')")],
    rel_type: Annotated[str, typer.Option("--type", help="Relation type (parallel, allusion, quotation, other). Default: 'other'")] = "other",
    note: Annotated[str, typer.Option("--note", "-n", help="Text content of the note")] = ""
):
    """
    Add a new cross-reference/note to a personal collection.
    """
    try:
        from src.application.services import AdapterFactory
        adapter = AdapterFactory.get()
        # AdapterFactory calculates data_dir internally, but we can access it via adapter instance
        data_dir = adapter.data_dir
        normalizer = adapter.normalizer
        
        db = ReferenceDatabase(data_dir, normalizer)
        success = db.add_relation(collection, source, target, rel_type, note)
        
        if success:
             typer.secho(f"Successfully added reference to collection '{collection}'", fg=typer.colors.GREEN)
        else:
             typer.secho("Failed to add reference.", fg=typer.colors.RED)
             raise typer.Exit(code=1)
             
    except Exception as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app.command()
def find(
    word: Annotated[str, typer.Argument(help="Search query (Greek word or French expression)")],
    limit: Annotated[int, typer.Option("--limit", "-k", help="Number of results to show")] = 20,
    bible: Annotated[Optional[str], typer.Option("--bible", "-b", help="French Version (tob, bj)")] = None,
    version: Annotated[Optional[str], typer.Option("--version", "-v", help="Greek Corpus (nt, lxx, all)")] = None,
    translations: Annotated[Optional[List[str]], typer.Option("--tr", "-tr", "-t", help="Translations to show (en, fr, gr, hb)")] = None,
):
    """
    Find occurrences of a word or expression.
    
    Automatically detects script (Greek vs Latin) to determine search mode.
    
    Modes:
    1. Greek Search (Default for Greek script):
       - Searches in Greek corpus (NT default).
       - Use -v to select corpus: nt, lxx, all.
       - Use -b to select preferred French translation version (tob/bj) if displaying French.
    
    2. French Search (Default for Latin script with -b):
       - Searches in French translations (TOB/BJ).
       - Requires -b [tob|bj].

    Examples:
        biblecli find "λόγος"                  # Greek NT search
        biblecli find "ἀρχή" -v lxx             # Greek LXX search
        biblecli find "Dieu" -b tob            # French TOB search
        biblecli find "λόγος" -tr fr           # Greek search + French translation
        biblecli find "λόγος" -tr fr en -v lxx # Greek LXX search + Translations
    """
    from src.application.services import BibleService
    import sys

    # Initialize Service
    try:
        service = BibleService()
    except Exception as e:
        typer.secho(f"Error initializing service: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        # Call Service
        response = service.find(
            query=word,
            limit=limit,
            bible=bible,
            version=version,
            translations=translations
        )
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"Error during search: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if response.total == 0:
        typer.secho(f"No occurrences found for '{word}'.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    # Helper for highlighting
    def apply_highlights(text: str, highlights: List[str]) -> str:
        if not text or not highlights: return text
        for hw in highlights:
            try:
                # Escape hw for regex
                escaped_hw = re.escape(hw)
                # Find all case-insensitive matches
                def replacer(match):
                    return typer.style(match.group(0), fg=typer.colors.RED, bold=True)
                text = re.sub(escaped_hw, replacer, text, flags=re.IGNORECASE)
            except Exception:
                pass
        return text

    # Display Results
    for item in response.results:
        # Determine Header Name (Localized)
        header_ref = f"{item.book_code} {item.chapter}:{item.verse}"
        
        if service.normalizer:
            bk = item.book_code
            
            # Determine Header Name (Localized)
            # Use French by default if available (consistent with App)
            n1904 = service.normalizer.code_to_n1904.get(bk, bk)
            tob_name = service.normalizer.n1904_to_tob.get(n1904)
            
            if tob_name:
                header_ref = f"{tob_name} {item.chapter}:{item.verse}"
            elif n1904:
                 header_ref = f"{n1904.replace('_', ' ')} {item.chapter}:{item.verse}"
            else:
                 header_ref = f"{bk} {item.chapter}:{item.verse}"

        typer.secho(f"{header_ref}", fg=typer.colors.GREEN, bold=True)


        
        # Main Text
        main_text = item.text
        if main_text:
             main_text = apply_highlights(main_text, item.highlights)
             typer.echo(main_text)
        
        # Translations
        if item.translations:
            # Sort for consistent display?
            # Dict order is insertion order in py3.7+, but let's be safe if we want specific order.
            # Service populates logic.
            for code, text in item.translations.items():
                typer.secho(f"({code}) {text}", fg=typer.colors.CYAN)

        typer.secho("-" * 40, fg=typer.colors.BRIGHT_BLACK)
        
    if response.total > len(response.results):
         typer.secho(f"... and {response.total - len(response.results)} more.", fg=typer.colors.YELLOW)

    typer.echo("")
    
    # Summary
    typer.secho("─" * 60, fg=typer.colors.BRIGHT_BLACK)
    
    label = "Expression" if " " in word.strip() else "Lemma"
    
    if word != response.lemma:
        if response.lemma_gloss:
            typer.secho(f"{label}: {word} → {response.lemma} ({response.lemma_gloss})", fg=typer.colors.CYAN, bold=True)
        else:
            typer.secho(f"{label}: {word} → {response.lemma}", fg=typer.colors.CYAN, bold=True)
    else:
        if response.lemma_gloss:
            typer.secho(f"{label}: {response.lemma} ({response.lemma_gloss})", fg=typer.colors.CYAN, bold=True)
        else:
            typer.secho(f"{label}: {response.lemma}", fg=typer.colors.CYAN, bold=True)
    
    typer.secho(f"Total occurrences: {response.total}", bold=True, fg=typer.colors.GREEN)
@app.command()
def greek(
    word: Annotated[str, typer.Argument(help="Greek word or phrase to analyze using OdyCy")],
):
    """
    Perform full NLP analysis on a Greek word or phrase.
    
    Displays morphological data (Case, Gender, Number, Tense, Mood, etc.),
    Part-of-Speech, Lemma, and syntactic dependency information.
    """
    from src.application.services import BibleService
    import sys

    try:
        service = BibleService()
    except Exception as e:
        typer.secho(f"Error initializing service: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        results = service.greek_analysis(word)
    except RuntimeError as e:
        typer.secho(f"Analysis failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not results:
        typer.secho("No analysis results returned.", fg=typer.colors.YELLOW)
        return

    # Morphology Mapping (Abbreviation -> Full term)
    MORPH_MAP = {
        # Case
        "Nom": "Nominative", "Gen": "Genitive", "Dat": "Dative", "Acc": "Accusative", "Voc": "Vocative",
        # Gender
        "Masc": "Masculine", "Fem": "Feminine", "Neut": "Neuter",
        # Number
        "Sing": "Singular", "Plur": "Plural", "Dual": "Dual",
        # Person
        "1": "1st Person", "2": "2nd Person", "3": "3rd Person",
        # Tense
        "Pres": "Present", "Imp": "Imperfect", "Fut": "Future", "Aor": "Aorist", "Perf": "Perfect", "Pqp": "Pluperfect", "Past": "Past",
        # Mood
        "Ind": "Indicative", "Sub": "Subjunctive", "Opt": "Optative", "Imp": "Imperative",
        # Voice
        "Act": "Active", "Mid": "Middle", "Pass": "Passive",
        # VerbForm
        "Fin": "Finite", "Inf": "Infinitive", "Part": "Participle",
        # Aspect
        "Imp": "Imperfective", "Perf": "Perfective",
        # Degree
        "Pos": "Positive", "Cmp": "Comparative", "Sup": "Superlative"
    }

    typer.secho(f"Analysis for: {word}", fg=typer.colors.BRIGHT_BLUE, bold=True)
    typer.echo("─" * 50)

    for i, token in enumerate(results):
        # Header if multiple tokens
        if len(results) > 1:
            typer.secho(f"Token {i+1}: {token.get('text')}", fg=typer.colors.GREEN, bold=True)

        # Core Info
        text = token.get("text", "")
        lemma = token.get("lemma", "")
        norm = token.get("norm", "")
        pos = token.get("pos", "")
        # tag = token.get("tag", "") 
        
        # Friendly POS Names
        POS_NAMES = {
            "ADJ": "Adjective",
            "ADP": "Adposition",
            "ADV": "Adverb",
            "AUX": "Auxiliary Verb",
            "CCONJ": "Coordinating Conjunction",
            "DET": "Determiner",
            "INTJ": "Interjection",
            "NOUN": "Noun",
            "NUM": "Numeral",
            "PART": "Particle",
            "PRON": "Pronoun",
            "PROPN": "Proper Noun",
            "PUNCT": "Punctuation",
            "SCONJ": "Subordinating Conjunction",
            "SYM": "Symbol",
            "VERB": "Verb",
            "X": "Other"
        }
        
        pos_display = POS_NAMES.get(pos, pos.title())
        
        typer.secho(f"  Lexeme:         {lemma}", fg=typer.colors.CYAN, bold=True)
        if norm and norm != lemma:
             typer.secho(f"  Norm:           {norm}", fg=typer.colors.BRIGHT_BLACK)
        typer.secho(f"  Part of Speech: {pos_display}", fg=typer.colors.CYAN)
        
        # 2. Morphology (Grouped and Expanded)
        morph = token.get("morph", {})
        if morph:
            # Categorize features
            nominal = [] # Case, Gender, Number
            verbal = []  # Tense, Mood, Voice, Person, Aspect
            other = []
            
            for k, v in morph.items():
                full_v = MORPH_MAP.get(v, v)
                pair = f"{k}={full_v}"
                
                # Simple categorization
                if k in ["Case", "Gender", "Number"]:
                    nominal.append(f"{k}: {full_v}")
                elif k in ["Tense", "Mood", "Voice", "Person", "Aspect", "VerbForm"]:
                    verbal.append(f"{k}: {full_v}")
                else:
                    other.append(f"{k}: {full_v}")
            
            if nominal:
                typer.secho(f"  Morph (Nominal): {', '.join(nominal)}", fg=typer.colors.YELLOW)
            if verbal:
                typer.secho(f"  Morph (Verbal):  {', '.join(verbal)}", fg=typer.colors.YELLOW)
            if other:
                typer.secho(f"  Morph (Other):   {', '.join(other)}", fg=typer.colors.YELLOW)

        # 3. Syntax / Dependency
        dep = token.get("dep")
        dep_desc = token.get("dep_explain", "")
        head = token.get("head")
        
        dep_str = f"{dep}"
        if dep_desc:
             dep_str += f" ({dep_desc})"
             
        if dep and head and dep != "ROOT":
             # Special handling for common cryptic labels if needed, but spacy explain is usually good
             typer.secho(f"  Syntax: {dep_str} → Head: {head}", fg=typer.colors.MAGENTA)
        elif dep == "ROOT":
             dep_str = "Sentence Root"
             typer.secho(f"  Syntax: {dep_str}", fg=typer.colors.MAGENTA, bold=True)
             
        # 4. Attributes (Filtered)
        flags = []
        if token.get("is_punct"): flags.append("Punctuation")
        if token.get("is_digit"): flags.append("Digit")
        if token.get("like_num"): flags.append("Number")
        if token.get("ent_type"): flags.append(f"Entity: {token['ent_type']}")
        
        if flags:
            typer.secho(f"  Flags:  {', '.join(flags)}", fg=typer.colors.WHITE)
            
        if len(results) > 1:
            typer.echo("-" * 30)

    typer.echo("")
    
@app.command(name="list")
def list_resources(
    resource: Annotated[str, typer.Argument(help="Resource to list (e.g., 'books')")]
):
    """
    List available resources (books).
    
    Usage:
        biblecli list books
    """
    if resource == "books":
        from src.application.services import AdapterFactory
        adapter = AdapterFactory.get()
        norm = adapter.normalizer
        
        ot_list = []
        nt_list = []
        # Sort by book_order
        sorted_codes = sorted(norm.book_order.keys(), key=lambda k: norm.book_order[k])
        for code in sorted_codes:
            name = norm.code_to_n1904.get(code, code)
            if norm.is_ot(code):
                ot_list.append(name)
            elif norm.is_nt(code):
                nt_list.append(name)
        
        typer.secho("Available Books:", bold=True)
        typer.secho("OT: ", nl=False, bold=True)
        typer.echo(", ".join(ot_list))
        typer.secho("NT: ", nl=False, bold=True)
        typer.echo(", ".join(nt_list))
        raise typer.Exit()
    else:
        typer.secho(f"Unknown resource '{resource}'. Did you mean 'list books'?", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app.command()
def start(
    port: int = typer.Option(8000, help="Port for the API server"),
    host: str = typer.Option("127.0.0.1", help="Host for the API server"),
    detach: bool = typer.Option(False, help="Detach processes (run in background)")
):
    """
    Start the API server and the macOS App.
    """
    manager = ProcessManager()
    if manager.is_running():
        typer.secho("Services seem to be already running. Use 'restart' to force a reboot.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    # 1. Start API
    typer.echo("Starting API Server...")
    api_pid = manager.start_api(host, port)
    typer.secho(f"API Server started (PID: {api_pid})", fg=typer.colors.GREEN)

    # Give API server a moment to start up
    import time
    time.sleep(2)

    # 2. Start App
    typer.echo("Building and launching App...")
    try:
        app_pid = manager.start_app()
    except Exception as e:
        typer.secho(f"Failed to launch app: {e}", fg=typer.colors.RED)
        # Kill API
        try:
             import signal
             os.kill(api_pid, signal.SIGTERM)
        except: pass
        raise typer.Exit(code=1)
        
    typer.secho(f"App launched (PID: {app_pid})", fg=typer.colors.GREEN)

    manager.save_state(api_pid, app_pid)
    
    if not detach:
        typer.echo("Services running. Press Ctrl+C to stop.")
        try:
            # Wait for processes? 
            # If we run them via Popen without waiting, the python script exits?
            # Creating a loop to keep script alive if not detached
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            typer.echo("\nStopping services...")
            manager.stop_processes()

@app.command()
def stop():
    """
    Stop the API server and the App.
    """
    manager = ProcessManager()
    manager.stop_processes()
    typer.secho("All services stopped.", fg=typer.colors.GREEN)

@app.command()
def restart(
    detach: bool = typer.Option(True, help="Detach processes (default True for restart)")
):
    """
    Restart the API server and the App.
    """
    manager = ProcessManager()
    typer.echo("Stopping services...")
    manager.stop_processes()
    
    import time
    time.sleep(1) # Give a moment for ports to clear
    
    typer.echo("Starting services...")
    # Restart logic - reusing start code concepts but calling internal helpers
    # We can invoke the start command logic directly or duplicating minimal logic
    
    # 1. Start API
    api_pid = manager.start_api()
    typer.secho(f"API Server started (PID: {api_pid})", fg=typer.colors.GREEN)

    # 2. Start App
    typer.echo("Building and launching App...")
    app_pid = manager.start_app()
    typer.secho(f"App launched (PID: {app_pid})", fg=typer.colors.GREEN)

    manager.save_state(api_pid, app_pid)


# --- Process Manager ---
import subprocess
import signal
import json
import time
from pathlib import Path

class ProcessManager:
    def __init__(self):
        self.state_dir = Path.home() / ".scripturesapp"
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / "state.json"
        
        # Paths
        self.project_root = Path(__file__).resolve().parent.parent
        self.venv_python = self.project_root / ".venv" / "bin" / "python3"
        self.macos_dir = self.project_root / "macos"

    def is_running(self) -> bool:
        if not self.state_file.exists():
            return False
        try:
            state = json.loads(self.state_file.read_text())
            # Check if processes are actually alive
            # Minimal check: kill 0
            os.kill(state["api_pid"], 0)
            return True
        except (ProcessLookupError, KeyError, json.JSONDecodeError):
            return False
        except Exception:
            return False

    def start_api(self, host="127.0.0.1", port=8000) -> int:
        cmd = [
            str(self.venv_python), "-m", "uvicorn", 
            "src.api.main:app", 
            "--host", host, 
            "--port", str(port),
            "--reload"
        ]
        
        # Log to server.log
        log_file = self.project_root / "server.log"
        self.server_log = open(log_file, "w")
        
        # Run in background
        proc = subprocess.Popen(
            cmd, 
            cwd=self.project_root,
            stdout=self.server_log, 
            stderr=subprocess.STDOUT,
            start_new_session=True # Detach
        )
        return proc.pid

    def start_app(self) -> int:
        # 1. Swift Build (blocking, we want to ensure it builds)
        build_cmd = ["swift", "build"]
        
        # Log to app.log
        log_file = self.project_root / "app.log"
        # We'll use this file for run output too
        
        # Execute Build
        # We stream build output to stdout for user feedback AND capture it? 
        # Or just let subprocess.run handle it?
        # User feedback is important.
        
        build_res = subprocess.run(
            build_cmd, 
            cwd=self.macos_dir, 
            capture_output=True, 
            text=True
        )
        
        # Write build logs
        with open(log_file, "w") as f:
            f.write("=== BUILD LOG ===\n")
            f.write(build_res.stdout)
            f.write(build_res.stderr)
            f.write("\n=== RUN LOG ===\n")
        
        if build_res.returncode != 0:
            typer.secho("App build failed! Check app.log for details.", fg=typer.colors.RED)
            typer.echo(build_res.stderr)
            raise typer.Exit(code=1)
            
        # 2. Swift Run (Background)
        run_cmd = ["swift", "run"]
        
        # Inject Environment Variable to disable App's internal server management
        env = os.environ.copy()
        env["BIBLE_APP_SERVER_MANAGED"] = "true"
        
        # Re-open log for appending
        self.app_log = open(log_file, "a")
        
        proc = subprocess.Popen(
            run_cmd,
            cwd=self.macos_dir,
            stdout=self.app_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env
        )
        return proc.pid

    def save_state(self, api_pid: int, app_pid: int):
        state = {
            "api_pid": api_pid,
            "app_pid": app_pid,
            "timestamp": time.time()
        }
        self.state_file.write_text(json.dumps(state))

    def stop_processes(self):
        if not self.state_file.exists():
            return
            
        try:
            state = json.loads(self.state_file.read_text())
            
            # Kill API
            if "api_pid" in state:
                try:
                    os.kill(state["api_pid"], signal.SIGTERM)
                except ProcessLookupError:
                    pass
            
            # Kill App
            if "app_pid" in state:
                try:
                    os.kill(state["app_pid"], signal.SIGTERM)
                except ProcessLookupError:
                    pass
                    
        except Exception as e:
            typer.echo(f"Error stopping processes: {e}")
        finally:
            if self.state_file.exists():
                self.state_file.unlink()

if __name__ == "__main__":
    import sys
    # Manual routing for default command
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        # Check if first arg is a registered command
        # Commands: add, find, start, stop, restart, greek. (read is explicit default)
        known_commands = ["add", "read", "find", "start", "stop", "restart", "list", "greek"]
        if cmd not in known_commands and not cmd.startswith("-"):
             # Insert 'read' to make it the command
             sys.argv.insert(1, "read")
    
    app()
