"""Lightweight Flask server that plays random legal moves using python-chess.

This provides a drop-in stand-in for the eventual reinforcement-learning engine so
that the SwiftUI client can be exercised end-to-end.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List

import chess
from flask import Flask, jsonify, request

app = Flask(__name__)

PIECE_MAP: Dict[str, int] = {
    "pawn": chess.PAWN,
    "knight": chess.KNIGHT,
    "bishop": chess.BISHOP,
    "rook": chess.ROOK,
    "queen": chess.QUEEN,
    "king": chess.KING,
}


@dataclass(frozen=True)
class PiecePayload:
    kind: str
    player: str
    row: int
    col: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "PiecePayload":
        return cls(
            kind=data["kind"],
            player=data["player"],
            row=data["pos"]["row"],
            col=data["pos"]["col"],
        )


def board_from_payload(payload: Dict[str, object]) -> chess.Board:
    board = chess.Board.empty()
    pieces: Iterable[PiecePayload] = (
        PiecePayload.from_dict(p) for p in payload.get("board", {}).get("pieces", [])
    )
    for piece in pieces:
        square = chess.square(piece.col, 7 - piece.row)
        piece_type = PIECE_MAP[piece.kind]
        color = chess.WHITE if piece.player == "white" else chess.BLACK
        board.set_piece_at(square, chess.Piece(piece_type, color))

    current_player = payload.get("currentPlayer", "white")
    board.turn = chess.WHITE if current_player == "white" else chess.BLACK
    return board


@app.get("/health")
def health_check():
    return jsonify({"status": "healthy"})


@app.post("/ai-move")
def ai_move():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"success": False, "error": "invalid_json"}), 400

    try:
        board = board_from_payload(payload)
    except Exception as exc:  # pragma: no cover - defensive logging
        return jsonify({"success": False, "error": str(exc)}), 400

    legal_moves: List[chess.Move] = list(board.legal_moves)
    if not legal_moves:
        return jsonify({"success": False, "error": "no_legal_moves"})

    move = random.choice(legal_moves)
    san = board.san(move)
    return jsonify({"success": True, "move": san})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
