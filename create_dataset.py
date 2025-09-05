import requests
import json
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time
from tqdm import tqdm

class ChessDataProcessor:
    def __init__(self, username: str, headers: Optional[Dict] = None):
        self.username = username 
        self.headers = headers or {"User-Agent": "InfiniteChessAI"}
        
    def fetch_archives_with_retry(self, max_retries: int = 3) -> List[str]:
        """Fetch game archives with retry logic and error handling."""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f'https://api.chess.com/pub/player/{self.username}/games/archives',
                    headers=self.headers,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()['archives']
            except (requests.RequestException, KeyError) as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def fetch_games_data(self, archives: List[str]) -> List[Dict]:
        """Fetch game data from archives with progress tracking."""
        data = []
        failed_urls = []
        
        for url in tqdm(archives, desc="Fetching game data"):
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                data.append(response.json())
                time.sleep(0.1)  # Rate limiting
            except requests.RequestException as e:
                print(f"Failed to fetch {url}: {e}")
                failed_urls.append(url)
                
        if failed_urls:
            print(f"Warning: Failed to fetch {len(failed_urls)} archives")
            
        return data
    
    def extract_moves_from_pgn(self, pgn: str) -> Tuple[List[str], List[str]]:
        """Extract white and black moves from PGN, handling edge cases."""
        if not pgn:
            return [], []
            
        try:
            # Split PGN into header and moves
            pgn_parts = pgn.split('\n\n', 1)
            if len(pgn_parts) < 2:
                return [], []
                
            moves_section = pgn_parts[1]
            
            # Remove clock times, comments, and variations
            moves_clean = re.sub(r'\{[^}]*\}', '', moves_section)  # Remove {clock} times
            moves_clean = re.sub(r'\([^)]*\)', '', moves_clean)    # Remove variations
            moves_clean = re.sub(r';[^\n]*', '', moves_clean)      # Remove comments
            
            # Extract white moves (format: "1. e4", "2. Nf3", etc.)
            white_moves = re.findall(r'\d+\.\s+([a-zA-Z0-9+#=\-]+)', moves_clean)
            
            # Extract black moves (format: "1... e5", "2... Nc6", etc.)  
            black_moves = re.findall(r'\d+\.\.\.\s+([a-zA-Z0-9+#=\-]+)', moves_clean)
            
            return white_moves, black_moves
            
        except Exception as e:
            print(f"Error extracting moves from PGN: {e}")
            return [], []
    
    def chess_data_to_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Convert raw chess.com API data to structured DataFrame with improved parsing."""
        games_list = []
        
        for archive in tqdm(data, desc="Processing games"):
            if 'games' not in archive:
                continue
                
            for game in archive['games']:
                try:
                    record = {
                        'TimeClass': game.get('time_class', ''),
                        'TimeControl': game.get('time_control', ''),
                        'url': game.get('url', '')
                    }
                    
                    # Extract PGN data
                    pgn = game.get('pgn', '')
                    if not pgn:
                        continue
                        
                    # Extract standard PGN headers
                    headers_to_extract = [
                        'White', 'Black', 'CurrentPosition', 'ECO', 'Termination', 
                        'Result', 'Date', 'WhiteElo', 'BlackElo'
                    ]
                    
                    for header in headers_to_extract:
                        match = re.search(rf'\[{header} "([^"]+)"\]', pgn)
                        record[header] = match.group(1) if match else ''
                    
                    # Extract moves
                    white_moves, black_moves = self.extract_moves_from_pgn(pgn)
                    record['WhiteMoves'] = white_moves
                    record['BlackMoves'] = black_moves
                    record['NumMoves'] = max(len(white_moves), len(black_moves))
                    
                    # Skip very short games (likely abandoned/disconnections)
                    if record['NumMoves'] < 5:
                        continue
                        
                    games_list.append(record)
                    
                except Exception as e:
                    print(f"Error processing game: {e}")
                    continue
        
        df = pd.DataFrame(games_list)
        
        # Filter out abandoned games and other low-quality games
        if not df.empty:
            abandoned_mask = df['Termination'].str.contains('abandoned', case=False, na=False)
            df = df[~abandoned_mask].copy()
            
        return df
    
    def prepare_training_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare training data with proper move sequences."""
        training_data = []
        
        for idx, row in df.iterrows():
            try:
                # Determine if we're playing as white or black
                playing_as_white = row['White'].lower() == self.username
                playing_as_black = row['Black'].lower() == self.username
                
                if not (playing_as_white or playing_as_black):
                    continue
                    
                white_moves = row['WhiteMoves']
                black_moves = row['BlackMoves']
                
                if playing_as_white:
                    my_moves = white_moves
                    opponent_moves = black_moves
                    color = 'white'
                else:
                    my_moves = black_moves
                    opponent_moves = white_moves
                    color = 'black'
                
                # Create training examples for each move
                for move_idx, my_move in enumerate(my_moves):
                    # Get game state up to this point
                    if color == 'white':
                        prev_white = white_moves[:move_idx]
                        prev_black = black_moves[:move_idx]
                    else:
                        prev_white = white_moves[:move_idx + 1]  # Include opponent's current move
                        prev_black = black_moves[:move_idx]
                    
                    training_example = {
                        'game_id': idx,
                        'move_number': move_idx + 1,
                        'prev_white_moves': prev_white,
                        'prev_black_moves': prev_black,
                        'target_move': my_move,
                        'time_control': row['TimeControl'],
                        'opening': row['ECO'],
                        'color': color,
                        'opponent_elo': row['BlackElo'] if playing_as_white else row['WhiteElo'],
                        'my_elo': row['WhiteElo'] if playing_as_white else row['BlackElo']
                    }
                    training_data.append(training_example)
                    
            except Exception as e:
                print(f"Error processing game {idx}: {e}")
                continue
        
        return pd.DataFrame(training_data)
    
    def format_game_history(self, white_moves: List[str], black_moves: List[str]) -> str:
        """Format move history in standard chess notation."""
        history = []
        max_moves = max(len(white_moves), len(black_moves))
        
        for i in range(max_moves):
            move_num = i + 1
            move_str = f"{move_num}."
            
            if i < len(white_moves):
                move_str += f" {white_moves[i]}"
            
            if i < len(black_moves):
                move_str += f" {black_moves[i]}"
                
            history.append(move_str)
        
        return " ".join(history)
    
    def create_training_formats(self, training_df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Create training data in both JSONL and conversational formats."""
        jsonl_data = []
        conversational_data = []
        
        for _, row in training_df.iterrows():
            # Format game history
            game_history = self.format_game_history(
                row['prev_white_moves'], 
                row['prev_black_moves']
            )
            
            # JSONL format (simple prompt-completion)
            prompt = f"Position: {game_history}\nPlaying as {row['color']} (Move {row['move_number']}). Next move:"
            jsonl_example = {
                "prompt": prompt,
                "completion": row['target_move']
            }
            jsonl_data.append(jsonl_example)
            
            # Conversational format for chat models
            system_msg = (
                f"You are a chess AI trained on games by {self.username}. "
                f"Time control: {row['time_control']}, Opening: {row['opening']}, "
                f"Playing as {row['color']}"
            )
            
            user_msg = f"Current position: {game_history}\n\nWhat's your next move?"
            
            conversational_example = {
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": row['target_move']}
                ],
                "metadata": {
                    "game_id": row['game_id'],
                    "move_number": row['move_number'],
                    "opponent_elo": row['opponent_elo'],
                    "my_elo": row['my_elo']
                }
            }
            conversational_data.append(conversational_example)
        
        return jsonl_data, conversational_data
    
    def save_training_data(self, jsonl_data: List[Dict], conversational_data: List[Dict], 
                          output_dir: str = "chess_training_data"):
        """Save training data in multiple formats."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save JSONL format
        jsonl_path = output_path / "training_data.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for example in jsonl_data:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        
        # Save conversational format
        conv_path = output_path / "conversational_data.json"
        with conv_path.open("w", encoding="utf-8") as f:
            json.dump(conversational_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(jsonl_data)} JSONL examples to {jsonl_path}")
        print(f"Saved {len(conversational_data)} conversational examples to {conv_path}")
    
    def process_all(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Complete processing pipeline."""
        print(f"Processing chess data for user: {self.username}")
        
        # Fetch archives
        archives = self.fetch_archives_with_retry()
        print(f"Found {len(archives)} game archives")
        
        # Fetch game data  
        raw_data = self.fetch_games_data(archives)
        
        # Convert to DataFrame
        games_df = self.chess_data_to_dataframe(raw_data)
        print(f"Processed {len(games_df)} valid games")
        
        # Prepare training data
        training_df = self.prepare_training_data(games_df)
        print(f"Created {len(training_df)} training examples")
        
        # Create different formats
        jsonl_data, conversational_data = self.create_training_formats(training_df)
        
        # Save the data
        self.save_training_data(jsonl_data, conversational_data)
        
        return games_df, training_df

# Usage
if __name__ == "__main__":
    processor = ChessDataProcessor('iAMbronze')
    games_df, training_df = processor.process_all()
    
    # Display some statistics
    print(f"\nTraining Data Statistics:")
    print(f"Total examples: {len(training_df)}")
    print(f"Games as White: {len(training_df[training_df['color'] == 'white'])}")
    print(f"Games as Black: {len(training_df[training_df['color'] == 'black'])}")
    print(f"Time controls: {training_df['time_control'].value_counts().to_dict()}")
    print(f"Most common openings: {training_df['opening'].value_counts().head().to_dict()}")