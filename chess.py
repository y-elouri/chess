from typing import NamedTuple
from functools import partial
import re

#TODO: implement AI opponent

W_PIECES = ('\u2659', '\u2658', '\u2657', '\u2656', '\u2655', '\u2654')
B_PIECES = ('\u265F', '\u265E', '\u265D', '\u265C', '\u265B', '\u265A')

class MoveError(Exception): pass
class SquareError(Exception): pass
class PromotionError(Exception): pass

class ChessBoard(NamedTuple):
    board: bytes
    player: bool
    en_passant: int
    promoted: int
    w_king: int
    b_king: int
    check: bool = False

    def __repr__(self) -> str:
        r = f"  {''.join('%2s' % c for c in 'abcdefgh')}\n"
        for i, square in enumerate(self.board):
            if square == 255:
                if i % 10 == 0 and i >= 20 and i <= 90:
                    r += '%2d' % (10 - i//10)
                continue
            elif square == 0:
                piece = '_'
            else:
                if square&32:
                    piece = B_PIECES[(square&7) - 2]
                else:
                    piece = W_PIECES[(square&7) - 2]
            r += '%2s' % piece
            if i % 10 == 8:
                r += '\n'
        return r

    def __bool__(self) -> bool:
        if self.player:
            pieces = [i for i, _ in enumerate(self.board) if 0 < self.board[i] < 32]
        else:
            pieces = [i for i, _ in enumerate(self.board) if 32 <= self.board[i] < 64]
        return any(map(partial(legal_moves, self, castle=False), pieces))

    @property
    def material(self):
        wp = sorted(i&7 for i in self.board if 0 < i < 32)
        bp = sorted(i&7 for i in self.board if 32 <= i < 64)
        ## obvious draws
        # K vs K
        if [7] == wp == bp:
            return False
        # K vs KN
        elif (wp == [7] and bp == [3, 7]) or (bp == [7] and wp == [3, 7]):
            return False 
        # K vs KB
        elif (wp == [7] and bp == [4, 7]) or (bp == [7] and wp == [4, 7]):
            return False
        # KB vs KB if bishops on same color
        elif [4, 7] == wp == bp:
            bishops = [i&7 for i in self.board if i == 4]
            if all(map(lambda x: sum([10 - x//10, x % 10]) % 2 == 0, bishops)):
                return False
        ## simple heuristics
        # K  vs KNN
        elif (wp == [7] and bp == [3, 3, 7]) or (bp == [7] and wp == [3, 3, 7]):
            return False
        # KB vs KNN
        elif (wp == [2, 7] and bp == [3, 3, 7]) or (wp == [2, 7] and bp == [3, 3, 7]):
            return False
        # KN vs KNN
        elif (wp == [3, 7] and bp == [3, 3, 7]) or (bp == [3, 7] and wp == [3, 3, 7]):
            return False
        # KB vs KN
        elif (wp == [2, 7] and bp == [3, 7]) or (bp == [2, 7] and wp == [3, 7]):
            return False
        # KN vs KN
        elif [3, 7] == wp == bp:
            return False
        # KN vs KBN
        elif (wp == [3, 7] and bp == [3, 4, 7]) or (bp == [3, 7] and wp == [3, 4, 7]):
            return False
        # KB vs KBN
        elif (wp == [4, 7] and bp == [3, 4, 7]) or (bp == [4, 7] and wp == [3, 4, 7]):
            return False
        return True

def new_game():
    with open('board.bin', mode='rb') as f:
        return ChessBoard(f.read(120), True, 0, 0, 95, 25)

def promote(chess_board, choice):
    board = bytearray(chess_board.board)
    if choice == 1:
        if chess_board.player:
            board[chess_board.promoted] = 6
        else:
            board[chess_board.promoted] = 38
    elif choice == 2:
        if chess_board.player:
            board[chess_board.promoted] = 5
        else:
            board[chess_board.promoted] = 37
    elif choice == 3:
        if chess_board.player:
            board[chess_board.promoted] = 4
        else:
            board[chess_board.promoted] = 36
    elif choice == 4:
        if chess_board.player:
            board[chess_board.promoted] = 3
        else:
            board[chess_board.promoted] = 35
    else:
        raise PromotionError('invalid promotion!')
    return ChessBoard(
        bytes(board),
        chess_board.player,
        chess_board.en_passant,
        0,
        chess_board.w_king,
        chess_board.b_king
    )

def move(chess_board, square, position):

    def invalid_move(symbol):
        if position in {'0-0', '0-0-0'}:
            raise MoveError(f'{symbol} {position} invalid move!')
        else:
            raise MoveError(f'{symbol}{square} {position} invalid move!')

    s = _an2i(square)
    if chess_board.board[s] == 0: # square to move from is empty
        raise SquareError(f'{square} is empty!')
    symbol = _i2symbol(chess_board.board[s])
    try: # handle invalid input with exception for castling
        target = _an2i(position)
        castle = False
    except SquareError:
        if chess_board.board[s]&7 == 7:
            if position == '0-0':
                castle, target = True, s + 2
            elif position == '0-0-0':
                castle, target = True, s - 2
            else:
                invalid_move(symbol)
        else:
            invalid_move(symbol)

    # cannot move opponent's piece or attack own pieces
    if any([chess_board.player == chess_board.board[s]&32,
            chess_board.board[target] and chess_board.board[s]&32 == chess_board.board[target]&32]):
        invalid_move(symbol)

    if target not in legal_moves(chess_board, s, castle=castle):
        invalid_move(symbol)

    # apply move in new board
    next_board = _apply_move(chess_board.board, s, target, castle)
    if next_board[target]&7 == 7:
        king = target
    else:
        king = chess_board.w_king if chess_board.player else chess_board.b_king
    next_king = chess_board.b_king if chess_board.player else chess_board.w_king

    # reset en passant
    en_passant = 0

    # promote pawn
    promoted = target if next_board[target]&7 == 2 and target // 10 in {2, 9} else 0

    # set en passant flag
    if next_board[target]&7 == 2 and abs(s - target) == 20:
        en_passant = target 
    # update king's castling rights
    elif next_board[target] == 5: ## ♖
        if next_board[king] == 15:
            next_board[king] = 7 # remove castling flag
    elif next_board[target] == 37: ## ♜
        if next_board[king] == 47:
            next_board[king] = 39 # remove castling flag
    elif next_board[target] == 15: ## ♔
        next_board[target] = 7 # remove castling flag
    elif next_board[target] == 47: ## ♚
        next_board[target] = 39 # remove castling flag

    # set the check flag
    if _under_attack(next_board, next_king, chess_board.player, en_passant=en_passant):
        check = True
    else:
        check = False

    return ChessBoard(
        bytes(next_board),
        not chess_board.player,
        en_passant,
        promoted,
        *((king, next_king) if chess_board.player else (next_king, king)),
        check
    )

def legal_moves(chess_board, square, castle=False):
    moves = _move_piece(
        chess_board.board,
        square,
        en_passant=chess_board.en_passant,
        castle=castle and not chess_board.check
    )
    legal_moves = []
    for move in moves:
        next_board = _apply_move(chess_board.board, square, move, castle)
        if chess_board.board[square]&7 == 7:
            king = move
        else:
            king = chess_board.w_king if chess_board.player else chess_board.b_king
        if not _under_attack(next_board, king, not chess_board.player, en_passant=chess_board.en_passant):
            legal_moves.append(move)
    return frozenset(legal_moves)

def _apply_move(board, square, target, castle):
    next_board = bytearray(board)

    # put piece on target square
    next_board[target], next_board[square] = next_board[square], 0

    # handle castling
    if castle:
        if target == square+2: # 0-0
            next_board[target-1], next_board[square+3] = next_board[square+3], 0
        else: # 0-0-0
            next_board[target+1], next_board[square-4] = next_board[square-4], 0
    
    return next_board

def _under_attack(board, target, player, en_passant=0):
    if player:
        attacks = (i for i in range(21, 100) if not board[i]&32 and 0 < board[i] < 255)
    else:
        attacks = (i for i in range(21, 100) if board[i]&32 and 0 < board[i] < 255)
    for square in attacks:
        moves = _move_piece(board, square, en_passant=en_passant)
        if target in moves:
            return True
    return False  

def _move_piece(board, square, en_passant=0, castle=False):
    piece = board[square]&7
    if piece == 2:
        moves = _move_pawn(board, square, en_passant=en_passant)
    elif piece == 3:
        moves = _move_knight(board, square)
    elif piece == 4:
        moves = _move_bishop(board, square)
    elif piece == 5:
        moves = _move_rook(board, square)
    elif piece == 6:
        moves = _move_queen(board, square)
    elif piece == 7:
        moves = _move_king(board, square, en_passant=en_passant, castle=castle)
    else:
        raise SquareError(f'{square} is not a valid square!')
    return moves

def _move_pawn(board, square, en_passant=0):
    moves = []
    if board[square]&32:
        if board[square+10] == 0:
            moves.append(square+10)
        if board[square+9] not in {0, 255} and board[square]&32 != board[square+9]&32:
            moves.append(square+9)
        if board[square+11] not in {0, 255} and board[square]&32 != board[square+11]&32:
            moves.append(square+11)
        if board[square+20] == 0 and square // 10 == 3:
            moves.append(square+20)
        if en_passant and square // 10 == 6 and abs(en_passant - square) == 1:
            moves.append(en_passant+10)
    else:
        if board[square-10] == 0:
            moves.append(square-10)
        if board[square-9] not in {0, 255} and board[square]&32 != board[square-9]&32:
            moves.append(square-9)
        if board[square-11] not in {0, 255} and board[square]&32 != board[square-11]&32:
            moves.append(square-11)
        if board[square-20] == 0 and square // 10 == 8:
            moves.append(square-20)
        if en_passant and square // 10 == 5 and abs(en_passant - square) == 1:
            moves.append(en_passant-10)
    return frozenset(moves)

def _move_knight(board, square):
    moves = []
    for i in [8, 12, 19, 21]:
        if board[square+i] == 0:
            moves.append(square+i)
        elif board[square+i] != 255 and board[square]&32 != board[square+i]&32:
            moves.append(square+i)
        if board[square-i] == 0:
            moves.append(square-i)
        elif board[square-i] != 255 and board[square]&32 != board[square-i]&32:
            moves.append(square-i)
    return frozenset(moves)

def _move_bishop(board, square):
    return frozenset().union(*map(_slide, [board]*4, [square]*4, [11, -11, 9, -9]))

def _move_rook(board, square):
    return frozenset().union(*map(_slide, [board]*4, [square]*4, [10, -10, 1, -1]))

def _move_queen(board, square):
    return _move_bishop(board, square) | _move_rook(board, square)

def _move_king(board, square, en_passant=0, castle=False):
    moves = []
    for i in [1, 9, 10, 11]:
        if (board[square+i] == 0 or board[square+i] != 255 and
                board[square]&32 != board[square+i]&32):
            moves.append(square+i)
        if (board[square-i] == 0 or board[square-i] != 255 and
                board[square]&32 != board[square-i]&32):
            moves.append(square-i)
    if castle and board[square]&8:
        if (board[square+3]&7 == 5 and
            0 == board[square+1] == board[square+2] and
            not _under_attack(board, square+1, board[square]&32, en_passant=en_passant) and
            not _under_attack(board, square+2, board[square]&32, en_passant=en_passant)):
                moves.append(square+2)
        if (board[square-4]&7 == 5 and
            0 == board[square-1] == board[square-2] == board[square-3] and
            not _under_attack(board, square-1, board[square]&32, en_passant=en_passant) and
            not _under_attack(board, square-2, board[square]&32, en_passant=en_passant)):
                moves.append(square-2)
    return frozenset(moves)

def _slide(board, square, direction):
    moves = []
    position = square + direction
    while board[position] != 255:
        if board[position] == 0:
            moves.append(position)
        elif board[square]&32 != board[position]&32:
            moves.append(position)
            break
        else:
            break
        position += direction
    return frozenset(moves)

def _i2symbol(i):
    return B_PIECES[(i&7) - 2] if i&32 else W_PIECES[(i&7) -2]

def _an2i(an):
    p = re.compile('^[a-h][1-8]$')
    if re.match(p, an):
        return 'abcdefgh'.index(an[0]) + 1 + (10 - int(an[1])) * 10
    raise SquareError(f'{an} is not a valid square!')

def _i2an(i):
    return '%s%d' % ('abcdefgh'[i%10 - 1], 10 - i//10)

if __name__ == '__main__':
    print('Valid moves:')
    print('xx yy    ==> xx: position of piece | yy: postion to move to')
    print('xx 0-0   ==> king side castle')
    print('xx 0-0-0 ==> queen side castle\n')
    chess_board = new_game()
    print(chess_board)
    while True:
        if chess_board.check:
            print('check!')
        try:
            square, position, *_ = input(f"player {1 if chess_board.player else 2}'s turn ==> ").split()
        except ValueError:
            print('missing input!')
            continue
        try:
            chess_board = move(chess_board, square, position)
        except (SquareError, MoveError) as err:
            print(err)
            continue
        while chess_board.promoted:
            print(f'promote {position} to:')
            if position[1] == '1':
                print('1. \u265B', '2. \u265C', '3. \u265D', '4. \u265E', sep='\n')
            else:
                print('1. \u2655', '2. \u2656', '3. \u2657', '4. \u2658', sep='\n')
            choice, *_ = input()
            try:
                chess_board = promote(chess_board, choice)
            except PromotionError as err:
                print(err)
        print(chess_board)
        if not chess_board.material:
            print('draw: insufficient material!')
        if not chess_board:
            if chess_board.check:
                print(f'checkmate: player {chess_board.player} won!')
            else:
                print('draw: stalemate!')
            break
