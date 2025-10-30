from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_chess_sft_dataset import build_training_examples, moves_to_history


def test_moves_to_history_white_perspective():
    history = moves_to_history(["e4", "Nf3"], ["e5", "Nc6"], "white")
    assert history == "1. e4 e5 2. Nf3 Nc6"


def test_moves_to_history_black_perspective():
    history = moves_to_history(["e5", "Nc6"], ["e4", "Nf3"], "black")
    assert history == "1. e4 e5 2. Nf3 Nc6"


def test_build_training_examples_white_player_alignment():
    df = pd.DataFrame(
        [
            {
                "White": "alice",
                "Black": "engine",
                "OwnMoves": ["e4", "Nf3"],
                "OpponentMoves": ["e5", "Nc6"],
                "TimeControl": "600",
                "ECO": "C50",
            }
        ],
        index=["game-1"],
    )

    examples = build_training_examples(df, "alice")
    assert len(examples) == 2
    assert examples[0].my_previous_moves == []
    assert examples[0].opponent_previous_moves == []
    assert examples[1].my_previous_moves == ["e4"]
    assert examples[1].opponent_previous_moves == ["e5"]


def test_build_training_examples_black_player_alignment():
    df = pd.DataFrame(
        [
            {
                "White": "opponent",
                "Black": "alice",
                "OwnMoves": ["d5", "Nf6"],
                "OpponentMoves": ["d4", "c4"],
                "TimeControl": "600",
                "ECO": "D06",
            }
        ],
        index=["game-2"],
    )

    examples = build_training_examples(df, "alice")
    assert len(examples) == 2
    assert examples[0].my_previous_moves == []
    assert examples[0].opponent_previous_moves == ["d4"]
    assert examples[1].my_previous_moves == ["d5"]
    assert examples[1].opponent_previous_moves == ["d4", "c4"]
