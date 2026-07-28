# Beetle Scan Compare 0.1.0

Beetle Scan Compare is a local macOS quality-control tool for comparing two
folders of beetle scan images side by side. It conservatively matches similar
filenames, supports dorsal (`-D`), ventral (`-V`), and right-side (`-R`) views,
and records rapid approve/reject decisions without modifying source images.

## Highlights

- Rapid keyboard review with **A** to approve and **R** to reject.
- Sustained background preloading for smooth navigation through large reviews.
- Independent zoom and drag-to-pan for both images.
- Scrollable **All Matched Pairs** and **Rejected Pairs** navigator tabs.
- Immediate temporary autosave plus timestamped decision and unmatched CSV
  exports.
- Conservative one-to-one fuzzy matching that reports ambiguous files rather
  than guessing.
- High-contrast two-FFB macOS application icon based on a dorsal forked fungus
  beetle reference and optimized for small Dock/Finder sizes.
- Standalone Apple Silicon application containing its Python and Pillow runtime.

## Installation

1. Download the Apple Silicon DMG.
2. Open it and drag **Beetle Scan Compare** into **Applications**.
3. Because this is an unsigned research build, the first launch may require
   Control-clicking the app and selecting **Open**.

The installer supports Apple Silicon Macs (M1, M2, M3, M4, or newer). Source
images remain read-only and no image data is sent over the network.
