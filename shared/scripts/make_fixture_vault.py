from __future__ import annotations

import argparse
from pathlib import Path


NOTE_CONTENT: dict[str, str] = {
    "Atomic Notes/202601010101 A clean atomic note explains one durable idea in plain language and keeps the claim small enough to test against examples.md": """---
aliases:
  - clean dae example
tags:
  - atomic-note
---

# Clean DAE note

A clean atomic note explains one durable idea in plain language and keeps the
claim small enough to test against examples.

It is like labeling one jar in a pantry instead of writing a recipe across every
container.

For example, a note about "good atomic note quality" names the quality, shows a
useful contrast, and links to [[Atomic Note Quality]] for review context.

Reference:

- [[Atomic Note Quality]]

Sources:

1. Synthetic fixture handbook, 2026.
""",
    "Atomic Notes/202601010102 Weak DAE note.md": """---
aliases: []
tags:
  - atomic-note
---

# Weak DAE note

This note says atomic notes should be better, but it does not define better or
show a concrete example.
""",
    "Atomic Notes/202601010103 Multi note bundle.md": """---
aliases:
  - bundled atomic note
tags:
  - atomic-note
---

# Capture quality

Bundling several ideas into one note makes review harder because each claim
needs separate links and separate examples.

START
Basic
What problem does a bundled note create?
Back: It mixes several claims so review and linking become unclear.
END

# Review quality

Review quality depends on checking whether each section can stand alone as a
single useful idea.

START
Basic
What is one sign that a note should be split?
Back: Two top-level sections explain different claims.
END
""",
    "Atomic Notes/202601010104 Misfiled reference note.md": """---
source: Synthetic Journal of Note Experiments
tags:
  - reference
---

# Misfiled reference note

> Highlight: Teams that review notes weekly often report cleaner links.

> Highlight: Several participants preferred examples over abstract rules.

These excerpts read like source material. They preserve highlights and summary
notes rather than presenting one Definition, Analogy, and Example.
""",
    "Atomic Notes/202601010105 Missing parent note.md": """---
aliases:
  - unparented dae note
tags:
  - atomic-note
---

# Missing parent note

An unparented atomic note has a focused idea but no link to a structure note
that explains where the idea belongs.

It is like a labeled folder left on a desk instead of filed in a cabinet.

For example, this note defines a review concern and gives a concrete case, but
it omits any structure-note parent link.

Sources:

1. Synthetic fixture handbook, 2026.
""",
    "Atomic Notes/202601010106 Factual risk note.md": """---
aliases: []
tags:
  - atomic-note
---

# Factual risk note

All memory techniques always work for every learner in every learning context.

This is like claiming one pair of shoes fits every person in every race.

For example, a learner who improves with spaced repetition proves that every
learner will improve with any memory technique.

Reference:

- [[Atomic Note Quality]]

Sources:

1. Synthetic fixture claim log, 2026.
""",
    "Atomic Notes/202601010107 Optional Anki cards can reinforce an atomic note when the prompt tests the central claim instead of repeating the heading.md": """---
aliases:
  - balanced anki dae
tags:
  - atomic-note
---

# Optional Anki note

Optional Anki cards can reinforce an atomic note when the prompt tests the
central claim instead of repeating the heading.

It is like a smoke alarm for memory: useful when it checks the right risk.

For example, an optional Anki card can ask which claim the note is testing
without exposing the answer inside the prompt.

START
Basic
What should an optional Anki card test?
Back: The central claim of the note.
END

Reference:

- [[Atomic Note Quality]]

Sources:

1. Synthetic fixture handbook, 2026.
""",
    "Atomic Notes/202601010108 Malformed Anki note.md": """---
aliases: []
tags:
  - atomic-note
---

# Malformed Anki note

A malformed Anki note contains a card boundary that never closes.

It is like opening a quotation mark and forgetting to close it.

For example, this note opens an Anki card block and never writes the matching
END marker.

START
Basic
What is wrong with this card?
Back: It starts but never ends.

Reference:

- [[Atomic Note Quality]]

Sources:

1. Synthetic fixture handbook, 2026.
""",
    "Atomic Notes/202601010109 Duplicate candidate note.md": """---
aliases:
  - atomic quality overlap
tags:
  - atomic-note
---

# Duplicate candidate note

Atomic-note quality improves when one note explains one durable idea with a
definition, analogy, example, links, and sources.

It is like checking a single ingredient before adding it to a recipe.

For example, this is an overlap candidate for the quality criteria collected in
[[Atomic Note Quality]] and may duplicate the clean DAE example.

Reference:

- [[Atomic Note Quality]]

Sources:

1. Synthetic fixture handbook, 2026.
""",
    "Atomic Notes/202601010110 A source-backed atomic note keeps one durable idea in DAE form and adds optional trailing sections for connections and provenance.md": """---
aliases:
  - reference and sources example
tags:
  - atomic-note
---

# Reference and sources note

A source-backed atomic note keeps one durable idea in DAE form and adds optional
trailing sections for connections and provenance.

It is like a museum placard: the caption explains the piece while a small line
beneath it credits where the piece came from.

For example, a note defines a concept, links to a sibling note under Reference,
and lists its origin under Sources.

Reference:

- Related: [[202601010101 A clean atomic note explains one durable idea in plain language and keeps the claim small enough to test against examples]].

Sources:

1. Synthetic fixture handbook, 2026.
""",
    "Structure Notes/Atomic Note Quality.md": """---
aliases:
  - atomic note review hub
tags:
  - structure-note
---

# Atomic Note Quality

Use this synthetic hub to compare notes that pass or fail atomic-note review.

## Strong examples

- [[202601010101 A clean atomic note explains one durable idea in plain language and keeps the claim small enough to test against examples]]
- [[202601010107 Optional Anki cards can reinforce an atomic note when the prompt tests the central claim instead of repeating the heading]]
- [[202601010110 A source-backed atomic note keeps one durable idea in DAE form and adds optional trailing sections for connections and provenance]]

## Review candidates

- [[202601010109 Duplicate candidate note]]
""",
    "Templates/Atomic Note Template.md": """---
aliases: []
tags:
  - template
---

# {{title}}

State the single idea clearly.

Compare the idea to a familiar situation.

Show the idea in a concrete case.

Reference:

- [[Related note]]

Sources:

- Source title.
""",
}


def create_fixture_vault(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative_path, content in NOTE_CONTENT.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def main(target: str | Path) -> int:
    root = create_fixture_vault(Path(target))
    print(root)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a synthetic fixture vault.")
    parser.add_argument("target", type=Path, help="Directory to create or update")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main(_parse_args().target))
