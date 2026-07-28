# Design and scientific-data safeguards

## Goals

The interface is optimized for fast visual quality control: a single ordered
sequence of pairs, two large images at equal scale, persistent filenames, and
single-key decisions.

The first visible pair is decoded immediately. Upcoming pairs are decoded and
resized by four background workers. Up to 120 forthcoming pairs are scheduled,
and a bounded in-memory cache retains 280 thumbnails. This avoids the slowdown
that occurred when rapid review exhausted the earlier 20-pair buffer while
still placing an upper bound on retained image memory.

Each image canvas has an independent 100–400% zoom level. Mouse-wheel zoom is
applied to the image under the pointer, while toolbar zoom applies to the canvas
with the blue active outline. Zoomed canvases can be panned by dragging.

Rejected decisions are mirrored into an in-session sidebar that shows both
filenames. Selecting an entry navigates back to the original pair index without
changing the decision; a later approve action replaces the rejection in both
the sidebar and autosaved CSV.

## Data flow

```text
Two selected folders
  -> filter by selected D/V/R marker
  -> normalize filenames
  -> conservative one-to-one fuzzy matching
  -> side-by-side rapid review
  -> temporary autosave plus explicit CSV exports
```

## Safety and provenance

- Image files are opened only for display.
- Full paths are retained in outputs so every decision can be traced.
- Every decision has a UTC timestamp and filename-match score.
- Unmatched files are reported from both input folders.
- Tied or near-tied candidates are not guessed.
- A temporary CSV is rewritten after every decision, limiting loss after a
  crash; explicit export creates timestamped permanent reports.

## Matching limitations

Filename similarity is not biological identity. Short or repetitive IDs may
produce high similarity scores. Scanner-generated suffixes other than the
documented D/V/R marker are not automatically stripped because doing so could
erase identifying information. Validate the match settings on representative
data, and treat the unmatched report as part of the review record.

## Future enhancements

- A signed `.app` bundle for installation without Terminal.
- Manual resolution of ambiguous candidates.
- Session resume from a saved decision CSV.
- Zoom/pan and synchronized image magnification.
- Optional SHA-256 hashes in exported provenance.
