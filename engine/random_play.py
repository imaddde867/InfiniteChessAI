import pygame
import sys
import random
import math

# Initialize Pygames
pygame.init()

# Constants
WIDTH, HEIGHT = 900, 800
BOARD_SIZE = 8
BOARD_OFFSET_X = 80
BOARD_OFFSET_Y = 80
SQUARE_SIZE = 75
BOARD_WIDTH = SQUARE_SIZE * BOARD_SIZE
BOARD_HEIGHT = SQUARE_SIZE * BOARD_SIZE
FPS = 60

# Colors - matching the reference image
LIGHT_SQUARE = (240, 217, 181)  # Light beige squares
DARK_SQUARE = (181, 136, 99)   # Dark brown squares
COORDINATE_COLOR = (139, 69, 19)  # Brown coordinates
BORDER_COLOR = (160, 82, 45)   # Saddle brown border
HIGHLIGHT = (255, 255, 0, 120)
MOVE_HIGHLIGHT = (50, 205, 50, 100)
DARK_GRAY = (40, 40, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 149, 237)
BUTTON_ACTIVE = (34, 139, 34)
BUTTON_TEXT = (255, 255, 255)

# Set up display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("♔ Infinite Chess AI ♔")

# Clock
clock = pygame.time.Clock()

class ChessBoard:
    def __init__(self):
        # Starting position
        self.board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ]
        self.current_player = 'white'
        self.selected_square = None
        self.last_move = None
        self.move_history = []
        self.animation_pieces = []
        self.captured_pieces = {'white': [], 'black': []}
        
    def draw_board_border(self, surface):
        """Draw the border and coordinates like the reference"""
        # Main border
        border_rect = pygame.Rect(BOARD_OFFSET_X - 35, BOARD_OFFSET_Y - 35, 
                                 BOARD_WIDTH + 70, BOARD_HEIGHT + 70)
        pygame.draw.rect(surface, BORDER_COLOR, border_rect)
        
        # Inner board area
        board_rect = pygame.Rect(BOARD_OFFSET_X - 5, BOARD_OFFSET_Y - 5,
                                BOARD_WIDTH + 10, BOARD_HEIGHT + 10)
        pygame.draw.rect(surface, COORDINATE_COLOR, board_rect)
        
    def draw_coordinates(self, surface):
        """Draw coordinates exactly like the reference"""
        font = pygame.font.Font(None, 28)
        
        # Files (a-h) - top and bottom
        files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for i, file_label in enumerate(files):
            x = BOARD_OFFSET_X + i * SQUARE_SIZE + SQUARE_SIZE // 2
            
            # Top coordinates
            text = font.render(file_label, True, COORDINATE_COLOR)
            text_rect = text.get_rect(center=(x, BOARD_OFFSET_Y - 20))
            surface.blit(text, text_rect)
            
            # Bottom coordinates  
            text_rect = text.get_rect(center=(x, BOARD_OFFSET_Y + BOARD_HEIGHT + 20))
            surface.blit(text, text_rect)
        
        # Ranks (8-1) - left and right
        ranks = ['8', '7', '6', '5', '4', '3', '2', '1']
        for i, rank_label in enumerate(ranks):
            y = BOARD_OFFSET_Y + i * SQUARE_SIZE + SQUARE_SIZE // 2
            
            # Left coordinates
            text = font.render(rank_label, True, COORDINATE_COLOR)
            text_rect = text.get_rect(center=(BOARD_OFFSET_X - 20, y))
            surface.blit(text, text_rect)
            
            # Right coordinates
            text_rect = text.get_rect(center=(BOARD_OFFSET_X + BOARD_WIDTH + 20, y))
            surface.blit(text, text_rect)
    
    def draw_squares(self, surface):
        """Draw the checkered squares"""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                # Alternate colors like a real chess board
                color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                x = BOARD_OFFSET_X + col * SQUARE_SIZE
                y = BOARD_OFFSET_Y + row * SQUARE_SIZE
                rect = pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(surface, color, rect)
                
                # Highlight effects
                if self.last_move and ((row, col) == self.last_move[0] or (row, col) == self.last_move[1]):
                    highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE))
                    highlight_surface.set_alpha(80)
                    highlight_surface.fill(MOVE_HIGHLIGHT)
                    surface.blit(highlight_surface, (x, y))
                
                if self.selected_square == (row, col):
                    highlight_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE))
                    highlight_surface.set_alpha(120)
                    highlight_surface.fill(HIGHLIGHT)
                    surface.blit(highlight_surface, (x, y))
    
    def draw_pieces(self, surface):
        """Draw pieces using the exact symbols from reference"""
        font = pygame.font.Font(None, 55)
        
        # Exact Unicode symbols matching the reference image
        piece_symbols = {
            # White pieces (outlined/hollow)
            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
            # Black pieces (filled/solid)  
            'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
        }
        
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece != '.':
                    symbol = piece_symbols.get(piece, piece)
                    
                    # Color matching reference: dark for both, but white pieces slightly lighter
                    color = (40, 40, 40) if piece.isupper() else (0, 0, 0)
                    
                    x = BOARD_OFFSET_X + col * SQUARE_SIZE + SQUARE_SIZE // 2
                    y = BOARD_OFFSET_Y + row * SQUARE_SIZE + SQUARE_SIZE // 2
                    
                    # Add subtle shadow for depth
                    shadow_text = font.render(symbol, True, (0, 0, 0))
                    shadow_rect = shadow_text.get_rect(center=(x + 1, y + 1))
                    surface.blit(shadow_text, shadow_rect)
                    
                    # Main piece
                    text = font.render(symbol, True, color)
                    text_rect = text.get_rect(center=(x, y))
                    surface.blit(text, text_rect)
        
        # Draw animated pieces
        for anim_piece in self.animation_pieces:
            anim_piece.update()
            anim_piece.draw(surface, font, piece_symbols)
    
    def draw_board(self, surface):
        """Draw the complete board"""
        self.draw_board_border(surface)
        self.draw_squares(surface)
        self.draw_coordinates(surface)
        self.draw_pieces(surface)
    
    def get_all_pieces(self, color):
        """Get all pieces for a color"""
        pieces = []
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.board[row][col]
                if piece != '.':
                    if color == 'white' and piece.isupper():
                        pieces.append((row, col, piece))
                    elif color == 'black' and piece.islower():
                        pieces.append((row, col, piece))
        return pieces
    
    def is_valid_position(self, row, col):
        """Check bounds"""
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE
    
    def get_basic_moves(self, row, col, piece):
        """Get moves for a piece"""
        moves = []
        piece_type = piece.lower()
        
        if piece_type == 'p':  # Pawn
            direction = -1 if piece.isupper() else 1
            start_row = 6 if piece.isupper() else 1
            
            # Forward
            new_row = row + direction
            if self.is_valid_position(new_row, col) and self.board[new_row][col] == '.':
                moves.append((new_row, col))
                # Double move
                if row == start_row:
                    new_row = row + 2 * direction
                    if self.is_valid_position(new_row, col) and self.board[new_row][col] == '.':
                        moves.append((new_row, col))
            
            # Captures
            for dc in [-1, 1]:
                new_row, new_col = row + direction, col + dc
                if self.is_valid_position(new_row, new_col):
                    target = self.board[new_row][new_col]
                    if target != '.' and target.isupper() != piece.isupper():
                        moves.append((new_row, new_col))
        
        elif piece_type == 'r':  # Rook
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for dr, dc in directions:
                for i in range(1, 8):
                    new_row, new_col = row + dr * i, col + dc * i
                    if not self.is_valid_position(new_row, new_col):
                        break
                    target = self.board[new_row][new_col]
                    if target == '.':
                        moves.append((new_row, new_col))
                    else:
                        if target.isupper() != piece.isupper():
                            moves.append((new_row, new_col))
                        break
        
        elif piece_type == 'n':  # Knight
            knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), 
                           (1, -2), (1, 2), (2, -1), (2, 1)]
            for dr, dc in knight_moves:
                new_row, new_col = row + dr, col + dc
                if self.is_valid_position(new_row, new_col):
                    target = self.board[new_row][new_col]
                    if target == '.' or target.isupper() != piece.isupper():
                        moves.append((new_row, new_col))
        
        elif piece_type == 'b':  # Bishop
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                for i in range(1, 8):
                    new_row, new_col = row + dr * i, col + dc * i
                    if not self.is_valid_position(new_row, new_col):
                        break
                    target = self.board[new_row][new_col]
                    if target == '.':
                        moves.append((new_row, new_col))
                    else:
                        if target.isupper() != piece.isupper():
                            moves.append((new_row, new_col))
                        break
        
        elif piece_type == 'q':  # Queen
            directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), 
                         (0, 1), (1, -1), (1, 0), (1, 1)]
            for dr, dc in directions:
                for i in range(1, 8):
                    new_row, new_col = row + dr * i, col + dc * i
                    if not self.is_valid_position(new_row, new_col):
                        break
                    target = self.board[new_row][new_col]
                    if target == '.':
                        moves.append((new_row, new_col))
                    else:
                        if target.isupper() != piece.isupper():
                            moves.append((new_row, new_col))
                        break
        
        elif piece_type == 'k':  # King
            directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), 
                         (0, 1), (1, -1), (1, 0), (1, 1)]
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                if self.is_valid_position(new_row, new_col):
                    target = self.board[new_row][new_col]
                    if target == '.' or target.isupper() != piece.isupper():
                        moves.append((new_row, new_col))
        
        return moves
    
    def get_all_legal_moves(self, color):
        """Get all legal moves"""
        all_moves = []
        pieces = self.get_all_pieces(color)
        
        for row, col, piece in pieces:
            moves = self.get_basic_moves(row, col, piece)
            for move_row, move_col in moves:
                all_moves.append(((row, col), (move_row, move_col)))
        
        return all_moves
    
    def make_move(self, from_pos, to_pos, animate=True):
        """Make a move with animation"""
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        
        piece = self.board[from_row][from_col]
        captured = self.board[to_row][to_col]
        
        # Record capture
        if captured != '.':
            color = 'white' if captured.isupper() else 'black'
            self.captured_pieces[color].append(captured)
        
        if animate:
            start_x = BOARD_OFFSET_X + from_col * SQUARE_SIZE + SQUARE_SIZE // 2
            start_y = BOARD_OFFSET_Y + from_row * SQUARE_SIZE + SQUARE_SIZE // 2
            end_x = BOARD_OFFSET_X + to_col * SQUARE_SIZE + SQUARE_SIZE // 2
            end_y = BOARD_OFFSET_Y + to_row * SQUARE_SIZE + SQUARE_SIZE // 2
            
            anim_piece = AnimatedPiece(piece, start_x, start_y, end_x, end_y)
            self.animation_pieces.append(anim_piece)
        
        # Make the move
        self.board[from_row][from_col] = '.'
        self.board[to_row][to_col] = piece
        
        self.last_move = (from_pos, to_pos)
        self.move_history.append((from_pos, to_pos, piece, captured))
        
        # Switch players
        self.current_player = 'black' if self.current_player == 'white' else 'white'
    
    def make_random_move(self):
        """Make random move"""
        legal_moves = self.get_all_legal_moves(self.current_player)
        if legal_moves:
            move = random.choice(legal_moves)
            self.make_move(move[0], move[1])
            return move
        return None
    
    def reset_game(self):
        """Reset everything"""
        self.__init__()

class AnimatedPiece:
    def __init__(self, piece, start_x, start_y, end_x, end_y, duration=600):
        self.piece = piece
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.current_x = start_x
        self.current_y = start_y
        self.duration = duration
        self.elapsed = 0
        self.finished = False
        self.scale = 1.0
        self.rotation = 0
    
    def update(self):
        """Update with enhanced animation"""
        if not self.finished:
            self.elapsed += clock.get_time()
            progress = min(self.elapsed / self.duration, 1.0)
            
            # Smooth cubic easing
            eased_progress = 1 - (1 - progress) ** 3
            
            # Position interpolation
            self.current_x = self.start_x + (self.end_x - self.start_x) * eased_progress
            self.current_y = self.start_y + (self.end_y - self.start_y) * eased_progress
            
            # Add subtle scaling effect
            self.scale = 1.0 + 0.2 * math.sin(progress * math.pi)
            
            if progress >= 1.0:
                self.finished = True
    
    def draw(self, surface, font, piece_symbols):
        """Draw animated piece with effects"""
        if not self.finished:
            symbol = piece_symbols.get(self.piece, self.piece)
            color = (40, 40, 40) if self.piece.isupper() else (0, 0, 0)
            
            # Scale font size for animation
            scaled_size = int(55 * self.scale)
            anim_font = pygame.font.Font(None, scaled_size)
            
            # Shadow
            shadow_text = anim_font.render(symbol, True, (100, 100, 100))
            shadow_rect = shadow_text.get_rect(center=(int(self.current_x + 2), int(self.current_y + 2)))
            surface.blit(shadow_text, shadow_rect)
            
            # Main piece
            text = anim_font.render(symbol, True, color)
            text_rect = text.get_rect(center=(int(self.current_x), int(self.current_y)))
            surface.blit(text, text_rect)

class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False
        self.pressed = False
        self.font = pygame.font.Font(None, 28)
        self.active = False
    
    def handle_event(self, event):
        """Enhanced button handling"""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.rect.collidepoint(event.pos) and self.pressed and self.action:
                self.action()
            self.pressed = False
    
    def draw(self, surface):
        """Draw with enhanced styling"""
        if self.active:
            color = BUTTON_ACTIVE
        elif self.pressed:
            color = (50, 100, 150)
        elif self.hovered:
            color = BUTTON_HOVER
        else:
            color = BUTTON_COLOR
        
        # Draw button with border
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 3)
        
        # Add pressed effect
        offset = 2 if self.pressed else 0
        
        text_surface = self.font.render(self.text, True, BUTTON_TEXT)
        text_rect = text_surface.get_rect(center=(self.rect.centerx + offset, self.rect.centery + offset))
        surface.blit(text_surface, text_rect)

# Game state
class GameState:
    def __init__(self):
        self.auto_play = False
        self.paused = False
        self.move_timer = 0
        self.move_delay = 1500  # Slower for better viewing

# Initialize
board = ChessBoard()
game_state = GameState()

# Button actions
def start_stop():
    game_state.auto_play = not game_state.auto_play
    game_state.paused = False

def pause_resume():
    if game_state.auto_play:
        game_state.paused = not game_state.paused

def reset_game():
    board.reset_game()
    game_state.auto_play = False
    game_state.paused = False

# Create buttons
buttons = [
    Button(WIDTH - 180, 100, 150, 50, "▶ START", start_stop),
    Button(WIDTH - 180, 170, 150, 50, "⏸ PAUSE", pause_resume), 
    Button(WIDTH - 180, 240, 150, 50, "🔄 RESET", reset_game)
]

# Main game loop
running = True
while running:
    dt = clock.tick(FPS)
    
    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        for button in buttons:
            button.handle_event(event)
    
    # Update button states
    buttons[0].active = game_state.auto_play
    buttons[1].active = game_state.paused
    
    # Clean up finished animations
    board.animation_pieces = [p for p in board.animation_pieces if not p.finished]
    
    # Game logic
    if game_state.auto_play and not game_state.paused:
        game_state.move_timer += dt
        if game_state.move_timer >= game_state.move_delay:
            move = board.make_random_move()
            if move:
                from_pos, to_pos = move
                notation = f"{chr(97+from_pos[1])}{8-from_pos[0]}→{chr(97+to_pos[1])}{8-to_pos[0]}"
                print(f"🔥 {board.current_player.title()}: {notation}")
            else:
                print(f"❌ No moves for {board.current_player}")
                game_state.auto_play = False
            game_state.move_timer = 0
    
    # Draw everything
    screen.fill(DARK_GRAY)
    board.draw_board(screen)
    
    # UI Panel
    panel_rect = pygame.Rect(WIDTH - 200, 50, 180, 400)
    pygame.draw.rect(screen, (60, 60, 60), panel_rect)
    pygame.draw.rect(screen, WHITE, panel_rect, 2)
    
    # Title
    title_font = pygame.font.Font(None, 32)
    title = title_font.render("♔ CHESS AI ♔", True, WHITE)
    title_rect = title.get_rect(center=(WIDTH - 110, 75))
    screen.blit(title, title_rect)
    
    # Status info
    info_font = pygame.font.Font(None, 24)
    y_offset = 320
    
    # Current player
    player_color = (255, 215, 0) if board.current_player == 'white' else (192, 192, 192)
    player_text = info_font.render(f"Turn: {board.current_player.title()}", True, player_color)
    screen.blit(player_text, (WIDTH - 190, y_offset))
    
    # Game status
    if game_state.auto_play:
        status = "🔴 PAUSED" if game_state.paused else "🟢 RUNNING"
        color = (255, 255, 0) if game_state.paused else (0, 255, 0)
    else:
        status = "⚫ STOPPED"
        color = (255, 100, 100)
    
    status_text = info_font.render(status, True, color)
    screen.blit(status_text, (WIDTH - 190, y_offset + 25))
    
    # Move count
    moves_text = info_font.render(f"Moves: {len(board.move_history)}", True, WHITE)
    screen.blit(moves_text, (WIDTH - 190, y_offset + 50))
    
    # Captures
    white_captures = len(board.captured_pieces['black'])
    black_captures = len(board.captured_pieces['white'])
    captures_text = info_font.render(f"Captures: ♔{white_captures} ♚{black_captures}", True, WHITE)
    screen.blit(captures_text, (WIDTH - 190, y_offset + 75))
    
    # Draw buttons
    for button in buttons:
        button.draw(screen)
    
    pygame.display.flip()

pygame.quit()
sys.exit()
