# Key-detection benchmark

GiantSteps Key: Beatport previews with user-corrected human labels (first 200 clips).

## Human labels (n=200)

| method                             |   weighted |   ci_lo |   ci_hi |   exact_% |   mixable_% |   sec_per_track |   failed |
|:-----------------------------------|-----------:|--------:|--------:|----------:|------------:|----------------:|---------:|
| bpmkey current (learned+bgate)     |      0.641 |   0.576 |   0.698 |      57   |        75   |           9.116 |        0 |
| M3 Essentia KeyExtractor edmm      |      0.62  |   0.556 |   0.684 |      55   |        72.5 |           0.236 |        0 |
| M2 Essentia KeyExtractor bgate     |      0.614 |   0.554 |   0.672 |      54   |        72   |           0.247 |        0 |
| M3 Essentia KeyExtractor braw      |      0.606 |   0.549 |   0.665 |      53.5 |        71   |           0.229 |        0 |
| M7 HPSS(margin=4) + bgate          |      0.59  |   0.528 |   0.649 |      50   |        69   |          13.933 |        0 |
| M7 HPSS(margin=8) + bgate          |      0.588 |   0.531 |   0.648 |      50   |        69   |          15.717 |        0 |
| M3 Essentia KeyExtractor edma      |      0.576 |   0.517 |   0.638 |      49   |        63.5 |           0.242 |        0 |
| M7 HPSS(margin=4) + edma           |      0.565 |   0.504 |   0.625 |      47.5 |        62.5 |          13.412 |        0 |
| M7 HPSS(margin=8) + edma           |      0.546 |   0.486 |   0.607 |      46   |        59   |          13.551 |        0 |
| M2 Essentia KeyExtractor shaath    |      0.541 |   0.478 |   0.601 |      44.5 |        60.5 |           0.239 |        0 |
| M2 Essentia KeyExtractor krumhansl |      0.526 |   0.471 |   0.588 |      42.5 |        58   |           0.24  |        0 |
| M4 HPCP36 edma no-detune           |      0.501 |   0.438 |   0.568 |      43.5 |        64.5 |           0.346 |        0 |
| M4 HPCP36 bgate no-detune          |      0.496 |   0.436 |   0.559 |      44   |        64.5 |           0.323 |        0 |
| M1 KS librosa chroma_stft          |      0.485 |   0.425 |   0.549 |      39   |        57   |           0.392 |        0 |
| M4 HPCP36 edma                     |      0.483 |   0.423 |   0.546 |      41.5 |        60.5 |           0.442 |        0 |
| M4 HPCP36 bgate                    |      0.475 |   0.412 |   0.539 |      42   |        61.5 |           0.328 |        0 |
| M1 KS librosa chroma_cqt           |      0.454 |   0.39  |   0.515 |      37.5 |        52   |           0.809 |        0 |
| M2 Essentia KeyExtractor temperley |      0.445 |   0.384 |   0.499 |      33.5 |        61   |           0.253 |        0 |
| M9 bass/treble chroma w=0.5        |      0.418 |   0.356 |   0.481 |      35   |        51   |           0.419 |        0 |
| M9 bass/treble chroma w=0.3        |      0.406 |   0.345 |   0.468 |      33   |        49.5 |           1.009 |        0 |
| M9 bass/treble chroma w=0.7        |      0.4   |   0.336 |   0.463 |      35   |        48.5 |           0.335 |        0 |
| M4 HPCP36 edma majmin              |      0.341 |   0.291 |   0.392 |      21.5 |        36.5 |           0.317 |        0 |

## Not run

- M5 Faraldo multi-profile (edmkey): repo not vendored; Essentia edma+majmin (M4) approximates it
- M6 libKeyFinder: no pip bindings / keyfinder-cli installed
- M8 Demucs stems + best: demucs not installed (heavy torch download); not run
- M10 Key-CNN: key-cnn/tensorflow not installed; not run
- M11 madmom CNN: madmom does not install on Python 3.10/numpy 2; not run
