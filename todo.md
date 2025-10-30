Engine endpoint:
  - Replace the mock Flask server with a staffed policy/engine that understands castling, en passant, and check/mate, and returns deterministic best moves.

Swift move logic:
  - Extend SAN parsing for castling/en passant and add checkmate/stalemate detection to finish the core ruleset.

Training pipeline:
  - [x] Add unit tests around the dataset script.
  - [ ] Automate regeneration on new archives.
  - [ ] Version resulting datasets/models.

Environment hygiene:
  - Recreate the virtual environment so /Users/imadeddine/miniforge3/bin/python resolves, then pin package versions once the toolchain is stable.
