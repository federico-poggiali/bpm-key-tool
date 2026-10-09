# Key-detection benchmark

Ground truth = keys from online databases (GetSongBPM, AcousticBrainz), NOT human labels. 'agreed' = two databases gave the same key; 'all labels' also includes tracks with a single database key.

## agreed (2 DBs) (n=4)

| method                             |   weighted |   ci_lo |   ci_hi |   exact_% |   mixable_% |   sec_per_track |   failed |
|:-----------------------------------|-----------:|--------:|--------:|----------:|------------:|----------------:|---------:|
| M4 HPCP36 edma                     |      0.875 |   0.625 |       1 |        75 |         100 |           3.171 |        0 |
| M4 HPCP36 edma no-detune           |      0.875 |   0.625 |       1 |        75 |         100 |           3.435 |        0 |
| M4 HPCP36 bgate                    |      0.875 |   0.625 |       1 |        75 |         100 |           3.312 |        0 |
| M4 HPCP36 bgate no-detune          |      0.875 |   0.625 |       1 |        75 |         100 |           3.455 |        0 |
| M1 KS librosa chroma_cqt           |      0.75  |   0.5   |       1 |        50 |         100 |           6.438 |        0 |
| M1 KS librosa chroma_stft          |      0.75  |   0.5   |       1 |        50 |         100 |           4.274 |        0 |
| M2 Essentia KeyExtractor krumhansl |      0.75  |   0.5   |       1 |        50 |         100 |           4.193 |        0 |
| M2 Essentia KeyExtractor temperley |      0.75  |   0.5   |       1 |        50 |         100 |           4.668 |        0 |
| M2 Essentia KeyExtractor shaath    |      0.75  |   0.5   |       1 |        50 |         100 |           4.532 |        0 |
| M2 Essentia KeyExtractor bgate     |      0.75  |   0.5   |       1 |        50 |         100 |           4.328 |        0 |
| M3 Essentia KeyExtractor edma      |      0.75  |   0.5   |       1 |        50 |         100 |           2.798 |        0 |
| M3 Essentia KeyExtractor edmm      |      0.75  |   0.5   |       1 |        50 |         100 |           3.543 |        0 |
| M3 Essentia KeyExtractor braw      |      0.75  |   0.5   |       1 |        50 |         100 |           3.223 |        0 |
| M7 HPSS(margin=4) + edma           |      0.75  |   0.5   |       1 |        50 |         100 |          32.143 |        0 |
| M7 HPSS(margin=4) + bgate          |      0.75  |   0.5   |       1 |        50 |         100 |          31.738 |        0 |
| M7 HPSS(margin=8) + edma           |      0.75  |   0.5   |       1 |        50 |         100 |          30.671 |        0 |
| M7 HPSS(margin=8) + bgate          |      0.75  |   0.5   |       1 |        50 |         100 |          28.939 |        0 |
| M9 bass/treble chroma w=0.5        |      0.75  |   0.25  |       1 |        75 |          75 |           3.256 |        0 |
| M9 bass/treble chroma w=0.7        |      0.75  |   0.25  |       1 |        75 |          75 |           3.218 |        0 |
| bpmkey current (learned+bgate)     |      0.75  |   0.5   |       1 |        50 |         100 |          14.833 |        0 |
| M4 HPCP36 edma majmin              |      0.5   |   0     |       1 |        50 |          50 |           3.775 |        0 |
| M9 bass/treble chroma w=0.3        |      0.5   |   0     |       1 |        50 |          50 |           3.194 |        0 |

## all labels (n=43)

| method                             |   weighted |   ci_lo |   ci_hi |   exact_% |   mixable_% |   sec_per_track |   failed |
|:-----------------------------------|-----------:|--------:|--------:|----------:|------------:|----------------:|---------:|
| M4 HPCP36 bgate                    |      0.523 |   0.384 |   0.66  |    44.186 |      60.465 |           3.554 |        0 |
| M4 HPCP36 edma                     |      0.507 |   0.367 |   0.649 |    41.86  |      60.465 |           4.131 |        0 |
| M3 Essentia KeyExtractor edmm      |      0.491 |   0.367 |   0.626 |    37.209 |      60.465 |           3.336 |        0 |
| M2 Essentia KeyExtractor bgate     |      0.467 |   0.347 |   0.593 |    32.558 |      60.465 |           4.379 |        0 |
| M7 HPSS(margin=4) + bgate          |      0.467 |   0.349 |   0.593 |    32.558 |      58.14  |          35.576 |        0 |
| M3 Essentia KeyExtractor braw      |      0.467 |   0.339 |   0.586 |    32.558 |      60.465 |           3.4   |        0 |
| M3 Essentia KeyExtractor edma      |      0.46  |   0.326 |   0.591 |    34.884 |      55.814 |           3.684 |        0 |
| bpmkey current (learned+bgate)     |      0.456 |   0.326 |   0.579 |    32.558 |      58.14  |          16.893 |        0 |
| M7 HPSS(margin=4) + edma           |      0.451 |   0.335 |   0.581 |    32.558 |      58.14  |          40.749 |        0 |
| M7 HPSS(margin=8) + bgate          |      0.451 |   0.33  |   0.586 |    32.558 |      58.14  |          33.434 |        0 |
| M2 Essentia KeyExtractor krumhansl |      0.449 |   0.321 |   0.574 |    30.233 |      55.814 |           4.665 |        0 |
| M7 HPSS(margin=8) + edma           |      0.416 |   0.288 |   0.547 |    32.558 |      51.163 |          35.181 |        0 |
| M2 Essentia KeyExtractor shaath    |      0.402 |   0.279 |   0.542 |    32.558 |      46.512 |           4.732 |        0 |
| M4 HPCP36 edma no-detune           |      0.402 |   0.27  |   0.53  |    32.558 |      51.163 |           3.348 |        0 |
| M1 KS librosa chroma_stft          |      0.377 |   0.258 |   0.502 |    25.581 |      51.163 |           5.634 |        0 |
| M4 HPCP36 bgate no-detune          |      0.377 |   0.244 |   0.509 |    30.233 |      46.512 |           3.35  |        0 |
| M2 Essentia KeyExtractor temperley |      0.372 |   0.253 |   0.495 |    23.256 |      53.488 |           4.538 |        0 |
| M4 HPCP36 edma majmin              |      0.351 |   0.23  |   0.472 |    25.581 |      39.535 |           3.769 |        0 |
| M9 bass/treble chroma w=0.7        |      0.319 |   0.186 |   0.463 |    30.233 |      39.535 |           3.49  |        0 |
| M1 KS librosa chroma_cqt           |      0.309 |   0.195 |   0.433 |    20.93  |      44.186 |           7.495 |        0 |
| M9 bass/treble chroma w=0.5        |      0.286 |   0.163 |   0.414 |    23.256 |      41.86  |           3.397 |        0 |
| M9 bass/treble chroma w=0.3        |      0.251 |   0.142 |   0.365 |    18.605 |      34.884 |           3.397 |        0 |

## Not run

- M5 Faraldo multi-profile (edmkey): repo not vendored; Essentia edma+majmin (M4) approximates it
- M6 libKeyFinder: no pip bindings / keyfinder-cli installed
- M8 Demucs stems + best: demucs not installed (heavy torch download); not run
- M10 Key-CNN: key-cnn/tensorflow not installed; not run
- M11 madmom CNN: madmom does not install on Python 3.10/numpy 2; not run
