#!/bin/env python3

import csv
import os
import argparse
from typing import List, Tuple

from oxford import Word, WordNotFound
import genanki
EXAMPLE_COUNT = 5  # Default number of examples per card (configurable)



def extract_id_from_definition_url(definition_url: str) -> str:
    """Return the last path segment used by Oxford as the entry id.

    Example: https://.../definition/english/abandon_1 -> abandon_1
    """
    return definition_url.rstrip("/").split("/")[-1]


def fetch_meaning_and_examples(definition_id: str, example_count: int = EXAMPLE_COUNT) -> Tuple[str, List[str]]:
    """Fetch the first meaning and up to example_count examples for an entry id.

    example_count defaults to EXAMPLE_COUNT (5)."""
    Word.get(definition_id)

    definitions = Word.definitions() or []
    meaning = definitions[0].strip() if definitions else ""

    examples = Word.examples() or []

    # If fewer than desired examples, try to pull extra examples from the full definition structure
    if len(examples) < example_count:
        full = Word.definition_full() or []
        for group in full:
            for d in group.get("definitions", []):
                for ex in d.get("extra_example", []) or []:
                    examples.append(ex)
                    if len(examples) >= example_count:
                        break
                if len(examples) >= example_count:
                    break
            if len(examples) >= example_count:
                break

    if len(examples) < example_count:
        return meaning, examples

    return meaning, examples[:example_count]


def build_back_field(meaning: str, examples: List[str]) -> str:
    """Compose the back field: meaning followed by up to 3 numbered examples."""
    lines: List[str] = []
    if meaning:
        lines.append(meaning)
    if examples:
        lines.append("")  # blank line between meaning and examples
        for ex in examples:
            lines.append(f"- {ex}")
    # Use HTML <br> so Anki renders each item on its own line without CSS
    return "<br>".join(lines) if lines else ""


def build_front_field(word: str, definition_url: str, voice_url: str) -> str:
    """Compose the front field: word name, link, and streaming audio (no packaged media)."""
    parts: List[str] = []
    if word:
        if definition_url:
            parts.append(
                f"<a href=\"{definition_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{word}</a>"
            )
        else:
            parts.append(word)
    if voice_url:
        # Use inline JS to play without <audio>; fallback opens the URL if codec unsupported
        js = (
            "(function(u){try{var t='audio/ogg';var a=document.createElement('audio');"
            "if(!a||!(a.canPlayType&&a.canPlayType(t))) { window.open(u,'_blank'); return; }"
            "var p=new Audio(u); p.play();}catch(e){window.open(u,'_blank');}})('" + voice_url + "')"
        )
        parts.append(f"<button onclick=\"{js}\">🔊 Play</button>")
    return "<br>".join([p for p in parts if p])


    # Removed IPA/media helpers to avoid packaged media. We stream audio directly via <audio>.


def ensure_output_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def main(word_level: str) -> None:
    input_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), "data.csv"))
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "result"))
    ensure_output_dir(output_dir)
    output_tsv = os.path.join(output_dir, "anki.tsv")
    output_apkg = os.path.join(output_dir, f"oxford-5000-words-{word_level}.apkg")
    # No media packaging; audio will stream from voice_url

    total = 0
    success = 0

    # Prepare Anki model and deck
    model = genanki.Model(
        1607392319,
        "WordsBasic",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": "{{Front}}<hr id=\"answer\">{{Back}}",
            }
        ],
        css="",
    )

    deck = genanki.Deck(2059400110, f"Words Deck ({word_level.upper()})")

    with open(input_csv, "r", encoding="utf-8") as f_in, open(
        output_tsv, "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        writer = csv.writer(f_out, delimiter="\t")

        for row in reader:
            total += 1
            word = (row.get("word") or "").strip()
            level = (row.get("level") or "").strip().lower()
            definition_url = (row.get("definition_url") or "").strip()
            voice_url = (row.get("voice_url") or "").strip()

            if level != word_level:
                continue

            if not word or not definition_url:
                continue

            entry_id = extract_id_from_definition_url(definition_url)

            try:
                meaning, examples = fetch_meaning_and_examples(entry_id, EXAMPLE_COUNT)
            except WordNotFound:
                # Skip entries not found
                continue
            except Exception:
                # Network/parse issues: skip and continue
                continue

            back = build_back_field(meaning, examples)
            if not back:
                continue

            writer.writerow([word, back])
            success += 1

            # Prepare front: word + link + streaming audio tag
            front = build_front_field(word, definition_url, voice_url)

            # Add to Anki deck
            note = genanki.Note(model=model, fields=[front, back])
            deck.add_note(note)

    # Write .apkg
    genanki.Package(deck).write_to_file(output_apkg)

    print(f"Wrote {success}/{total} cards to {output_tsv} and {output_apkg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Anki deck from data.csv filtered by level")
    parser.add_argument("--word-level", required=True, type=str.lower, choices=["a1","a2","b1","b2","c1"], help="Word level to include")
    args = parser.parse_args()
    main(word_level=args.word_level)


