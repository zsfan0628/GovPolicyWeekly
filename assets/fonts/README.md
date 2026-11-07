# Embedded PDF Fonts

Source Han Sans CN (Simplified Chinese), Regular 400, Medium 500 and Bold 700.
Static TrueType instances generated from Adobe's regional variable font using
fontTools. All 30,926 Unicode mappings in the source font are retained; these are
not the small, sample-text-only subsets used during the design preview.

Source: https://github.com/adobe-fonts/source-han-sans/tree/release/Variable/TTF/Subset
Original file: SourceHanSansCN-VF.ttf
License: SIL Open Font License 1.1; see LICENSE.txt.

The application embeds the used glyphs in each PDF. Users do not need to install
the fonts separately. Include this directory in source archives and frozen builds.
Font generation is a development step, not an installation or runtime dependency.
