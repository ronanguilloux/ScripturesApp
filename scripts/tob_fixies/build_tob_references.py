"""Convert the per-book TOB note dumps into the runtime cross-reference format.

`data/cross_refs_by_book/tob/*_notes.min.json` holds 20k+ verse notes covering the
whole TOB (deuterocanonicals included) but nothing read it: only Mark had ever been
converted, by hand, from a raw text dump.

This walks all 73 books and reuses `parse_relations_from_content` from
`parse_tob_notes.py` -- the part that actually understands TOB reference notation
(book carried over between refs, reset on em-dash, '+' note markers).

Output mirrors what `src/references_db.py` globs:
    data/references_nt_tob.json
    data/references_ot_tob.json
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from parse_tob_notes import parse_relations_from_content  # noqa: E402
from src.book_normalizer import BookNormalizer  # noqa: E402

SRC_DIR = "data/cross_refs_by_book/tob"

# The dump's filenames use French abbreviations for 11 books; every other filename
# is already the canonical code from data/bible_books.json. Verified bijection.
FILE_CODE_MAP = {
    "1RO": "1KI", "2RO": "2KI", "ABD": "OBA", "AGG": "HAG", "CAN": "SNG",
    "ESD": "EZR", "JUG": "JDG", "OSE": "HOS", "SAG": "WIS", "SOP": "ZEP",
    "ZAC": "ZEC",
}

# 99.6% of verse_ref values are a clean "C.V". The rest are source-parser bleed
# ("6.21 4 M 6.15.") or non-verse anchors ("ch. 1", "(5)"). Take the leading C.V
# when there is one, skip the anchor-only entries.
VERSE_RE = re.compile(r"^(\d+)\.(\d+)")


def build():
    normalizer = BookNormalizer("data")
    canonical = set(json.load(open("data/bible_books.json"))["books"].keys())

    buckets = {"nt": [], "ot": []}
    skipped = 0

    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*_notes.min.json"))):
        raw_code = os.path.basename(path).replace("_notes.min.json", "")
        code = FILE_CODE_MAP.get(raw_code, raw_code)
        if code not in canonical:
            raise SystemExit(
                f"{path}: book code {raw_code!r} -> {code!r} is not in data/bible_books.json. "
                f"Add it to FILE_CODE_MAP."
            )

        # Mirror the scope rule the consumer uses (search.py: 'nt' if is_nt else 'ot'),
        # so deuterocanonicals land in the OT file rather than nowhere.
        bucket = "nt" if normalizer.is_nt(code) else "ot"

        with open(path, encoding="utf-8") as fh:
            chapters = json.load(fh)

        for chapter in chapters:
            for note in chapter.get("notes", []):
                m = VERSE_RE.match(note.get("verse_ref", "") or "")
                if not m:
                    skipped += 1
                    continue
                text = note.get("notes", "") or ""
                relations = parse_relations_from_content(text, code)
                if not relations and not text:
                    continue
                buckets[bucket].append({
                    "source": f"{code}.{m.group(1)}.{m.group(2)}",
                    "notes": text,
                    "relations": relations,
                })

    for scope, entries in buckets.items():
        out = f"data/references_{scope}_tob.json"
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({
                "version": "1.0",
                "description": f"TOB notes and cross-references ({scope.upper()}), "
                               f"generated from {SRC_DIR} by scripts/tob_fixies/build_tob_references.py",
                "cross_references": entries,
            }, fh, indent=1, ensure_ascii=False)
        rels = sum(len(e["relations"]) for e in entries)
        print(f"{out}: {len(entries)} verses, {rels} relations")

    print(f"skipped (non-verse anchors): {skipped}")


if __name__ == "__main__":
    build()
