# CAJ processing route

Read this reference only when `literature/input/` contains `.caj` files.

## Supported route

Use `scripts/prepare_literature_corpus.py` first. It keeps the CAJ source unchanged and records every conversion or extraction result.

1. If the file starts with a PDF signature despite its extension, process it directly as PDF.
2. If a same-stem PDF is beside the CAJ file, treat that PDF as the user's manual conversion and retain the CAJ as the provenance source.
3. Otherwise use an installed `caj2pdf` command, or pass its path with `--caj2pdf`. The converter's own documentation says that CAJ and HN are different internal families and HN support is incomplete; conversion success must therefore be verified, not assumed.
4. If conversion is unavailable or fails, record `needs_manual_conversion`. Ask the user to open the file with official CAJViewer and produce a same-stem PDF under `literature/input/`, then rerun preprocessing.
5. After PDF creation, extract its text layer locally. If text density is too low, try an installed `ocrmypdf`; otherwise record `ocr_required` and request a text-selectable PDF or TXT export. Do not spend model tokens visually reading an entire image-only thesis.

Never upload competition literature to an unapproved third-party conversion website. Do not delete or overwrite the CAJ source.

## Tool facts and sources

- Official CAJViewer downloads: <https://cajviewer.oversea.cnki.net/download.html>
- `caj2pdf` source and compatibility warning: <https://github.com/caj2pdf/caj2pdf>
- Packaged `caj2pdf-restructured` requirements: <https://pypi.org/project/caj2pdf-restructured/>
- Official MuPDF releases for the `mutool` dependency: <https://mupdf.com/releases>

The open-source converter is a best-effort compatibility layer, not an official CNKI parser. Preserve converter logs in the corpus manifest and fall back to CAJViewer when the subtype is unsupported.
