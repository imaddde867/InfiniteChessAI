Engine endpoint: replace the mock Flask server with a real policy/engine that understands more SAN (castling, en passant, check/mate) and returns deterministic best moves.
Swift move logic: extend SAN parsing for castling/en passant and add checkmate/stalemate detection to finish the core ruleset.
Training pipeline: add unit tests around the dataset script, automate regeneration on new archives, and version resulting datasets/models.
Environment hygiene: recreate the virtual environment so /Users/imadeddine/miniforge3/bin/python resolves, then pin package versions once the toolchain is stable.