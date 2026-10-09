# Key-detection benchmark

GiantSteps Key: Beatport previews with user-corrected human labels.

## Human labels (n=604)

| method                             |   weighted |   ci_lo |   ci_hi |   exact_% |   mixable_% |   sec_per_track |   failed |
|:-----------------------------------|-----------:|--------:|--------:|----------:|------------:|----------------:|---------:|
| M3 Essentia KeyExtractor edmm      |      0.701 |   0.668 |   0.735 |    64.901 |      77.815 |           0.238 |        0 |
| M2 Essentia KeyExtractor bgate     |      0.68  |   0.646 |   0.714 |    61.258 |      78.311 |           0.249 |        0 |
| M3 Essentia KeyExtractor braw      |      0.666 |   0.632 |   0.7   |    60.099 |      77.318 |           0.231 |        0 |
| M3 Essentia KeyExtractor edma      |      0.65  |   0.614 |   0.684 |    57.616 |      72.185 |           0.242 |        0 |
| M2 Essentia KeyExtractor shaath    |      0.633 |   0.599 |   0.665 |    55.132 |      70.364 |           0.24  |        0 |
| M2 Essentia KeyExtractor krumhansl |      0.585 |   0.55  |   0.618 |    49.007 |      66.391 |           0.239 |        0 |
| M1 KS librosa chroma_stft          |      0.536 |   0.503 |   0.573 |    42.881 |      64.073 |           0.393 |        0 |
| M1 KS librosa chroma_cqt           |      0.52  |   0.484 |   0.556 |    44.371 |      60.43  |           0.742 |        0 |
| M4 HPCP36 edma no-detune           |      0.483 |   0.449 |   0.518 |    41.556 |      64.404 |           0.332 |        0 |
| M4 HPCP36 edma                     |      0.473 |   0.438 |   0.508 |    40.563 |      63.411 |           0.389 |        0 |
| M9 bass/treble chroma w=0.5        |      0.469 |   0.43  |   0.505 |    39.073 |      57.119 |           0.372 |        0 |
| M2 Essentia KeyExtractor temperley |      0.464 |   0.431 |   0.498 |    34.934 |      66.391 |           0.246 |        0 |
| M9 bass/treble chroma w=0.3        |      0.464 |   0.426 |   0.497 |    37.748 |      57.45  |           0.672 |        0 |
| M4 HPCP36 bgate no-detune          |      0.454 |   0.418 |   0.491 |    39.901 |      63.576 |           0.324 |        0 |
| M9 bass/treble chroma w=0.7        |      0.445 |   0.408 |   0.479 |    38.079 |      53.311 |           0.328 |        0 |
| M4 HPCP36 bgate                    |      0.439 |   0.403 |   0.476 |    38.245 |      61.093 |           0.324 |        0 |
| M4 HPCP36 edma majmin              |      0.345 |   0.317 |   0.377 |    22.351 |      37.748 |           0.316 |        0 |

## Not run

- M5 Faraldo multi-profile (edmkey): repo not vendored; Essentia edma+majmin (M4) approximates it
- M6 libKeyFinder: no pip bindings / keyfinder-cli installed
- M8 Demucs stems + best: demucs not installed (heavy torch download); not run
- M10 Key-CNN: key-cnn/tensorflow not installed; not run
- M11 madmom CNN: madmom does not install on Python 3.10/numpy 2; not run
