//
//  MinimalChess.swift
//  iOS 17+, SwiftUI 5
//

import SwiftUI

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

// MARK: - Board & Rules
@MainActor
final class Board: ObservableObject {
    @Published private(set) var pieces: [Piece] = []
    @Published private(set) var turn: Player = .white
    @Published private(set) var selected: Piece?
    @Published private(set) var highlights: Set<Position> = []
    
    init() { reset() }
    
    func tap(at p: Position) {
        if let sel = selected, highlights.contains(p) { move(sel, to: p); return }
        deselect()
        if let piece = pieces.first(where: { $0.pos == p && $0.player == turn }) {
            selected = piece
            highlights = legalDestinations(for: piece)
        }
    }
    
    func reset() {
        pieces = Self.startingLineUp()
        turn = .white
        deselect()
    }
    
    // MARK: private
    private func deselect() { selected = nil; highlights = [] }
    
    private func move(_ piece: Piece, to p: Position) {
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

// MARK: - UI
struct ChessView: View {
    @StateObject private var board = Board()
    var body: some View {
        GeometryReader { geo in
            VStack(spacing: 0) {
                header
                Spacer()
                boardBody(geo)
                Spacer()
                controls
            }
            .background(.ultraThinMaterial)
        }
        .preferredColorScheme(.dark)
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
            Button("New Game") { board.reset() }
            Spacer()
            Button("AI Move") { }.disabled(true)
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
