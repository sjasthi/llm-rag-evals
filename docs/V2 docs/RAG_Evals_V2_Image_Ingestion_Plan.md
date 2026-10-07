# RAG Evals Version 2.0 Image Ingestion Plan

## Purpose

V2 should let users upload standalone image files, mainly **PNG** and
**JPEG**, and retrieve their content in Chat the same way they retrieve
PDF content. The professor suggested reusing the new PDF pipeline,
specifically its image branch. This document checks whether converting
an image to a PDF and running it through `process_pdf()` works, lists the
other approaches, and recommends one.

## How the Current Image Branch Works

```text
PDF ──> process_pdf()                      rag/pdf_processor.py
          ├─ text      -> "text" element      (pymupdf_text)
          ├─ tables    -> "table" element     (pymupdf_table)
          ├─ embedded images
          │     document.extract_image(xref)
          │     analyze_visual(bytes, ext)  -> image/chart/diagram/scanned_page/other
          │                                   (gemini_vision)
          └─ vector drawings
                render page -> analyze_visual (gemini_vision_page_render)
        ──> chunk_element()                 rag/chunking.py
        ──> MySQL document_chunks + ChromaDB
```

The part that does the work for images is `analyze_visual()` in
`rag/visual_processor.py`. It takes **raw image bytes and a format
string**. It does not need a PDF. The PDF code only finds the image
bytes and passes them to it.

## Option A: Convert the Image to a PDF, Then Run `process_pdf()`

### Is it viable?

**Yes, with two fixes.** We tested it with PyMuPDF
(`pymupdf.open(image).convert_to_pdf()`) and the current
`process_pdf()`, with `analyze_visual()` stubbed out so no Gemini calls
were made:

| Input | Result | What Gemini would receive |
| --- | --- | --- |
| RGB PNG | 1 `image` element, page 1 | Correct image |
| JPEG (CMYK) | 1 `image` element, page 1 | Correct image, converted to RGB |
| Multi-page TIFF (2 frames) | 2 elements, pages 1 and 2 | Correct image per page |
| **PNG with transparency** (RGBA or palette) | 1 `image` element | **A solid black image. The text is lost.** |
| **JPEG with EXIF rotation** (phone photo) | 1 `image` element | **The unrotated raw pixels.** The page itself is rotated correctly. |

The vector-drawing branch never fires for image-only PDFs, and no text
or table elements are made, so each image costs **one Gemini call**.
That is the same cost as calling Gemini on the image directly.

### Why the two failures happen

`process_pdf()` uses `document.extract_image(xref)`, which returns the
image's **raw stored stream**:

- A PDF stores transparency as a separate soft mask (`smask`).
  `extract_image()` returns only the base color channels, so transparent
  pixels become black. In our test, all 80,000 pixels came back as value
  0. Screenshots, logos and exported slides often have transparency.
- PyMuPDF uses EXIF orientation to set the page size, but the stored
  image stream is not rotated. Gemini gets the sideways pixels.

Rendering the page (`page.get_pixmap(alpha=False)`, which
`render_page_for_visual_analysis()` already does) composites the mask
onto white and keeps the orientation. In our test, the transparent PNG's
text survived rendering.

### Other drawbacks

- **Provenance is wrong.** The document would be stored with
  `source_type = 'pdf'` and `extraction_method = 'gemini_vision'`, even
  though the user uploaded a PNG. The V2 schema records extraction
  provenance so V1-versus-V2 results can be explained. A wrapper PDF
  hides where the content came from.
- **Extra work for no gain.** We encode a PDF only to decode it again.
  The image may be re-encoded, and we pay the cost of building and
  opening the PDF.
- **Coupling.** Future changes to `process_pdf()`, such as size filters,
  duplicate-image rules or table heuristics, would quietly change how
  images behave.

### Fixes needed if we choose Option A

1. For image-derived PDFs, send the **rendered page** to Gemini instead
   of `extract_image()` bytes. Alternatively, flatten the image before
   building the PDF: apply EXIF orientation, composite onto white, and
   convert to RGB.
2. Keep the original `source_type` (`png` or `jpeg`) and set
   `extraction_method` to something like `gemini_vision_image_file`.
   This means `ingest.py` must not label the document `pdf`.

## Option B (Recommended): Send Image Files Directly to the Image Branch

Add a small `process_image()` that produces the same `DocumentElement`
objects `process_pdf()` produces, without building a PDF:

```text
PNG / JPEG ──> normalize with Pillow
                 - ImageOps.exif_transpose (fix phone rotation)
                 - composite alpha onto white, convert to RGB
                 - downscale the long edge to a cap (for example 3072 px)
                 - re-encode as PNG (or JPEG for photos)
           ──> analyze_visual(bytes, "png")         same Gemini call and prompt
           ──> DocumentElement(page_number=1,
                               content_type=<from Gemini>,
                               extraction_method="gemini_vision_image_file")
           ──> chunk_element() ──> MySQL + ChromaDB  same as PDFs
```

This *is* reusing the PDF pipeline's image branch, as the professor
suggested. It shares `analyze_visual()`, the visual prompt, the
`DocumentElement` contract, `chunk_element()`, the V2
`document_elements` table and Chroma storage. It skips only the
PDF-specific discovery step, which is where both failures came from.

Why we recommend it:

- The transparency and rotation failures cannot happen, because we
  normalize the pixels ourselves.
- Provenance is accurate. `source_type` is `png` or `jpeg`, and
  `extraction_method` says the content came from an image file.
- It needs about 40 lines of new code and no new packages. Pillow is
  already installed as a dependency of `pdfplumber` and `ragas`. We should
  still list it in `rag/requirements.txt` once we import it directly.
- Multi-frame formats (TIFF, animated GIF/WebP) can loop over frames
  with `ImageSequence` and use the frame number as `page_number`.

### Implementation steps

| # | Change | File |
| --- | --- | --- |
| 1 | Add `process_image(path, settings) -> list[DocumentElement]` with Pillow normalization and a size or pixel cap | new `rag/image_processor.py` |
| 2 | Fix the MIME type: `image/jpg` is not a valid MIME type, so map `jpg` to `image/jpeg` | `rag/visual_processor.py` (`analyze_visual`) |
| 3 | Route `.png`, `.jpg` and `.jpeg` to `process_image()` and keep `source_type` as `png` or `jpeg` | `rag/ingest.py` (`prepare_document_chunks`, `build_chunks`, `read_documents`) |
| 4 | Add image types to `SUPPORTED_TYPES` and its error message | `rag/document_loader.py` |
| 5 | Allow `png => image/png` and `jpg/jpeg => image/jpeg`; verify the MIME type with `finfo` as the code already does | `api/documents.php` (`ALLOWED_UPLOADS`) |
| 6 | Update the file picker `accept=".txt,.pdf,.docx"` | `index.php` |
| 7 | Persist each image's element row in `document_elements` (`page_number = 1`), and its chunks with `element_id` | `rag/database.py` / `rag/ingest.py` (V2 schema write path) |
| 8 | Tests: alpha PNG, EXIF-rotated JPEG, CMYK JPEG, oversized image and corrupt file, all with `analyze_visual` stubbed so the tests stay provider-free | `tests/` |

### Things to decide

- **Dense text images.** `MAX_VISUAL_OUTPUT_TOKENS = 1024` can cut off
  a screenshot of a full policy page. Raise it for image files, or for
  the `scanned_page` type.
- **Failure behavior.** For PDFs, a failed visual call logs a warning and
  skips that image. For an image file, the image *is* the whole
  document, so a failed call should fail the upload with a clear error
  (`record_document_failure`) instead of indexing nothing.
- **Re-ingestion cost.** Images cost a paid Gemini call each time they
  are ingested. **Restore bundled sources** re-runs every one. We could
  cache results by `source_hash` and `extraction_model`.
- **Formats beyond PNG and JPEG.** WebP works through Pillow and Gemini
  with no extra work. HEIC (iPhone photos) needs `pillow-heif`. Gemini
  accepts PNG, JPEG, WebP, HEIC and HEIF.

## Option C: Local OCR (Tesseract)

Run OCR on the image, using `pytesseract` or PyMuPDF's Tesseract
integration, and store the text as an `ocr_text` element.

- **Pros:** free, offline, the same input always gives the same output,
  and no API key is needed. That fits the project's provider-free test
  philosophy.
- **Cons:** it needs the Tesseract system binary on the server, which
  the PHP host may not have. It reads text only. It cannot describe
  charts, diagrams or photos, and it does poorly on low-quality phone
  photos.
- **Best use:** as a **fallback** when no Gemini key is configured, or a
  **hybrid**: OCR first, then call Gemini only when OCR finds little text
  or the image looks like a chart. The schema already supports this,
  because `extraction_method` and `content_type` record which path
  produced each element.

## Option D: Multimodal Embeddings

Embed the image directly with CLIP, Gemini multimodal embeddings or a
similar model, and retrieve by vector similarity.

- **Cons:** it needs a second Chroma collection, because the current
  `all-MiniLM-L6-v2` index is text-only. Scores from the image index and
  the text index cannot be compared directly. The answer LLM still needs
  text or the raw image to answer. The text-based evaluators
  (faithfulness, context precision and the others) cannot score image
  vectors.
- **Verdict:** too large a change for this phase. It is worth revisiting
  only if image-to-image search becomes a requirement.

## Option E: Store the Image and Pass It to the Answer Model at Query Time

Index a caption for retrieval. When the caption is retrieved, send the
original image to a multimodal answer model.

- **Pros:** the answer model sees the whole image, so no detail is lost
  in the caption.
- **Cons:** every question that retrieves the image pays image-input
  cost. `retrieved_contexts.context_excerpt` and all 13 evaluators expect
  text, so evaluation would no longer be comparable with V1.
- **Verdict:** a possible later improvement on top of Option B, not a
  replacement for it.

## Comparison

| | A: Image to PDF | **B: Direct (recommended)** | C: OCR | D: Image embeddings | E: Image at query time |
| --- | --- | --- | --- | --- | --- |
| Reuses current pipeline | Fully | Image branch, chunking, storage | Chunking, storage | Little | Partly |
| Charts and diagrams | Yes | Yes | No | Partly | Yes |
| Transparent PNG / phone photo | **Broken without fixes** | Handled | Handled | Handled | Handled |
| Accurate provenance | No, unless patched | Yes | Yes | Yes | Yes |
| Cost per image | 1 Gemini call | 1 Gemini call | Free | Embedding call | 1 call plus per-question cost |
| Fits the text-based evaluators | Yes | Yes | Yes | No | Partly |
| New dependencies | None | None (Pillow is already installed; list it explicitly) | Tesseract binary | Model and second index | Multimodal answer model |
| Effort | Small, plus fixes | Small | Small to medium | Large | Medium |

## Recommendation

1. **Build Option B.** It reuses the PDF pipeline's image branch through
   `analyze_visual()`, `DocumentElement`, `chunk_element()` and the V2
   `document_elements` table. It avoids the PDF wrapper, which loses
   transparent content and phone-photo rotation, and it records accurate
   provenance.
2. If the team prefers Option A to keep one code path, make the two
   fixes above: render the page instead of using `extract_image()`, and
   keep the original `source_type`. Without them, transparent PNGs index
   as empty or incorrect content.
3. Later, consider adding Option C as a no-API-key fallback, or as a
   hybrid that avoids Gemini calls for text-only images.

## Appendix: Reproducing the Conversion Test

The test built a transparent RGBA PNG, an RGB PNG, an EXIF-rotated
JPEG, a CMYK JPEG, a transparent palette PNG and a two-frame TIFF. It
converted each with `pymupdf.open(path).convert_to_pdf()`, ran
`pdf_processor.process_pdf()` with `analyze_visual` replaced by a stub
that recorded the bytes it received, and inspected those bytes with
Pillow. The transparent images came back with one pixel value: black.
Rendering the same page with `get_pixmap(alpha=False)` kept the text
(PyMuPDF 1.28.2, Pillow 12.3).
