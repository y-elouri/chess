import unittest
import chess

initial_position = {
    ('\u265C', 21): set(),
    ('\u265E', 22): {41, 43},
    ('\u265D', 23): set(),
    ('\u265B', 24): set(),
    ('\u265A', 25): set(),
    ('\u265D', 26): set(),
    ('\u265E', 27): {46, 48},
    ('\u265C', 28): set(),
    ('\u265F', 31): {41, 51},
    ('\u265F', 32): {42, 52},
    ('\u265F', 33): {43, 53},
    ('\u265F', 34): {44, 54},
    ('\u265F', 35): {45, 55},
    ('\u265F', 36): {46, 56},
    ('\u265F', 37): {47, 57},
    ('\u265F', 38): {48, 58},
    ('\u2659', 81): {71, 61},
    ('\u2659', 82): {72, 62},
    ('\u2659', 83): {73, 63},
    ('\u2659', 84): {74, 64},
    ('\u2659', 85): {75, 65},
    ('\u2659', 86): {76, 66},
    ('\u2659', 87): {77, 67},
    ('\u2659', 88): {78, 68},
    ('\u2656', 91): set(),
    ('\u2658', 92): {71, 73},
    ('\u2657', 93): set(),
    ('\u2655', 94): set(),
    ('\u2654', 95): set(),
    ('\u2657', 96): set(),
    ('\u2658', 97): {76, 78},
    ('\u2656', 98): set()
}
position2 = {}
position3 = {}
position4 = {}
position5 = {}
position6 = {}

class TestChessBoard(unittest.TestCase):
    """Test cases from: https://www.chessprogramming.org/Perft_Results"""

    def test_move_generation(self):
        positions = [
            (chess.new_game(), initial_position)
        ]
        for chess_board, correct_moves in positions:
            with self.subTest(chess_board=chess_board, correct_moves=correct_moves):
                actual_moves = {}
                for square in range(21, 100):
                    if 0 < chess_board.board[square] < 255:
                        moves = chess.legal_moves(chess_board, square, castle=True)
                        actual_moves[(chess._i2symbol(chess_board.board[square]), square)] = moves
                self.assertEqual(actual_moves, correct_moves)    
