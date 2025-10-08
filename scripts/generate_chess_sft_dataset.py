"""Generate supervised fine-tuning data from Chess.com games.

This script mirrors the exploratory notebook logic but wraps it in a reproducible
command-line workflow. It fetches public archives for a Chess.com username,
extracts SAN moves, and emits prompt/completion pairs suitable for tuning a
language model on move prediction.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pandas as pd
import requests

CHESS_COM_API = "https://api.chess.com/pub/player/{username}/games/archives"
USER_AGENT = "InfiniteChessAI/0.1"


@dataclass()
class TrainingExample:
    game_id: str
    move_number: int
    my_previous_moves: Sequence[str]
    opponent_previous_moves: Sequence[str]
    my_move: str
    time_control: str
    opening: str
    color: str

    def to_prompt_completion(self) -> Dict[str, str]:
        history = moves_to_history(self.my_previous_moves, self.opponent_previous_moves, self.color)
        prompt = (
            f"Moves so far: {history}\n"
            f"Play as {self.color}. Give only the next move in SAN (or UCI):"
        )
        completion = self.my_move + "\n"
        return {"prompt": prompt, "completion": completion}


def fetch_archives(username: str, session: requests.Session | None = None) -> List[str]:
    session = session or requests.Session()
    resp = session.get(
        CHESS_COM_API.format(username=username),
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json()
    archives = data.get("archives", [])
    if not archives:
        raise ValueError(f"No archives returned for user '{username}'. Is the username correct?")
    return archives


def download_archives(archives: Iterable[str], session: requests.Session | None = None) -> List[Dict[str, Any]]:
    session = session or requests.Session()
    bundles: List[Dict[str, Any]] = []
    for url in archives:
        resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        bundles.append(resp.json())
    return bundles


def chess_data_to_dataframe(archives_json: Sequence[Dict[str, Any]]) -> pd.DataFrame:
    games: List[Dict[str, Any]] = []
    for archive in archives_json:
        for game in archive.get("games", []):
            record: Dict[str, Any] = {
                "TimeClass": game.get("time_class", ""),
                "TimeControl": game.get("time_control", ""),
            }
            pgn = game.get("pgn", "")
            record["pgn"] = pgn
            if pgn:
                headers_to_extract = [
                    "White",
                    "Black",
                    "CurrentPosition",
                    "ECO",
                    "Termination",
                    "Result",
                    "Date",
                ]
                for header in headers_to_extract:
                    match = re.search(rf"\[{header} \"([^\"]+)\"\]", pgn)
                    record[header] = match.group(1) if match else ""

                parts = pgn.split("\n\n", 1)
                if len(parts) == 2:
                    _, moves_section = parts
                    moves_clean = re.sub(r"\{[^}]*\}", "", moves_section)
                    record["MovesRaw"] = moves_clean.strip()
                    record["NumMoves"] = len(re.findall(r"\d+\.", moves_section))
            games.append(record)
    df = pd.DataFrame(games)
    if df.empty:
        raise ValueError("No games with PGN data were found in the downloaded archives.")
    return df


def enrich_with_player_moves(df: pd.DataFrame, username: str) -> pd.DataFrame:
    df = df.copy()
    df["OwnMoves"] = None
    df["OpponentMoves"] = None

    for idx, row in df.iterrows():
        moves_raw = row.get("MovesRaw") or ""
        my_as_white = re.findall(r"\d+\.\s+([^\s]+)", moves_raw)
        opponent_as_black = re.findall(r"\d+\.\.\.\s+([^\s]+)", moves_raw)

        if row.get("White") == username:
            df.at[idx, "OwnMoves"] = my_as_white
            df.at[idx, "OpponentMoves"] = opponent_as_black
        elif row.get("Black") == username:
            df.at[idx, "OwnMoves"] = opponent_as_black
            df.at[idx, "OpponentMoves"] = my_as_white
        else:
            df.at[idx, "OwnMoves"] = []
            df.at[idx, "OpponentMoves"] = []
    return df


def build_training_examples(df: pd.DataFrame, username: str) -> List[TrainingExample]:
    examples: List[TrainingExample] = []
    for game_id, row in df.iterrows():
        own_moves: Sequence[str] = row.get("OwnMoves") or []
        opp_moves: Sequence[str] = row.get("OpponentMoves") or []
        if not own_moves:
            continue

        color = "white" if row.get("White") == username else "black"
        for move_number, move in enumerate(own_moves, start=1):
            example = TrainingExample(
                game_id=str(game_id),
                move_number=move_number,
                my_previous_moves=own_moves[: move_number - 1],
                opponent_previous_moves=opp_moves[: move_number - 1],
                my_move=move,
                time_control=row.get("TimeControl", ""),
                opening=row.get("ECO", ""),
                color=color,
            )
            examples.append(example)
    return examples


def moves_to_history(my_prev: Sequence[str], opp_prev: Sequence[str], color: str) -> str:
    history: List[str] = []
    for index in range(max(len(my_prev), len(opp_prev))):
        white_move = my_prev[index] if index < len(my_prev) else ""
        black_move = opp_prev[index] if index < len(opp_prev) else ""
        move_number = index + 1
        if white_move and black_move:
            history.append(f"{move_number}. {white_move} {black_move}")
        elif white_move:
            history.append(f"{move_number}. {white_move}")
        elif black_move:
            history.append(f"{move_number}. {black_move}")
    return " ".join(history)


def write_examples(examples: Iterable[TrainingExample], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for example in examples:
            obj = example.to_prompt_completion()
            handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="Chess.com username to download games for")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sft_data.jsonl"),
        help="Where to write the JSONL dataset (default: sft_data.jsonl)",
    )
    parser.add_argument(
        "--drop-abandoned",
        action="store_true",
        help="Exclude games with 'abandoned' termination results",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session = requests.Session()
    archives = fetch_archives(args.username, session=session)
    bundles = download_archives(archives, session=session)
    df = chess_data_to_dataframe(bundles)

    if args.drop_abandoned:
        df = df[~df["Termination"].str.contains("abandoned", case=False, na=False)]

    df = enrich_with_player_moves(df, args.username)
    examples = build_training_examples(df, args.username)
    written = write_examples(examples, args.output)

    print(f"Wrote {written} prompt/completion pairs to {args.output}")


if __name__ == "__main__":
    main()
