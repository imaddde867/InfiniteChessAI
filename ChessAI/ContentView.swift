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
    var kind: Kind
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
        
        if let sel = selected, highlights.contains(p) {
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
        lastAIMove = moveString
        let cleanMove = sanitize(moveString)
        guard !cleanMove.isEmpty else {
            makeRandomLegalMove()
            return
        }
        print("AI attempting move: \(cleanMove)")
        if parseCastling(cleanMove) { return }
        if parsePieceMove(cleanMove) { return }
        if parsePawnMove(cleanMove) { return }
        makeRandomLegalMove()
    }
    
    private func sanitize(_ move: String) -> String {
        move.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "+", with: "")
            .replacingOccurrences(of: "#", with: "")
    }
    
    private func parsePawnMove(_ move: String) -> Bool {
        guard let firstChar = move.first, firstChar.isLetter else { return false }
        var trimmed = move
        var promotion: Kind?
        if let promoIndex = trimmed.firstIndex(of: "=") {
            let promoCharIndex = trimmed.index(after: promoIndex)
            if promoCharIndex < trimmed.endIndex,
               let kind = kind(fromPromotion: trimmed[promoCharIndex]) {
                promotion = kind
            }
            trimmed = String(trimmed[..<promoIndex])
        }
        
        let isCapture = trimmed.contains("x")
        if isCapture {
            return parsePawnCapture(trimmed, promotion: promotion)
        } else {
            return parsePawnAdvance(trimmed, promotion: promotion)
        }
    }
    
    private func parsePawnAdvance(_ move: String, promotion: Kind?) -> Bool {
        guard move.count >= 2,
              let fileChar = move.first,
              let rankChar = move.last,
              let col = fileIndex(from: fileChar),
              let row = rankIndex(from: rankChar) else { return false }
        let target = Position(row: row, col: col)
        let candidates = pieces.filter { $0.player == turn && $0.kind == .pawn && $0.pos.col == col }
        for pawn in candidates where legalDestinations(for: pawn).contains(target) {
            movePiece(pawn, to: target, promoteTo: promotion)
            return true
        }
        return false
    }
    
    private func parsePawnCapture(_ move: String, promotion: Kind?) -> Bool {
        // Example formats: exd5, gxe4
        guard move.count >= 4,
              let sourceFileChar = move.first,
              let sourceCol = fileIndex(from: sourceFileChar) else { return false }
        let destinationPart = move.split(separator: "x", maxSplits: 1, omittingEmptySubsequences: true).last ?? ""
        guard destinationPart.count >= 2,
              let fileChar = destinationPart.last(where: { $0.isLetter }),
              let rankChar = destinationPart.last,
              let destCol = fileIndex(from: fileChar),
              let destRow = rankIndex(from: rankChar) else { return false }
        let target = Position(row: destRow, col: destCol)
        let candidates = pieces.filter {
            $0.player == turn && $0.kind == .pawn && $0.pos.col == sourceCol
        }
        for pawn in candidates where legalDestinations(for: pawn).contains(target) {
            movePiece(pawn, to: target, promoteTo: promotion)
            return true
        }
        return false
    }
    
    private func parsePieceMove(_ move: String) -> Bool {
        guard let pieceChar = move.first,
              let pieceKind = kind(fromPieceNotation: pieceChar) else { return false }
        var remainder = String(move.dropFirst())
        var isCapture = false
        if let captureIndex = remainder.firstIndex(of: "x") {
            isCapture = true
            remainder.remove(at: captureIndex)
        }
      guard remainder.count >= 2 else { return false }
      let destinationPart = String(remainder.suffix(2))
      guard let fileChar = destinationPart.first,
          let rankChar = destinationPart.last,
          let col = fileIndex(from: fileChar),
          let row = rankIndex(from: rankChar) else { return false }
      let destination = Position(row: row, col: col)
      let disambiguation = String(remainder.dropLast(2))
        var candidates = pieces.filter { $0.player == turn && $0.kind == pieceKind }
        if !disambiguation.isEmpty {
            for char in disambiguation {
                if char.isLetter, let expectedCol = fileIndex(from: char) {
                    candidates = candidates.filter { $0.pos.col == expectedCol }
                } else if char.isNumber, let expectedRow = rankIndex(from: char) {
                    candidates = candidates.filter { $0.pos.row == expectedRow }
                }
            }
        }
        candidates = candidates.filter { legalDestinations(for: $0).contains(destination) }
        if isCapture, occupantsPlayer(at: destination) == turn { return false }
        if let piece = candidates.first {
            movePiece(piece, to: destination)
            return true
        }
        return false
    }
    
    private func parseCastling(_ move: String) -> Bool {
        guard move == "O-O" || move == "O-O-O" else { return false }
        // Castling not yet supported.
        return false
    }
    
    private func makeRandomLegalMove() {
        let playerPieces = pieces.filter { $0.player == turn }.shuffled()
        for piece in playerPieces {
            let destinations = legalDestinations(for: piece)
            if let randomDestination = destinations.randomElement() {
                movePiece(piece, to: randomDestination)
                return
            }
        }
        turn = turn == .white ? .black : .white
    }
    
    func reset() {
        pieces = Self.startingLineUp()
        turn = .white  // Human always starts as white
        lastAIMove = nil
        deselect()
    }
    
    // MARK: private
    private func deselect() { selected = nil; highlights = [] }
    
    private func movePiece(_ piece: Piece, to p: Position, promoteTo: Kind? = nil) {
        if let captureIndex = pieces.firstIndex(where: { $0.pos == p }) {
            guard pieces[captureIndex].player != piece.player else { return }
            pieces.remove(at: captureIndex)
        }
        pieces.replace(piece) {
            $0.pos = p
            if let promoteTo { $0.kind = promoteTo }
        }
        turn = turn == .white ? .black : .white
        deselect()
    }
    
    private func legalDestinations(for piece: Piece) -> Set<Position> {
        switch piece.kind {
        case .pawn:
            return pawnDestinations(for: piece)
        case .rook:
            return Set(slidingMoves(from: piece.pos, directions: [(1, 0), (-1, 0), (0, 1), (0, -1)], for: piece))
        case .bishop:
            return Set(slidingMoves(from: piece.pos, directions: [(1, 1), (1, -1), (-1, 1), (-1, -1)], for: piece))
        case .queen:
            return Set(slidingMoves(from: piece.pos,
                                     directions: [(1, 0), (-1, 0), (0, 1), (0, -1),
                                                  (1, 1), (1, -1), (-1, 1), (-1, -1)],
                                     for: piece))
        case .knight:
            let offsets = [(2, 1), (1, 2), (-1, 2), (-2, 1), (-2, -1), (-1, -2), (1, -2), (2, -1)]
            var moves: Set<Position> = []
            for (dr, dc) in offsets {
                let destination = Position(row: piece.pos.row + dr, col: piece.pos.col + dc)
                guard contains(destination) else { continue }
                if let occupant = occupant(of: destination) {
                    if occupant.player != piece.player { moves.insert(destination) }
                } else {
                    moves.insert(destination)
                }
            }
            return moves
        case .king:
            var moves: Set<Position> = []
            for dr in -1...1 {
                for dc in -1...1 where dr != 0 || dc != 0 {
                    let destination = Position(row: piece.pos.row + dr, col: piece.pos.col + dc)
                    guard contains(destination) else { continue }
                    if let occupant = occupant(of: destination) {
                        if occupant.player != piece.player { moves.insert(destination) }
                    } else {
                        moves.insert(destination)
                    }
                }
            }
            return moves
        }
    }
    
    private func pawnDestinations(for piece: Piece) -> Set<Position> {
        var moves: Set<Position> = []
        let direction = piece.player == .white ? -1 : 1
        let startRow = piece.player == .white ? 6 : 1
        let oneForward = Position(row: piece.pos.row + direction, col: piece.pos.col)
        if contains(oneForward) && occupant(of: oneForward) == nil {
            moves.insert(oneForward)
            let twoForward = Position(row: piece.pos.row + 2 * direction, col: piece.pos.col)
            if piece.pos.row == startRow && occupant(of: twoForward) == nil {
                moves.insert(twoForward)
            }
        }
        for deltaCol in [-1, 1] {
            let capturePos = Position(row: piece.pos.row + direction, col: piece.pos.col + deltaCol)
            guard contains(capturePos), let target = occupant(of: capturePos) else { continue }
            if target.player != piece.player {
                moves.insert(capturePos)
            }
        }
        return moves
    }
    
    private func slidingMoves(from start: Position, directions: [(Int, Int)], for piece: Piece) -> [Position] {
        var positions: [Position] = []
        for (dr, dc) in directions {
            var row = start.row + dr
            var col = start.col + dc
            while contains(Position(row: row, col: col)) {
                let destination = Position(row: row, col: col)
                if let occupant = occupant(of: destination) {
                    if occupant.player != piece.player {
                        positions.append(destination)
                    }
                    break
                } else {
                    positions.append(destination)
                }
                row += dr
                col += dc
            }
        }
        return positions
    }
    
    private func contains(_ p: Position) -> Bool { (0..<8).contains(p.row) && (0..<8).contains(p.col) }
    private func occupant(of p: Position) -> Piece? { pieces.first { $0.pos == p } }
    private func occupantsPlayer(at position: Position) -> Player? { occupant(of: position)?.player }
    
    private func fileIndex(from char: Character) -> Int? {
        guard let ascii = char.asciiValue else { return nil }
        let index = Int(ascii - Character("a").asciiValue!)
        return (0..<8).contains(index) ? index : nil
    }
    
    private func rankIndex(from char: Character) -> Int? {
        guard let value = Int(String(char)) else { return nil }
        let index = 8 - value
        return (0..<8).contains(index) ? index : nil
    }
    
    private func kind(fromPieceNotation char: Character) -> Kind? {
        switch char {
        case "K": return .king
        case "Q": return .queen
        case "R": return .rook
        case "B": return .bishop
        case "N": return .knight
        default: return nil
        }
    }
    
    private func kind(fromPromotion char: Character) -> Kind? {
        switch char {
        case "Q": return .queen
        case "R": return .rook
        case "B": return .bishop
        case "N": return .knight
        default: return nil
        }
    }
    
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
