"""BJ-style margin references: per-verse grouping, cap, and short labels.

The Bible de Jerusalem prints a verse's cross-references in the outer margin,
level with the line the verse starts on. Reproducing that needs two things the
API did not provide: references attached to THEIR verse (they used to be
flattened into one bag for the whole passage), and a short label that drops the
book name the way the BJ does.
"""
import json
import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.application.use_cases.search import SearchBibleUseCase
from src.book_normalizer import BookNormalizer
from src.domain.models import (CrossReferenceRelation, CrossReferenceType,
                               Language, Verse)
from src.references_db import ReferenceDatabase


@pytest.fixture(scope="module")
def normalizer():
    return BookNormalizer("data")


def _labels(use_case, targets, current_book, notes=None):
    notes = notes or {}
    rels = [
        CrossReferenceRelation(
            target_ref=t,
            rel_type=CrossReferenceType.PARALLEL,
            target_ref_localized=use_case._localize_ref(t),
            note=notes.get(t, ""),
        )
        for t in targets
    ]
    return [r.target_ref_margin for r in use_case._margin_labels(rels, current_book)]


@pytest.fixture(scope="module")
def use_case(normalizer):
    return SearchBibleUseCase(None, ReferenceDatabase("data", normalizer), normalizer)


# --- the label convention -------------------------------------------------

def test_book_is_abbreviated_not_spelled_out(use_case):
    """_localize_ref spells 'Joel' out; a margin has room only for 'Jl'."""
    assert _labels(use_case, ["JOE.3.1-JOE.3.5"], "ACT") == ["Jl 3:1-5"]


def test_current_book_is_elided(use_case):
    """Reading Acts, a reference to Acts 2:33 prints as '2:33' (BJ: '2 33+')."""
    assert _labels(use_case, ["ACT.2.33"], "ACT") == ["2:33"]


def test_repeated_book_is_elided_but_chapter_kept(use_case):
    """BJ prints 'Rm 7 5+' then '11 27+' -- the book carries over, not the chapter."""
    assert _labels(use_case, ["ROM.7.5", "ROM.11.27"], "ACT") == ["Rm 7:5", "11:27"]


def test_book_returns_when_it_changes(use_case):
    assert _labels(
        use_case, ["ISA.51.4", "ISA.51.7", "ROM.10.13", "ISA.2.2"], "ACT"
    ) == ["Is 51:4", "51:7", "Rm 10:13", "Is 2:2"]


def test_note_marker_is_kept(use_case):
    """TOB/BJ suffix '+' means the reference carries an explanatory note."""
    assert _labels(
        use_case, ["MAT.14.33"], "MRK", notes={"MAT.14.33": "+"}
    ) == ["Mt 14:33+"]


def test_non_canonical_target_passes_through(use_case):
    """A hand-written target in a personal collection has no parsable book."""
    assert _labels(use_case, ["Jn 1:1"], "ACT") == ["Jn 1:1"]


# --- per-verse grouping and cap -------------------------------------------

class _FakeProvider:
    """Just enough provider to expand 'Ac 2:14-18' and hand back verses."""

    def normalize_reference(self, ref):
        ref = ref.replace(".", ":").strip()
        if ref.startswith("Ac "):
            rest = ref[3:]
            chap, _, verse = rest.partition(":")
            return ("ACT", int(chap), int(verse or 0))
        for code in ("ACT", "ISA", "JOE", "ROM", "ZEC"):
            if ref.startswith(code + "."):
                _, c, v = ref.split(".")[:3]
                return (code, int(c), int(v))
        return None

    def get_verse(self, book, chapter, verse, version="N1904"):
        return Verse(book_code=book, chapter=chapter, verse=verse,
                     text=f"texte {book} {chapter}:{verse}",
                     language=Language.FRENCH, version=version)

    def get_chapter(self, book, chapter, version):
        return []


@pytest.fixture
def acts_refs(tmp_path_factory, normalizer):
    """A reference file with a deliberately overloaded verse, like openbible."""
    path = os.path.join("data", "references_nt_marginfixture.json")
    payload = {
        "version": "1.0",
        "cross_references": [
            {"source": "ACT.2.16", "notes": "Jl 3.1-5.",
             "relations": [{"target": "JOE.3.1-JOE.3.5", "type": "parallel", "note": ""}]},
            {"source": "ACT.2.17", "notes": "",
             "relations": [
                 {"target": f"ISA.{n}.1", "type": "parallel", "note": ""}
                 for n in range(2, 14)
             ]},
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    yield
    os.remove(path)


@pytest.fixture
def margin_use_case(normalizer):
    return SearchBibleUseCase(_FakeProvider(), ReferenceDatabase("data", normalizer), normalizer)


def test_references_are_attached_to_their_own_verse(acts_refs, margin_use_case):
    resp = margin_use_case.execute(
        "Ac 2:14-18", translations=["fr"], show_crossrefs=True,
        crossref_source="marginfixture",
    )
    by_verse = {
        item.primary.verse: [r.target_ref for r in item.cross_references.relations]
        if item.cross_references else []
        for item in resp.verses
    }
    assert by_verse[16] == ["JOE.3.1-JOE.3.5"]
    assert by_verse[15] == []
    assert by_verse[18] == []
    assert all(t.startswith("ISA.") for t in by_verse[17])


def test_margin_is_capped_while_the_aggregate_is_not(acts_refs, margin_use_case):
    """BJ shows 2-3 refs per verse; openbible can carry 30+. The bottom block keeps them all."""
    resp = margin_use_case.execute(
        "Ac 2:14-18", translations=["fr"], show_crossrefs=True,
        crossref_source="marginfixture", crossref_max=3,
    )
    v17 = next(i for i in resp.verses if i.primary.verse == 17)
    assert len(v17.cross_references.relations) == 3
    assert len(resp.cross_references.relations) == 13  # 12 Isaiah + 1 Joel


def test_cap_is_configurable(acts_refs, margin_use_case):
    resp = margin_use_case.execute(
        "Ac 2:14-18", translations=["fr"], show_crossrefs=True,
        crossref_source="marginfixture", crossref_max=5,
    )
    v17 = next(i for i in resp.verses if i.primary.verse == 17)
    assert len(v17.cross_references.relations) == 5
