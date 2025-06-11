#!/usr/bin/env python3
"""
Enhanced Random Chess Engine using python-chess

This engine:
1. Uses chess.Board() to initialize a board
2. Loops while the game is not over
3. Picks and plays random legal moves for each side
4. Prints move history and game result
5. Optionally prints board state
6. Optionally saves games to PGN in /data/games/

Author: BlueUwu
Project: InfiniteChessAI
"""

import chess
import chess.pgn
import random
import os
import datetime
from pathlib import Path

class RandomChessEngine:
    """Enhanced Random Chess Engine using python-chess library"""

    def __init__(self, display_board=True, save_pgn=True):
        """
        Initialize the random chess engine

        Args:
            display_board (bool): Whether to print board after each move
            save_pgn (bool): Whether to save games to PGN files
        """
        self.display_board = display_board
        self.save_pgn = save_pgn
        self.games_played = 0

        # Ensure data/games directory exists
        if self.save_pgn:
            Path("data/games").mkdir(parents=True, exist_ok=True)

    def play_random_game(self):
        """Play a complete random chess game"""
        # Initialize chess board
        board = chess.Board()
        move_count = 0

        print("🎯 Starting new random chess game...")
        print("=" * 50)

        if self.display_board:
            print("Initial position:")
            print(board)
            print()

        # Game loop - continue while game is not over
        while not board.is_game_over():
            # Get all legal moves for current player
            legal_moves = list(board.legal_moves)

            if not legal_moves:
                break  # No legal moves available

            # Pick a random legal move
            random_move = random.choice(legal_moves)

            # Make the move
            board.push(random_move)
            move_count += 1

            # Print move information
            current_player = "White" if board.turn else "Black"
            previous_player = "Black" if board.turn else "White"

            print(f"Move {move_count}: {previous_player} plays {random_move}")

            # Optionally display board
            if self.display_board:
                print(f"\nBoard after {previous_player}'s move:")
                print(board)
                print()

        # Game is over - determine and print result
        self._print_game_result(board, move_count)

        # Save game to PGN if enabled
        if self.save_pgn:
            self._save_game_to_pgn(board)

        self.games_played += 1
        return board

    def _print_game_result(self, board, move_count):
        """Print the final game result and statistics"""
        print("=" * 50)
        print("🏁 GAME OVER!")
        print(f"Total moves played: {move_count}")

        # Determine game result
        if board.is_checkmate():
            winner = "Black" if board.turn else "White"
            print(f"🎉 {winner} wins by checkmate!")
        elif board.is_stalemate():
            print("🤝 Game ended in stalemate (draw)")
        elif board.is_insufficient_material():
            print("🤝 Draw due to insufficient material")
        elif board.is_seventyfive_moves():
            print("🤝 Draw due to 75-move rule")
        elif board.is_fivefold_repetition():
            print("🤝 Draw due to fivefold repetition")
        else:
            print("🤝 Game ended in draw")

        print("=" * 50)
        print()

    def _save_game_to_pgn(self, board):
        """Save the completed game to a PGN file"""
        try:
            # Create PGN game object
            game = chess.pgn.Game()

            # Set game headers
            game.headers["Event"] = "Random Chess Game"
            game.headers["Site"] = "InfiniteChessAI"
            game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
            game.headers["Round"] = str(self.games_played + 1)
            game.headers["White"] = "RandomEngine"
            game.headers["Black"] = "RandomEngine"

            # Determine result
            if board.is_checkmate():
                result = "0-1" if board.turn else "1-0"
            else:
                result = "1/2-1/2"
            game.headers["Result"] = result

            # Add moves to the game
            node = game
            temp_board = chess.Board()
            for move in board.move_stack:
                node = node.add_variation(move)
                temp_board.push(move)

            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/games/random_game_{timestamp}.pgn"

            # Save to file
            with open(filename, "w") as pgn_file:
                print(game, file=pgn_file)

            print(f"💾 Game saved to: {filename}")

        except Exception as e:
            print(f"❌ Error saving PGN: {e}")

    def play_multiple_games(self, num_games=5):
        """Play multiple random chess games"""
        print(f"🚀 Playing {num_games} random chess games...")
        print()

        results = {"White": 0, "Black": 0, "Draw": 0}

        for game_num in range(num_games):
            print(f"🎮 Game {game_num + 1}/{num_games}")
            board = self.play_random_game()

            # Track results
            if board.is_checkmate():
                winner = "Black" if board.turn else "White"
                results[winner] += 1
            else:
                results["Draw"] += 1

            print()

        # Print final statistics
        print("📊 FINAL STATISTICS")
        print("=" * 50)
        print(f"Games played: {num_games}")
        print(f"White wins: {results['White']}")
        print(f"Black wins: {results['Black']}")
        print(f"Draws: {results['Draw']}")
        print(f"White win rate: {results['White']/num_games*100:.1f}%")
        print(f"Black win rate: {results['Black']/num_games*100:.1f}%")
        print(f"Draw rate: {results['Draw']/num_games*100:.1f}%")
        print("=" * 50)


def main():
    """Main function to run the random chess engine"""
    print("♔ Enhanced Random Chess Engine ♔")
    print("Using python-chess library")
    print("=" * 50)
    print()

    # Create engine instance
    # Set display_board=True to see board after each move
    # Set save_pgn=True to save games to data/games/
    engine = RandomChessEngine(display_board=False, save_pgn=True)

    while True:
        print("Choose an option:")
        print("1. Play a single random game")
        print("2. Play multiple random games")
        print("3. Play a game with board display")
        print("4. Exit")
        print()

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            print()
            engine.play_random_game()
            print()

        elif choice == "2":
            try:
                num_games = int(input("How many games to play? (default: 5): ") or "5")
                print()
                engine.play_multiple_games(num_games)
                print()
            except ValueError:
                print("❌ Invalid number. Using default of 5 games.")
                engine.play_multiple_games(5)
                print()

        elif choice == "3":
            print()
            # Create engine with board display enabled
            display_engine = RandomChessEngine(display_board=True, save_pgn=True)
            display_engine.play_random_game()
            print()

        elif choice == "4":
            print("👋 Thanks for using the Random Chess Engine!")
            break

        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
            print()


if __name__ == "__main__":
    main()