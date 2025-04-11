# ♟️ InfiniteChessAI

**InfiniteChessAI** is a Python-based, self-learning chess engine that trains by playing against itself infinitely until challenged by a human. The long-term goal is to create the world's smartest chess engine that learns and improves continuously without human supervision.

---

## 🚀 Vision

> Create a powerful AI engine that:
- Plays legal chess games using smart strategies.
- Trains itself through self-play using reinforcement learning.
- Continuously evolves its understanding of the game through deep learning.
- Challenges and beats human players with adaptive intelligence.

---

## 📌 Features (Planned Roadmap)

### ✅ Phase 1: Basic Engine Setup
- [x] Legal move generation using `python-chess`
- [x] Random-move engine prototype

### 🔄 Phase 2: Classical AI
- [ ] Minimax with evaluation function
- [ ] Alpha-beta pruning optimization

### 🧠 Phase 3: Reinforcement Learning
- [ ] Self-play match history recording
- [ ] Q-learning or policy gradient exploration

### 🔁 Phase 4: AlphaZero-style Deep Learning
- [ ] MCTS + Neural Network integration
- [ ] Policy and value network training
- [ ] Evaluation against past engine versions

### 🌐 Phase 5: Human Challenge Mode
- [ ] Web interface for human vs AI
- [ ] Elo-based ranking system
- [ ] Optional Stockfish benchmark comparison

---

## 🛠️ Technologies

| Tool          | Purpose                             |
|---------------|-------------------------------------|
| `python-chess`| Chess rules, board handling         |
| `PyTorch`     | Deep learning and neural networks   |
| `NumPy`       | Numerical calculations              |
| `Flask`       | (Planned) Web interface             |
| `Ray RLlib`   | (Optional) Reinforcement learning at scale |

---

## 📂 Project Structure (To be updated)

```
InfiniteChessAI/
├── engine/             # Core logic of the chess engine
│   ├── minimax.py
│   ├── evaluation.py
│   └── self_play.py
├── neural_net/         # Deep learning models and training
│   ├── model.py
│   └── train.py
├── interface/          # Human vs AI interface (Web or CLI)
│   └── play.py
├── data/               # Saved games, training data
│   └── games/
├── utils/              # Helper functions
│   └── board_utils.py
├── requirements.txt
└── README.md
```

---

## 📦 Installation

```bash
git clone https://github.com/your-username/InfiniteChessAI.git
cd InfiniteChessAI
pip install -r requirements.txt
```

> ✅ Requires Python 3.8 or later.

---

## 🧪 Running the Engine

Play a basic random move game:
```bash
python engine/random_play.py
```

> More game modes (minimax, self-play, MCTS) coming soon.

---

## 💡 Contributing

This is a solo R&D project for now, but open collaboration may come in the future. If you're passionate about AI, chess, or reinforcement learning — feel free to fork and experiment.

---

## 📖 References

- [AlphaZero Paper (DeepMind)](https://deepmind.google/discover/blog/alphazero-shedding-new-light-on-chess-shogi-and-go/)
- [python-chess Documentation](https://python-chess.readthedocs.io/en/latest/)
- [Reinforcement Learning: Sutton & Barto](http://incompleteideas.net/book/RLbook2020.pdf)

---

## 🧠 Author

**Imad Eddine El Mouss**  
🛠️ AI & Data Engineering student | 💭 Building intelligent systems from scratch

---

## 📅 Project Status

> 🚧 In early-stage development — follow the journey and witness the evolution of a truly infinite AI.
