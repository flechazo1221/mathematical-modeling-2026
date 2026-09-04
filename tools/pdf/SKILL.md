---
name: pdf
description: Read, extract, create, merge, split, rotate, OCR, secure, or fill PDF files when the requested operation acts on PDF content or structure. Do not trigger merely because a PDF is mentioned as a citation or background source.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Operations

Preserve source PDFs unless the user explicitly requests in-place replacement. Write outputs to the requested location, validate that they open, and inspect rendered pages whenever layout can change.

## Route by operation

- Text or table extraction: use `pdfplumber` for layout-aware extraction and `pypdf` for basic text or metadata. Record page numbers; do not silently treat an empty text layer as an empty document.
- Scanned documents: inspect a sample page, then use local OCR. Report language, unreadable pages, and whether results came from OCR.
- Merge, split, rotate, metadata, encryption, or decryption: use `pypdf` or `qpdf`; preserve page order and verify the resulting page count.
- Creation: use a document-native source when complex layout matters; otherwise use ReportLab. Avoid Unicode subscript/superscript glyphs in built-in ReportLab fonts—use paragraph markup or an embedded font.
- Forms: read [forms.md](forms.md) and use the bundled scripts under `scripts/`.

## Required checks

1. Confirm the exact input and output paths and whether overwrite is authorized.
2. Compare input/output page counts and the requested page order or transformations.
3. Reopen the output with an independent parser.
4. Render and visually inspect affected pages after filling, OCR, watermarking, rotation, or PDF creation.
5. Report encrypted, corrupt, image-only, clipped, missing-font, or partially processed pages instead of claiming full success.

Do not install dependencies, bypass access controls, remove encryption without authorization, or expose supplied passwords in logs.
