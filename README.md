# ♟️ InfiniteChessAI

An experiment in building an end-to-end chess experience that spans an iOS board,
data collection from Chess.com, and (eventually) a self-improving engine. The
project is currently in a prototyping phase: we now have a SwiftUI board with a
basic rule engine, Python tooling to generate supervised datasets, and a mock
AI server so the client can be exercised while the real model is under
construction.

---

## � Current snapshot (October 2025)

- **SwiftUI board (`ChessAI/`)** – a native iOS app that lets you play as white
	against an AI operator. Legal move generation has been fleshed out for all
	pieces and simple SAN parsing is supported for AI moves.
- **Data tooling (`scripts/`, `main.ipynb`)** – reproducible pipeline that pulls
	your public Chess.com games and emits prompt/completion pairs for fine-tuning
	language models.
- **Mock inference server (`server/mock_ai_server.py`)** – a Flask service that
	uses `python-chess` to return random legal moves, unblocking UI development
	until a stronger model is available.
- **Supervised dataset (`sft_data.jsonl`)** – sample output generated from the
	notebook/script. Keep regenerating as your game archive grows.

---

## � Repository layout

```
.
├── ChessAI/                 # SwiftUI front-end
├── ChessAI.xcodeproj/
├── ChessAITests/, ChessAIUITests/  # Xcode test targets (placeholders for now)
├── scripts/
│   └── generate_chess_sft_dataset.py
├── server/
│   └── mock_ai_server.py
├── main.ipynb              # Exploratory notebook that informed the script
├── sft_data.jsonl          # Example supervised dataset
├── requirements.txt        # Python dependencies for scripts/server
└── README.md
```

---

## ⚙️ Getting started

### 1. Install Python tooling (optional but recommended)

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

### 2. Generate a supervised dataset

```bash
python scripts/generate_chess_sft_dataset.py <chess.com-username> --drop-abandoned
```

This mirrors the notebook workflow but is now reproducible. It writes a
JSONL file (default `sft_data.jsonl`) in the repository root.

### 3. Run the mock AI server

```bash
python server/mock_ai_server.py
```

The Swift client polls `http://localhost:5000/health` on launch and posts board
state to `/ai-move`. The mock server responds with random legal SAN moves.

### 4. Launch the iOS app

Open `ChessAI.xcodeproj` in Xcode (17+) and run the **ChessAI** scheme on an
iOS 17 simulator or device. Ensure the mock server is running for AI moves.

---

## 🧠 Vision & next phases

1. **Engine quality** – replace the mock server with a staffed engine that uses
	 the generated datasets (minimax baseline → policy/value networks → RL).
2. **Evaluation loop** – automate self-play, rating tracking, and regression
	 testing against prior checkpoints.
3. **UX polish** – richer move annotations, game history, difficulty settings,
	 and cross-platform support.

Refer to `scripts/` and `server/` for current scaffolding; everything is
intentionally modular to support incremental upgrades.

---

## � References & inspiration

- [python-chess documentation](https://python-chess.readthedocs.io/en/latest/)
- [AlphaZero paper (DeepMind)](https://deepmind.google/discover/blog/alphazero-shedding-new-light-on-chess-shogi-and-go/)
- [Hugging Face supervised fine-tuning docs](https://huggingface.co/docs/transformers/main/en/training)

---

## 👤 Author

**Imad Eddine El Mouss**  
AI & Data Engineering student | Building intelligent systems from scratch

---

## 📅 Status

Early-stage R&D: the plumbing is now in place, allowing us to iterate on model
quality and gameplay features with real feedback loops.
