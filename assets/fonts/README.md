# Bundled Desktop and PDF Fonts

The desktop uses Source Han Serif CN SemiBold for titles and the calendar count,
and Source Han Sans CN for controls, text and log columns. These fonts load
locally, without a system-wide installation. PDF export still uses Sans only.

Serif: unmodified Adobe regional OpenType, tag 2.003R, licensed under the
SIL Open Font License 1.1 (see LICENSE-Serif.txt).
[Upstream font](https://github.com/adobe-fonts/source-han-serif/blob/7889f11bf31170b5d092a083b357c8c8130f89e0/SubsetOTF/CN/SourceHanSerifCN-SemiBold.otf).
SHA-256: `50d3f12201ce2dd840650b6bfa47ebb8572ecf767eec0e5ccb20a247b5bfa805`.

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
