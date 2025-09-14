//
//  MinimalChess.swift
//  iOS 17+, SwiftUI 5
//

import SwiftUI
import Foundation

// MARK: - Domain
struct Position: Hashable { var row: Int; var col: Int }

enum Player { case white, black }
enum Kind: String, CaseIterable { case pawn, knight, bishop, rook, queen, king }

struct Piece: Identifiable, Hashable {
    let id = UUID()
    let player: Player
    let kind: Kind
    var pos: Position
    
    var glyph: String {
        switch (player, kind) {
        case (.white, .king): "♔"; case (.black, .king): "♚"
        case (.white, .queen): "♕"; case (.black, .queen): "♛"
        case (.white, .rook): "♖"; case (.black, .rook): "♜"
        case (.white, .bishop): "♗"; case (.black, .bishop): "♝"
        case (.white, .knight): "♘"; case (.black, .knight): "♞"
        case (.white, .pawn): "♙"; case (.black, .pawn): "♟"
        }
    }
}

// MARK: - AI Service
class ChessAIService: ObservableObject {
    private let serverURL = "http://localhost:5000"
    @Published var isThinking = false
    @Published var lastError: String?
    
    func requestAIMove(board: Board) async -> String? {
        await MainActor.run { isThinking = true }
        defer { Task { @MainActor in isThinking = false } }
        
        do {
            guard let url = URL(string: "\(serverURL)/ai-move") else { return nil }
            
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            
            let pieces = await MainActor.run { board.pieces }
            let currentTurn = await MainActor.run { board.turn }
            
            let boardData: [String: Any] = [
                "board": [
                    "pieces": pieces.map { piece in
                        [
                            "kind": piece.kind.rawValue,
                            "player": piece.player == .white ? "white" : "black",
                            "pos": ["row": piece.pos.row, "col": piece.pos.col]
                        ] as [String: Any]
                    }
                ] as [String: Any],
                "currentPlayer": currentTurn == .white ? "white" : "black"
            ]
            
            request.httpBody = try JSONSerialization.data(withJSONObject: boardData)
            
            let (data, _) = try await URLSession.shared.data(for: request)
            
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let success = json["success"] as? Bool,
               success,
               let move = json["move"] as? String {
                await MainActor.run { lastError = nil }
                return move
            }
            
        } catch {
            await MainActor.run { lastError = error.localizedDescription }
        }
        
        return nil
    }
    
    func checkServerHealth() async -> Bool {
        do {
            guard let url = URL(string: "\(serverURL)/health") else { return false }
            let (data, _) = try await URLSession.shared.data(from: url)
            
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let status = json["status"] as? String {
                return status == "healthy"
            }
        } catch {
            print("Health check failed: \(error)")
        }
        return false
    }
}
@MainActor
final class Board: ObservableObject {
    @Published private(set) var pieces: [Piece] = []
    @Published private(set) var turn: Player = .white
    @Published private(set) var selected: Piece?
    @Published private(set) var highlights: Set<Position> = []
    @Published var aiEnabled = false
    @Published var lastAIMove: String?
    
    init() { reset() }
    
    func tap(at p: Position) {
        // Only allow human player (white) to make moves manually
        guard turn == .white else { return }
        
        if let sel = selected, highlightƒs.contains(p) { 
            movePiece(sel, to: p)
            // After human move, trigger AI move if it's now black's turn
            if turn == .black {
                triggerAIMove()
            }
            return 
        }
        deselect()
        if let piece = pieces.first(where: { $0.pos == p && $0.player == turn }) {
            selected = piece
            highlights = legalDestinations(for: piece)
        }
    }
    
    private func triggerAIMove() {
        // This will be called from the view when it's the AI's turn
        NotificationCenter.default.post(name: .aiTurnNotification, object: nil)
    }
    
    func makeAIMove(_ moveString: String) {
        // Parse move string and execute it
        lastAIMove = moveString
        
        // Clean the move string
        let cleanMove = moveString.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "+", with: "")
            .replacingOccurrences(of: "#", with: "")
        
        print("AI attempting move: \(cleanMove)")
        
        // Try to parse different move formats
        if parsePawnMove(cleanMove) { return }
        if parsePieceMove(cleanMove) { return }
        if parseCastling(cleanMove) { return }
        
        // If all parsing fails, make a random legal move
        makeRandomLegalMove()
    }
    
    private func parsePawnMove(_ move: String) -> Bool {
        // Handle pawn moves like "e4", "d5"
        guard move.count >= 2,
              let firstChar = move.first,
              firstChar.isLetter && firstChar.isLowercase,
              let secondChar = move.dropFirst().first,
              secondChar.isNumber else { return false }
        
        let col = Int(firstChar.asciiValue! - Character("a").asciiValue!)
        let row = 8 - Int(String(secondChar))!
        
        guard (0..<8).contains(col) && (0..<8).contains(row) else { return false }
        
        // Find a pawn that can move to this position
        if let pawn = pieces.first(where: { 
            $0.kind == .pawn && 
            $0.player == turn &&
            $0.pos.col == col &&
            canMovePawnTo(pawn: $0, destination: Position(row: row, col: col))
        }) {
            movePiece(pawn, to: Position(row: row, col: col))
            return true
        }
        
        return false
    }
    
    private func parsePieceMove(_ move: String) -> Bool {
        // Handle piece moves like "Nf3", "Bb5", etc.
        guard move.count >= 3,
              let pieceChar = move.first,
              "KQRBN".contains(pieceChar) else { return false }
        
        let pieceKind: Kind
        switch pieceChar {
        case "K": pieceKind = .king
        case "Q": pieceKind = .queen
        case "R": pieceKind = .rook
        case "B": pieceKind = .bishop
        case "N": pieceKind = .knight
        default: return false
        }
        
        let destination = String(move.dropFirst())
        guard destination.count >= 2,
              let fileChar = destination.first,
              let rankChar = destination.dropFirst().first,
              fileChar.isLetter && fileChar.isLowercase,
              rankChar.isNumber else { return false }
        
        let col = Int(fileChar.asciiValue! - Character("a").asciiValue!)
        let row = 8 - Int(String(rankChar))!
        
        guard (0..<8).contains(col) && (0..<8).contains(row) else { return false }
        
        let targetPos = Position(row: row, col: col)
        
        // Find the piece that can move to this position
        if let piece = pieces.first(where: { 
            $0.kind == pieceKind && 
            $0.player == turn &&
            legalDestinations(for: $0).contains(targetPos)
        }) {
            movePiece(piece, to: targetPos)
            return true
        }
        
        return false
    }
    
    private func parseCastling(_ move: String) -> Bool {
        // Handle castling moves "O-O" (kingside) or "O-O-O" (queenside)
        guard move == "O-O" || move == "O-O-O" else { return false }
        
        // For now, just return false - castling is complex to implement
        // In a full implementation, you'd check if castling is legal and execute it
        return false
    }
    
    private func makeRandomLegalMove() {
        // Find all pieces of the current player
        let playerPieces = pieces.filter { $0.player == turn }
        
        // Find all legal moves
        for piece in playerPieces {
            let destinations = legalDestinations(for: piece)
            if let randomDestination = destinations.randomElement() {
                movePiece(piece, to: randomDestination)
                return
            }
        }
        
        // If no legal moves found, just pass the turn
        turn = turn == .white ? .black : .white
    }
    
    private func canMovePawnTo(pawn: Piece, destination: Position) -> Bool {
        let direction = pawn.player == .white ? -1 : 1
        let oneStep = Position(row: pawn.pos.row + direction, col: pawn.pos.col)
        let twoStep = Position(row: pawn.pos.row + 2 * direction, col: pawn.pos.col)
        
        // Check if destination is one step forward and empty
        if destination == oneStep && occupant(of: destination) == nil {
            return true
        }
        
        // Check if destination is two steps forward (from starting position) and empty
        let startingRow = pawn.player == .white ? 6 : 1
        if pawn.pos.row == startingRow && destination == twoStep && occupant(of: destination) == nil {
            return true
        }
        
        return false
    }
    
    func reset() {
        pieces = Self.startingLineUp()
        turn = .white  // Human always starts as white
        lastAIMove = nil
        deselect()
    }
    
    // MARK: private
    private func deselect() { selected = nil; highlights = [] }
    
    private func movePiece(_ piece: Piece, to p: Position) {
        pieces.removeAll { $0.pos == p }
        pieces.replace(piece) { $0.pos = p }
        turn = turn == .white ? .black : .white
        deselect()
    }
    
    private func legalDestinations(for piece: Piece) -> Set<Position> {
        var set = Set<Position>()
        switch piece.kind {
        case .pawn:
            let dir = piece.player == .white ? -1 : 1
            let one = Position(row: piece.pos.row + dir, col: piece.pos.col)
            if contains(one) && occupant(of: one) == nil { set.insert(one) }
        case .rook:
            for dst in straightLine(from: piece.pos, ΔRow: 1, ΔCol: 0) { set.insert(dst) }
            for dst in straightLine(from: piece.pos, ΔRow: -1, ΔCol: 0) { set.insert(dst) }
            for dst in straightLine(from: piece.pos, ΔRow: 0, ΔCol: 1) { set.insert(dst) }
            for dst in straightLine(from: piece.pos, ΔRow: 0, ΔCol: -1) { set.insert(dst) }
        case .king:
            for dr in -1...1 { for dc in -1...1 where dr != 0 || dc != 0 {
                let dst = Position(row: piece.pos.row + dr, col: piece.pos.col + dc)
                if contains(dst), occupant(of: dst)?.player != piece.player { set.insert(dst) }
            }}
        default: break
        }
        return set
    }
    
    private func straightLine(from: Position, ΔRow: Int, ΔCol: Int) -> [Position] {
        var arr: [Position] = [], r = from.row + ΔRow, c = from.col + ΔCol
        while contains(Position(row: r, col: c)) {
            let p = Position(row: r, col: c)
            arr.append(p)
            if occupant(of: p) != nil { break }
            r += ΔRow; c += ΔCol
        }
        return arr
    }
    
    private func contains(_ p: Position) -> Bool { (0..<8).contains(p.row) && (0..<8).contains(p.col) }
    private func occupant(of p: Position) -> Piece? { pieces.first { $0.pos == p } }
    
    private static func startingLineUp() -> [Piece] {
        func backRow(_ player: Player, _ row: Int) -> [Piece] {
            [Kind.rook, .knight, .bishop, .queen, .king, .bishop, .knight, .rook]
                .enumerated().map { Piece(player: player, kind: $1, pos: Position(row: row, col: $0)) }
        }
        func pawnRow(_ player: Player, _ row: Int) -> [Piece] {
            (0..<8).map { Piece(player: player, kind: .pawn, pos: Position(row: row, col: $0)) }
        }
        return backRow(.white, 7) + pawnRow(.white, 6) + pawnRow(.black, 1) + backRow(.black, 0)
    }
}

// MARK: - Notification Extension
extension Notification.Name {
    static let aiTurnNotification = Notification.Name("aiTurnNotification")
}

// MARK: - UI
struct ChessView: View {
    @StateObject private var board = Board()
    @StateObject private var aiService = ChessAIService()
    
    var body: some View {
        GeometryReader { geo in
            VStack(spacing: 0) {
                header
                gameStatus
                Spacer()
                boardBody(geo)
                Spacer()
                controls
            }
            .background(.ultraThinMaterial)
            .task {
                // Check if AI server is available on app launch
                board.aiEnabled = await aiService.checkServerHealth()
            }
            .onReceive(NotificationCenter.default.publisher(for: .aiTurnNotification)) { _ in
                // Automatically make AI move when it's the AI's turn
                if board.turn == .black && board.aiEnabled && !aiService.isThinking {
                    Task {
                        if let move = await aiService.requestAIMove(board: board) {
                            await MainActor.run {
                                board.makeAIMove(move)
                            }
                        }
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
    
    private var gameStatus: some View {
        VStack(spacing: 4) {
            HStack {
                Text("You: ♔ White")
                    .foregroundColor(board.turn == .white ? .primary : .secondary)
                Spacer()
                Text("AI: ♚ Black")
                    .foregroundColor(board.turn == .black ? .primary : .secondary)
            }
            .font(.caption)
            .padding(.horizontal, 24)
            
            if let lastMove = board.lastAIMove {
                Text("AI played: \(lastMove)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            } else if board.turn == .black && aiService.isThinking {
                HStack(spacing: 4) {
                    ProgressView()
                        .scaleEffect(0.6)
                    Text("AI is thinking...")
                        .font(.caption2)
                }
                .foregroundColor(.secondary)
            } else if board.turn == .white {
                Text("Your turn - tap a piece to move")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 8)
    }
    
    private var header: some View {
        HStack {
            Label("Chess", systemImage: "crown.fill").font(.title3.bold())
            Spacer()
            TurnIndicator(player: board.turn)
        }
        .padding(.horizontal, 24).padding(.vertical, 12)
    }
    
    private func boardBody(_ geo: GeometryProxy) -> some View {
        let side = min(geo.size.width, geo.size.height) * 0.9
        return VStack(spacing: 0) {
            ForEach(0..<8, id: \.self) { row in
                HStack(spacing: 0) {
                    ForEach(0..<8, id: \.self) { col in
                        Square(pos: Position(row: row, col: col))
                    }
                }
            }
        }
        .frame(width: side, height: side)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.2), radius: 10)
        .environmentObject(board)
    }
    
    private var controls: some View {
        HStack {
            Button("New Game") { 
                board.reset() 
                Task {
                    board.aiEnabled = await aiService.checkServerHealth()
                }
            }
            
            Spacer()
            
            // Show connection status
            HStack(spacing: 4) {
                Circle()
                    .fill(board.aiEnabled ? .green : .red)
                    .frame(width: 8, height: 8)
                Text(board.aiEnabled ? "AI Connected" : "AI Offline")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.large)
        .padding(.horizontal, 24).padding(.bottom, 8)
    }
}

struct Square: View {
    let pos: Position
    @EnvironmentObject private var board: Board
    private var piece: Piece? { board.pieces.first { $0.pos == pos } }
    private var isLight: Bool { (pos.row + pos.col).isMultiple(of: 2) }
    private var isSelected: Bool { board.selected?.pos == pos }
    private var isHighlight: Bool { board.highlights.contains(pos) }
    
    var body: some View {
        ZStack {
            Color(isLight ? UIColor.systemGray5 : UIColor.systemGray6)
                .overlay(selectionOverlay)
            pieceView
            highlightDot
        }
        .onTapGesture { board.tap(at: pos) }
    }
    
    @ViewBuilder
    private var selectionOverlay: some View {
        if isSelected { Color.accentColor.opacity(0.35) }
    }
    
    @ViewBuilder
    private var pieceView: some View {
        if let piece {
            Text(piece.glyph)
                .font(.system(size: 36))
                .scaleEffect(isSelected ? 1.15 : 1)
                .animation(.spring(response: 0.2, dampingFraction: 0.6), value: isSelected)
        }
    }
    
    @ViewBuilder
    private var highlightDot: some View {
        if isHighlight && piece == nil {
            Circle().fill(Color.accentColor).frame(width: 10, height: 10)
        }
    }
}

struct TurnIndicator: View {
    let player: Player
    var body: some View {
        Circle()
            .stroke(Color.primary, lineWidth: 2)
            .background(Circle().fill(player == .white ? Color.white : Color.black))
            .frame(width: 18, height: 18)
    }
}

// MARK: - App
@main
struct MinimalChessApp: App {
    var body: some Scene {
        WindowGroup { ChessView().ignoresSafeArea(.keyboard) }
    }
}

// MARK: - Helper
extension Array where Element == Piece {
    fileprivate mutating func replace(_ piece: Piece, _ update: (inout Piece) -> Void) {
        if let idx = firstIndex(where: { $0.id == piece.id }) {
            update(&self[idx])
        }
    }
}
