# PDF Layout / PDF 版式

All normal exports use the built-in renderer, regardless of LibreOffice availability.
Word, Excel and JSON exports remain available and keep their existing formats.
The PDF design was approved using a small preview; the production renderer supports
arbitrary result counts and paginates dynamically rather than fixing six items to four pages.

- A4 portrait; embedded Source Han Sans CN Regular, Medium and Bold.
- Overview counts are mutually exclusive: a record labelled both policy and personnel
  appears only in the personnel section. Dates sort descending within each section.
- Index titles and detail titles link to the original HTTP(S) article. Index numbers
  link to details inside the report. Original-page and attachment links remain clickable.
- Pale detail heading bands, grey summary blocks, accent bars and clear separators.
- Short items stay together when possible. Long tables and bodies can span pages;
  index table headers repeat. Footer numbering includes the total number of pages.
- Coverage comes from the actual task, never sample constants. Missing historical
  coverage is marked unknown. Empty results are not presented as proof of a complete search.
- Judgment methods/reasons and known collection failures appear in an appendix.
- Only exact repeated fragments and repeated titles are removed from display summaries.
  Raw result data is not changed; truncated or missing facts are not invented.

Fonts are included in `assets/fonts` with their OFL license. Source ZIP preparation
and PyInstaller both include that directory. No font installation, fontTools runtime
dependency or LibreOffice installation is required. Build/test dependencies include
pypdf for pagination/link/font checks; the renderer itself uses ReportLab.

The old DOCX-to-PDF helper remains for legacy callers, but `export_all` no longer
selects it automatically. Installing or bundling LibreOffice will not change the PDF
template. Rebuild the Windows executable before distributing these changes; already
downloaded executables do not update automatically.

This change is to PDF layout, not an audit or reclassification of historical articles.
