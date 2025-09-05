import SwiftUI

// MARK: - Chess Piece Model
struct ChessPiece: Identifiable, Equatable {
    let id = UUID()
    let type: PieceType
    let color: PieceColor
    var position: ChessPosition
    
    enum PieceType: String, CaseIterable {
        case king = "♔"
        case queen = "♕"
        case rook = "♖"
        case bishop = "♗"
        case knight = "♘"
        case pawn = "♙"
    }
    
    enum PieceColor {
        case white, black
    }
    
    var symbol: String {
        switch (type, color) {
        case (.king, .white): return "♔"
        case (.king, .black): return "♚"
        case (.queen, .white): return "♕"
        case (.queen, .black): return "♛"
        case (.rook, .white): return "♖"
        case (.rook, .black): return "♜"
        case (.bishop, .white): return "♗"
        case (.bishop, .black): return "♝"
        case (.knight, .white): return "♘"
        case (.knight, .black): return "♞"
        case (.pawn, .white): return "♙"
        case (.pawn, .black): return "♟"
        }
    }
}

// MARK: - Chess Position
struct ChessPosition: Equatable {
    let row: Int
    let col: Int
    
    init(row: Int, col: Int) {
        self.row = row
        self.col = col
    }
    
    init?(notation: String) {
        guard notation.count == 2,
              let file = notation.first,
              let rank = notation.last,
              let col = "abcdefgh".firstIndex(of: file),
              let row = Int(String(rank)) else {
            return nil
        }
        self.col = "abcdefgh".distance(from: "abcdefgh".startIndex, to: col)
        self.row = 8 - row
    }
    
    var notation: String {
        let files = "abcdefgh"
        let fileIndex = files.index(files.startIndex, offsetBy: col)
        let file = files[fileIndex]
        let rank = 8 - row
        return "\(file)\(rank)"
    }
}

// MARK: - Game State
class ChessGameState: ObservableObject {
    @Published var pieces: [ChessPiece] = []
    @Published var selectedPiece: ChessPiece?
    @Published var possibleMoves: [ChessPosition] = []
    @Published var currentPlayer: ChessPiece.PieceColor = .white
    @Published var gameStatus: GameStatus = .active
    @Published var moveHistory: [String] = []
    
    enum GameStatus {
        case active
        case check
        case checkmate
        case stalemate
        case draw
    }
    
    init() {
        setupInitialPosition()
    }
    
    private func setupInitialPosition() {
        pieces = [
            // White pieces
            ChessPiece(type: .rook, color: .white, position: ChessPosition(row: 7, col: 0)),
            ChessPiece(type: .knight, color: .white, position: ChessPosition(row: 7, col: 1)),
            ChessPiece(type: .bishop, color: .white, position: ChessPosition(row: 7, col: 2)),
            ChessPiece(type: .queen, color: .white, position: ChessPosition(row: 7, col: 3)),
            ChessPiece(type: .king, color: .white, position: ChessPosition(row: 7, col: 4)),
            ChessPiece(type: .bishop, color: .white, position: ChessPosition(row: 7, col: 5)),
            ChessPiece(type: .knight, color: .white, position: ChessPosition(row: 7, col: 6)),
            ChessPiece(type: .rook, color: .white, position: ChessPosition(row: 7, col: 7)),
        ]
        
        // White pawns
        for col in 0..<8 {
            pieces.append(ChessPiece(type: .pawn, color: .white, position: ChessPosition(row: 6, col: col)))
        }
        
        // Black pieces
        pieces.append(contentsOf: [
            ChessPiece(type: .rook, color: .black, position: ChessPosition(row: 0, col: 0)),
            ChessPiece(type: .knight, color: .black, position: ChessPosition(row: 0, col: 1)),
            ChessPiece(type: .bishop, color: .black, position: ChessPosition(row: 0, col: 2)),
            ChessPiece(type: .queen, color: .black, position: ChessPosition(row: 0, col: 3)),
            ChessPiece(type: .king, color: .black, position: ChessPosition(row: 0, col: 4)),
            ChessPiece(type: .bishop, color: .black, position: ChessPosition(row: 0, col: 5)),
            ChessPiece(type: .knight, color: .black, position: ChessPosition(row: 0, col: 6)),
            ChessPiece(type: .rook, color: .black, position: ChessPosition(row: 0, col: 7)),
        ])
        
        // Black pawns
        for col in 0..<8 {
            pieces.append(ChessPiece(type: .pawn, color: .black, position: ChessPosition(row: 1, col: col)))
        }
    }
    
    func pieceAt(position: ChessPosition) -> ChessPiece? {
        return pieces.first { $0.position == position }
    }
    
    func selectPiece(at position: ChessPosition) {
        if let piece = pieceAt(position: position), piece.color == currentPlayer {
            selectedPiece = piece
            possibleMoves = calculatePossibleMoves(for: piece)
        } else if let selected = selectedPiece, possibleMoves.contains(position) {
            makeMove(from: selected.position, to: position)
        } else {
            deselectPiece()
        }
    }
    
    func deselectPiece() {
        selectedPiece = nil
        possibleMoves = []
    }
    
    private func makeMove(from: ChessPosition, to: ChessPosition) {
        guard let pieceIndex = pieces.firstIndex(where: { $0.position == from }) else { return }
        
        // Remove captured piece if any
        pieces.removeAll { $0.position == to }
        
        // Move the piece
        pieces[pieceIndex].position = to
        
        // Add move to history
        let notation = "\(from.notation)-\(to.notation)"
        moveHistory.append(notation)
        
        // Switch players
        currentPlayer = currentPlayer == .white ? .black : .white
        
        deselectPiece()
    }
    
    private func calculatePossibleMoves(for piece: ChessPiece) -> [ChessPosition] {
        // Simplified move calculation - you'll need to implement proper chess rules
        var moves: [ChessPosition] = []
        let pos = piece.position
        
        switch piece.type {
        case .pawn:
            let direction = piece.color == .white ? -1 : 1
            let newRow = pos.row + direction
            if newRow >= 0 && newRow < 8 {
                let forward = ChessPosition(row: newRow, col: pos.col)
                if pieceAt(position: forward) == nil {
                    moves.append(forward)
                }
            }
        case .rook:
            // Horizontal and vertical moves
            for i in 0..<8 {
                if i != pos.row {
                    moves.append(ChessPosition(row: i, col: pos.col))
                }
                if i != pos.col {
                    moves.append(ChessPosition(row: pos.row, col: i))
                }
            }
        case .king:
            // Adjacent squares
            for rowOffset in -1...1 {
                for colOffset in -1...1 {
                    let newRow = pos.row + rowOffset
                    let newCol = pos.col + colOffset
                    if newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8 && !(rowOffset == 0 && colOffset == 0) {
                        moves.append(ChessPosition(row: newRow, col: newCol))
                    }
                }
            }
        default:
            break
        }
        
        // Filter out moves that would capture own pieces
        return moves.filter { move in
            if let targetPiece = pieceAt(position: move) {
                return targetPiece.color != piece.color
            }
            return true
        }
    }
    
    func resetGame() {
        pieces.removeAll()
        selectedPiece = nil
        possibleMoves = []
        currentPlayer = .white
        gameStatus = .active
        moveHistory = []
        setupInitialPosition()
    }
}

// MARK: - Chess Board View
struct ChessBoardView: View {
    @StateObject private var gameState = ChessGameState()
    
    var body: some View {
        VStack(spacing: 0) {
            // Game Header
            HeaderView(gameState: gameState)
            
            // Chess Board
            VStack(spacing: 0) {
                ForEach(0..<8, id: \.self) { row in
                    HStack(spacing: 0) {
                        ForEach(0..<8, id: \.self) { col in
                            ChessSquareView(
                                position: ChessPosition(row: row, col: col),
                                gameState: gameState
                            )
                        }
                    }
                }
            }
            .aspectRatio(1, contentMode: .fit)
            .background(Color.black)
            .cornerRadius(8)
            .shadow(color: .black.opacity(0.3), radius: 10, x: 0, y: 5)
            
            // Game Controls
            ControlsView(gameState: gameState)
        }
        .padding()
        .background(
            LinearGradient(
                gradient: Gradient(colors: [Color(.systemGray6), Color(.systemGray5)]),
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }
}

// MARK: - Header View
struct HeaderView: View {
    @ObservedObject var gameState: ChessGameState
    
    var body: some View {
        VStack(spacing: 16) {
            HStack {
                Text("iAMbronze Chess AI")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.primary)
                
                Spacer()
                
                Circle()
                    .fill(gameState.currentPlayer == .white ? Color.white : Color.black)
                    .frame(width: 16, height: 16)
                    .overlay(
                        Circle()
                            .stroke(Color.primary, lineWidth: 2)
                    )
            }
            
            HStack {
                VStack(alignment: .leading) {
                    Text("Current Turn")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(gameState.currentPlayer == .white ? "White" : "Black")
                        .font(.headline)
                        .fontWeight(.semibold)
                }
                
                Spacer()
                
                VStack(alignment: .trailing) {
                    Text("Moves")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(gameState.moveHistory.count)")
                        .font(.headline)
                        .fontWeight(.semibold)
                }
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - Chess Square View
struct ChessSquareView: View {
    let position: ChessPosition
    @ObservedObject var gameState: ChessGameState
    
    private var isLightSquare: Bool {
        (position.row + position.col) % 2 == 0
    }
    
    private var isSelected: Bool {
        gameState.selectedPiece?.position == position
    }
    
    private var isPossibleMove: Bool {
        gameState.possibleMoves.contains(position)
    }
    
    var body: some View {
        ZStack {
            Rectangle()
                .fill(squareColor)
                .aspectRatio(1, contentMode: .fit)
            
            if let piece = gameState.pieceAt(position: position) {
                Text(piece.symbol)
                    .font(.system(size: 32))
                    .scaleEffect(isSelected ? 1.1 : 1.0)
                    .animation(.easeInOut(duration: 0.1), value: isSelected)
            }
            
            if isPossibleMove {
                Circle()
                    .fill(Color.green.opacity(0.6))
                    .frame(width: 12, height: 12)
            }
        }
        .overlay(
            Rectangle()
                .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 3)
        )
        .onTapGesture {
            gameState.selectPiece(at: position)
        }
    }
    
    private var squareColor: Color {
        if isSelected {
            return Color.blue.opacity(0.3)
        } else if isPossibleMove {
            return Color.green.opacity(0.2)
        } else {
            return isLightSquare ? Color(.systemGray4) : Color(.systemGray2)
        }
    }
}

// MARK: - Controls View
struct ControlsView: View {
    @ObservedObject var gameState: ChessGameState
    
    var body: some View {
        VStack(spacing: 16) {
            // Game Status
            HStack {
                Label("Status: Active", systemImage: "gamecontroller")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Button("AI Move") {
                    // TODO: Implement AI move
                    print("AI will make a move here")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
            
            // Action Buttons
            HStack(spacing: 16) {
                Button("New Game") {
                    gameState.resetGame()
                }
                .buttonStyle(.bordered)
                .controlSize(.regular)
                
                Spacer()
                
                Button("Undo") {
                    // TODO: Implement undo
                    print("Undo move")
                }
                .buttonStyle(.bordered)
                .controlSize(.regular)
                .disabled(gameState.moveHistory.isEmpty)
                
                Button("Hint") {
                    // TODO: Implement hint system
                    print("Show hint")
                }
                .buttonStyle(.bordered)
                .controlSize(.regular)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - Main App View
struct ContentView: View {
    var body: some View {
        NavigationView {
            ChessBoardView()
                .navigationBarHidden(true)
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }
}
