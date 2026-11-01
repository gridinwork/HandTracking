# Third-Party Licenses

HandTracking depends on third-party open-source software. Each dependency remains subject to its own license.

## Google MediaPipe

- Project: https://github.com/google-ai-edge/mediapipe
- License: Apache License 2.0
- Usage in this project: MediaPipe Python solutions API — Holistic (pose + hand landmarks), hand and pose connection definitions.

MediaPipe model files are not committed to this repository. They are shipped inside the `mediapipe` package installed from PyPI.

## OpenCV

- Project: https://opencv.org/
- Package used: `opencv-python`
- License: Apache License 2.0 for current OpenCV releases.

## NumPy

- Project: https://numpy.org/
- License: BSD-3-Clause.

## PySide6 / Qt for Python

- Project: https://doc.qt.io/qtforpython/
- Licensing: LGPLv3 / GPLv3 / commercial options, subject to Qt's published licensing terms.

## Python (embeddable distribution, optional)

- Project: https://www.python.org/
- License: Python Software Foundation License.
- Usage: `requirements.py` can download the official embeddable Python 3.11 package from python.org at install time. It is not included in this repository.

## Repository license

Unless otherwise noted, original application source code in this repository is licensed under the Apache License 2.0 in the root `LICENSE` file.

This document is provided for attribution and dependency clarity; it does not replace the complete license text distributed by each upstream project.
