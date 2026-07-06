# VLDB-2027-Template

Official LaTeX template for PVLDB Volume 20 / VLDB 2027 submissions,
maintained by the VLDB 2027 Program and Proceedings Chairs.

Currently configured for **PVLDB Volume 20**, bundling **acmart.cls v2.19
(2026/06/27)**, pinned from [CTAN](https://ctan.org/pkg/acmart).

Use this repository directly rather than an old Overleaf copy, a
previous volume's template, or your local TeX installation's default
`acmart.cls`.

## Contents

| File | Purpose |
|---|---|
| `main.tex` | The paper source you edit. |
| `acmart.cls` | ACM base class, v2.19. Do not edit. |
| `vldb2027.sty` | PVLDB/VLDB-specific formatting and boilerplate. Do not edit. |
| `ACM-Reference-Format.bst` | Bibliography style matching `acmart.cls` v2.19. |
| `sample.bib` | Example bibliography — replace with your own. |
| `figures/` | Example figure — replace/add your own. |

## What's new vs. Volume 19 and earlier

- **`acmart.cls` is pinned to v2.19**, bundled directly in this repo.
  Previous volumes didn't pin a version, so output varied depending on
  the acmart version an author's TeX Live install or Overleaf project
  happened to default to.
- **ALL-CAPS section headings are explicitly restored.** acmart v2.x
  changed its default so section headings are no longer auto-capitalized.
  Every published PVLDB volume to date uses ALL-CAPS ("1 INTRODUCTION"),
  so this is now set explicitly rather than left to the class default.
- **VLDB-specific formatting now lives in `vldb2027.sty`**, not hardcoded
  in `main.tex`. The PVLDB Reference Format block, license/copyright
  footnote, and Artifact Availability block are rendered by a single
  `\vldbtopmatter` call instead of ~25 lines of inline LaTeX authors could
  edit or break by accident.

## Usage

1. Edit `main.tex`: title, authors, affiliations, abstract, body,
   bibliography. Leave `acmart.cls` and `vldb2027.sty` alone.

2. Set the paper-specific values near the top of `main.tex`:
   ```latex
   \renewcommand\vldbdoi{XX.XX/XXX.XX}
   \renewcommand\vldbpages{XXX-XXX}
   \renewcommand\vldbavailabilityurl{URL_TO_YOUR_ARTIFACTS}
   ```
   Leave `\vldbavailabilityurl` empty (`{}`) if there's nothing to link.
   DOI/pages are normally assigned during production — placeholders are
   fine for submission.

3. Don't touch the two blocks marked
   `%%% do not modify the following VLDB block %%`:
   - `\usepackage{vldb2027}` right after `\documentclass`
   - `\vldbtopmatter` right after `\maketitle`

   These apply the reference format, license footnote, availability
   block, and ALL-CAPS headings. Removing them will put your paper out
   of compliance with the formatting guidelines.

4. Compile:
   ```
   pdflatex main.tex
   bibtex main
   pdflatex main.tex
   pdflatex main.tex
   ```

5. Check output against the current
   [formatting guidelines](https://www.vldb.org/2027/formatting-guidelines.html)
   before submitting.

## Issues

Open an issue in this repository, or contact the VLDB 2027 Proceedings
Chairs, if you hit a bug in the template or a formatting flag you
believe originates here rather than in your own `main.tex`.
