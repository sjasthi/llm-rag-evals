# Final Study Evidence

This directory contains the application-generated JSON exports for the six
completed conditions in the `final-study-v1` experiment. They make the final
evidence inspectable from a GitHub clone without access to the author's local
MySQL database.

Every run uses the same ordered dataset-v2.0 question IDs:
`1, 23, 210, 213, 221` (display positions `1, 23, 35, 38, 46`). The files retain
run configuration, saved answers, immutable question snapshots, ordered
retrieved contexts, canonical evaluator results, attempt history, current
human reviews, and valid matched comparisons. They contain no API key or
database password.

| Run | Controlled condition | Baseline | Responses | Evidence |
| ---: | --- | ---: | ---: | --- |
| 5 | Chroma, top-k 3, Gemini 2.5 Flash, 27 documents | — | 5 | [JSON](final-study-run-5.json) |
| 6 | MySQL keyword retrieval | 5 | 5 | [JSON](final-study-run-6.json) |
| 7 | Chroma top-k 5 | 5 | 5 | [JSON](final-study-run-7.json) |
| 8 | Chroma top-k 8 | 5 | 5 | [JSON](final-study-run-8.json) |
| 10 | Gemini 3.1 Flash-Lite | 5 | 5 | [JSON](final-study-run-10.json) |
| 12 | Four-category, 20-document corpus | 10 | 5 | [JSON](final-study-run-12.json) |

Runs 9 and 11 are intentionally absent because they were unsuccessful audit
records rather than completed comparison conditions. Run 9 used a retired
model deployment name; run 11 reached the provider's free-tier request limit.
Their failure modes are documented in the
[final study report](../../../docs/final-study-report.md).

## SHA-256 checksums

The evidence JSON is pinned to LF line endings through `.gitattributes`, so
these hashes remain stable across operating-system checkouts.

```text
8343202c6ed513ef72238ad4d2c32ac87e88d0d5c9c00e67dc2bbedef49a7bfd  final-study-run-10.json
a052e4b2b626a52c673e494980f99a1b20ad3ed99b688f0de7b91542c9810cf4  final-study-run-12.json
92c6176eed86f8a5d271810baf7ba89de33f38d5259884c16d7824f5d15668ae  final-study-run-5.json
ca7177efed68fd43f75c8190ea049c373f4053f852cc909b8aa70b61ee31cc8f  final-study-run-6.json
e80e5af313b9e9b865169f0e6822d14f426a230b1bd719beb0fcc1831bdda477  final-study-run-7.json
e6e3f261bf8803da02d473d023f7dcf5119f92740fd97dcbb7938b8f154efde5  final-study-run-8.json
```
