from typing import NamedTuple
import re

#TODO: finish checkmate condition
#TODO: implement draw: stalemate | insufficient material
#TODO: implement AI opponent

W_PIECES = ('\u2659', '\u2658', '\u2657', '\u2656', '\u2655', '\u2654')
B_PIECES = ('\u265F', '\u265E', '\u265D', '\u265C', '\u265B', '\u265A')

class MoveError(Exception): pass
class SquareError(Exception): pass
class PromotionError(Exception): pass

class ChessBoard(NamedTuple):
    board: bytes
    player: int
    en_passant: int
    promoted: int
    w_king: int
    b_king: int

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
        king = self.w_king if self.player == 1 else self.b_king
        if not is_check(self.board, king):
            return True
        for pos in move_king(self.board, king):
            next_board = bytearray(self.board)
            next_board[pos], next_board[king] = next_board[king], 0
            if not is_check(next_board, pos):
                return True
        return False

def new_game():
    with open('board.bin', mode='rb') as f:
        return ChessBoard(f.read(120), 1, 0, 0, 95, 25)

def promote(chess_board, choice):
    board = bytearray(chess_board.board)
    if choice == 1:
        if chess_board.player == 1:
            board[chess_board.promoted] = 6
        else:
            board[chess_board.promoted] = 38
    elif choice == 2:
        if chess_board.player == 1:
            board[chess_board.promoted] = 5
        else:
            board[chess_board.promoted] = 37
    elif choice == 3:
        if chess_board.player == 1:
            board[chess_board.promoted] = 4
        else:
            board[chess_board.promoted] = 36
    elif choice == 4:
        if chess_board.player == 1:
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

    def invalid_move(p):
        if position in {'0-0', '0-0-0'}:
            raise MoveError(f'{p} {position} invalid move!')
        else:
            raise MoveError(f'{p}{square} {position} invalid move!')

    s = an2i(square)
    if chess_board.board[s] == 0: # square to move from is empty
        raise SquareError(f'{square} is empty!')
    p = i2symbol(chess_board.board[s])
    try: # handle invalid input with exception for castling
        pos = an2i(position)
        castle = False
    except SquareError:
        if chess_board.board[s]&7 == 7:
            if position == '0-0':
                castle, pos = True, s + 2
            elif position == '0-0-0':
                castle, pos = True, s - 2
            else:
                invalid_move(p)
        else:
            invalid_move(p)

    # cannot move opponent's piece or attack own pieces
    if any([chess_board.player == 1 and chess_board.board[s]&32,
            chess_board.player == 2 and not chess_board.board[s]&32,
            chess_board.board[pos] and chess_board.board[s]&32 == chess_board.board[pos]&32]):
        invalid_move(p)

    piece = chess_board.board[s]&7
    if piece == 2:
        moves = move_pawn(chess_board.board, s, en_passant=chess_board.en_passant)
    elif piece == 3:
        moves = move_knight(chess_board.board, s)
    elif piece == 4:
        moves = move_bishop(chess_board.board, s)
    elif piece == 5:
        moves = move_rook(chess_board.board, s)
    elif piece == 6:
        moves = move_queen(chess_board.board, s)
    else:
        moves = move_king(chess_board.board, s, castle=castle)

    if pos not in moves: invalid_move(p)

    # apply move in new board
    next_board = bytearray(chess_board.board)
    if chess_board.player == 1:
        king, next_king = chess_board.w_king, chess_board.b_king
    else:
        king, next_king = chess_board.b_king, chess_board.w_king
    if piece == 7 and castle:
        next_board[pos], next_board[s] = next_board[s], 0
        king = pos # remember king's new position
        if pos == s+2:
            next_board[pos-1], next_board[s+3] = next_board[s+3], 0 # castle king 0-0
            next_board[pos-1] = 5 if chess_board.player == 1 else 37 # remove rook castling flag
        else:
            next_board[pos+1], next_board[s-4] = next_board[s-4], 0 # castle king 0-0-0
            next_board[pos+1] = 5 if chess_board.player == 1 else 37 # remove rook castling flag
    else:
        next_board[pos], next_board[s] = next_board[s], 0
        if piece == 7: king = pos # remember king's new position
        if is_check(next_board, king): # king stays if move results in check
            raise MoveError(f'{p}{square} {position} illegal move: check!')

    en_passant = 0 # reset en passant    
    promoted = pos if piece == 2 and pos // 10 in {2, 9} else 0 # promotion

    if next_board[pos] == 10: ## ♙
        next_board[pos] = 2 # remove double-step flag
        if s - pos == 20:
            en_passant = pos # set en passant flag
    elif next_board[pos] == 42: ## ♟
        next_board[pos] = 34 # remove double-step flag
        if pos - s == 20:
            en_passant = pos # set en passant flag
    elif next_board[pos] == 13: ## ♖
        next_board[pos] = 5 # remove castling flag
    elif next_board[pos] == 45: ## ♜
        next_board[pos] = 37 # remove castling flag
    elif next_board[pos] == 15: ## ♔
        next_board[pos] = 7 # remove castling flag
    elif next_board[pos] == 47: ## ♚
        next_board[pos] = 39 # remove castling flag

    if next_board[king]&16: # remove current player's check flag
        if next_board[king] == 31: ## ♔
            next_board[king] = 15
        if next_board[king] == 23: ## ♔
            next_board[king] = 7
        if next_board[king] == 63: ## ♚
            next_board[king] = 47
        if next_board[king] == 55: ## ♚
            next_board[king] = 39

    if is_check(next_board, next_king): # raise next player's check flag
        if next_board[next_king] == 15: ## ♔
            next_board[next_king] = 31
        if next_board[next_king] == 7:  ## ♔
            next_board[next_king] = 23
        if next_board[next_king] == 47: ## ♚
            next_board[next_king] = 63
        if next_board[next_king] == 39: ## ♚
            next_board[next_king] = 55

    return ChessBoard(
        bytes(next_board),
        2 if chess_board.player == 1 else 1,
        en_passant,
        promoted,
        king if chess_board.player == 1 else next_king,
        next_king if chess_board.player == 1 else king
    )

def move_pawn(board, square, en_passant=0):
    moves = []
    if board[square]&32:
        if board[square+10] == 0:
            moves.append(square+10)
        if board[square+9] > 0 and board[square]&32 != board[square+9]&32:
            moves.append(square+9)
        if board[square+11] > 0 and board[square]&32 != board[square+11]&32:
            moves.append(square+11)
        if board[square+20] == 0 and board[square]&8:
            moves.append(square+20)
        if en_passant and square // 10 == 6 and abs(en_passant - square) == 1:
            moves.append(en_passant+10)
    else:
        if board[square-10] == 0:
            moves.append(square-10)
        if board[square-9] > 0 and board[square]&32 != board[square-9]&32:
            moves.append(square-9)
        if board[square-11] > 0 and board[square]&32 != board[square-11]&32:
            moves.append(square-11)
        if board[square-20] == 0 and board[square]&8:
            moves.append(square-20)
        if en_passant and square // 10 == 5 and abs(en_passant - square) == 1:
            moves.append(en_passant-10)
    return frozenset(moves)

def move_knight(board, square):
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

def move_bishop(board, square):
    return frozenset().union(*map(slide, [board]*4, [square]*4, [11, -11, 9, -9]))

def move_rook(board, square):
    return frozenset().union(*map(slide, [board]*4, [square]*4, [10, -10, 1, -1]))

def move_queen(board, square):
    return move_bishop(board, square) | move_rook(board, square)

def move_king(board, square, castle=False):

    def quick_check(board, king, pos):
        next_board = bytearray(board)
        next_board[pos], next_board[square] = next_board[square], 0
        return is_check(bytes(next_board), pos)

    moves = []
    for i in [1, 9, 10, 11]:
        if (board[square+i] == 0 or board[square+i] != 255 and
                board[square]&32 != board[square+i]&32):
            moves.append(square+i)
        if (board[square-i] == 0 or board[square-i] != 255 and
                board[square]&32 != board[square-i]&32):
            moves.append(square-i)
    if castle and board[square]&8 and not board[square]&16:
        if (board[square+3]&7 == 5 and board[square+3]&8 and 0 == board[square+1] == board[square+2] and not
                any(quick_check(board, square, pos) for pos in [square+1, square+2])):
            moves.append(square+2)
        if (board[square-4]&7 == 5 and board[square-4]&8 and 0 == board[square-1] == board[square-2] == board[square-3] and not
                any(quick_check(board, square, pos) for pos in [square-1, square-2])):
            moves.append(square-2)
    return frozenset(moves)

def slide(board, square, direction):
    moves = []
    position = square + direction
    while board[position] != 255:
        if board[position] == 0:
            moves.append(position)
        elif board[square]&32 != board[position]&32:
            moves.append(position)
        else:
            break
        position += direction
    return frozenset(moves)

def is_check(board, king):
    if board[king]&32:
        attacks = (i for i in range(100) if not board[i]&32 and 0 < board[i] < 255)
    else:
        attacks = (i for i in range(100) if board[i]&32 and 0 < board[i] < 255)
    for square in attacks:
        piece = board[square]&7
        if piece == 2:
            moves = move_pawn(board, square)
        elif piece == 3:
            moves = move_knight(board, square)
        elif piece == 4:
            moves = move_bishop(board, square)
        elif piece == 5:
            moves = move_rook(board, square)
        elif piece == 6:
            moves = move_queen(board, square)
        else:
            moves = move_king(board, square)
    return True if king in moves else False  

def i2symbol(i):
    return B_PIECES[(i&7) - 2] if i&32 else W_PIECES[(i&7) -2]

def an2i(an):
    p = re.compile('^[a-h][1-8]$')
    if re.match(p, an):
        return 'abcdefgh'.index(an[0]) + 1 + (10 - int(an[1])) * 10
    raise SquareError(f'{an} is not a valid square!')

def i2an(i):
    return '%s%d' % ('abcdefgh'[i%10 - 1], 10 - i//10)

if __name__ == '__main__':
    print('Valid moves:')
    print('xx yy    ==> xx: position of piece | yy: postion to move to')
    print('xx 0-0   ==> king side castle')
    print('xx 0-0-0 ==> queen side castle\n')
    chess_board = new_game()
    print(chess_board)
    while True:
        try:
            square, position, *_ = input(f"player {chess_board.player}'s turn ==> ").split()
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
        if not chess_board:
            break
        if is_check(chess_board.board, chess_board.w_king if chess_board.player == 1 else chess_board.b_king):
            print('check!') 
    print(f'checkmate: player {chess_board.player} won!')
