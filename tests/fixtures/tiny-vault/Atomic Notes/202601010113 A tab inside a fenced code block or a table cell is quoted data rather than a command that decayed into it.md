---
aliases:
  - quoted control character
tags:
  - atomic-note
---

# Quoted control character note

A tab inside a fenced code block or a table cell is quoted data rather than a
command that decayed into it.

It is like a photograph of a broken window: the frame says the damage is being
shown rather than happening here.

For example, this note quotes the corrupted bytes so a reader can recognize
them on sight:

```text
3	imes 4
```

| Quoted bytes | Reading |
|---|---|
| 3	imes 4 | a tab standing where `\times` should begin |

Reference:

- [[Atomic Note Quality]]

Sources:

1. Synthetic fixture handbook, 2026.
