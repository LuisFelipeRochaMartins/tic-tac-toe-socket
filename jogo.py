import pygame
import socket
import argparse
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import time
import sys

WIDTH, HEIGHT = 600, 600
LINE_COLOR = (23, 145, 135)
BG_COLOR = (28, 170, 156)
CROSS_COLOR = (66, 66, 66)
CIRCLE_COLOR = (239, 231, 200)
LINE_WIDTH = 15
CIRCLE_RADIUS = 60
CIRCLE_WIDTH = 15
CROSS_WIDTH = 25
SPACE = 55

PORT = 5555
BUFFER_SIZE = 4096

class Network:
    def __init__(self, host, is_server=False):
        self.is_server = is_server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        
        try:
            if is_server:
                self.sock.bind((host, PORT))
                self.sock.listen(1)
                print(f"Server started. Waiting for connection on {host}:{PORT}...")
                self.conn, addr = self.sock.accept()
                print(f"Connected by {addr}")
            else:
                print(f"Attempting to connect to server at {host}:{PORT}...")
                self.sock.connect((host, PORT))
                self.conn = self.sock
                print(f"Successfully connected to server {host}:{PORT}")
            
            self.queue = Queue()
            self.executor = ThreadPoolExecutor(max_workers=1)
            self.executor.submit(self._receive_loop)
            
        except socket.error as e:
            print(f"Network error: {e}")
            print("Check that:")
            print("1. The server is running if you're trying to connect as a client")
            print("2. The IP address is correct (use the server's actual IP, not 'localhost' for remote connections)")
            print("3. Port 5555 is not blocked by a firewall")
            sys.exit(1)

    def send(self, data):
        try:
            packet = pickle.dumps(data)
            self.conn.sendall(packet)
        except (socket.error, BrokenPipeError) as e:
            print(f"Send error: {e}")
            sys.exit(1)

    def receive(self, timeout=None):
        try:
            return self.queue.get(timeout=timeout)
        except:
            return None

    def _receive_loop(self):
        while True:
            try:
                packet = self.conn.recv(BUFFER_SIZE)
                if not packet:
                    print("Connection closed by peer")
                    break
                data = pickle.loads(packet)
                self.queue.put(data)
            except Exception as e:
                print(f"Receive error: {e}")
                break
        print("Connection lost")
        sys.exit(1)

def draw_lines(screen):
    pygame.draw.line(screen, LINE_COLOR, (0, HEIGHT//3), (WIDTH, HEIGHT//3), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (0, 2*HEIGHT//3), (WIDTH, 2*HEIGHT//3), LINE_WIDTH)

    pygame.draw.line(screen, LINE_COLOR, (WIDTH//3, 0), (WIDTH//3, HEIGHT), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (2*WIDTH//3, 0), (2*WIDTH//3, HEIGHT), LINE_WIDTH)

def draw_marks(screen, board):
    for row in range(3):
        for col in range(3):
            mark = board[row][col]
            if mark == 'O':
                pygame.draw.circle(screen, CIRCLE_COLOR, (col*WIDTH//3 + WIDTH//6, row*HEIGHT//3 + HEIGHT//6), CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif mark == 'X':
                start_desc = (col*WIDTH//3 + SPACE, row*HEIGHT//3 + SPACE)
                end_desc = (col*WIDTH//3 + WIDTH//3 - SPACE, row*HEIGHT//3 + HEIGHT//3 - SPACE)
                pygame.draw.line(screen, CROSS_COLOR, start_desc, end_desc, CROSS_WIDTH)
                start_asc = (col*WIDTH//3 + SPACE, row*HEIGHT//3 + HEIGHT//3 - SPACE)
                end_asc = (col*WIDTH//3 + WIDTH//3 - SPACE, row*HEIGHT//3 + SPACE)
                pygame.draw.line(screen, CROSS_COLOR, start_asc, end_asc, CROSS_WIDTH)

def draw_game_status(screen, is_my_turn, winner, mark):
    font = pygame.font.Font(None, 36)
    
    pygame.draw.rect(screen, BG_COLOR, (0, HEIGHT + 10, WIDTH, 50))
    
    if winner:
        if winner == 'Draw':
            text = font.render("Game ended in a Draw!", True, (255, 255, 255))
        elif winner == mark:
            text = font.render("You Won!", True, (255, 255, 255))
        else:
            text = font.render("You Lost!", True, (255, 255, 255))
    else:
        if is_my_turn:
            text = font.render(f"Your turn (You are {mark})", True, (255, 255, 255))
        else:
            text = font.render("Waiting for opponent...", True, (255, 255, 255))
    
    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT + 25))

def check_winner(board):
    lines = []
    lines.extend(board) 
    cols = [[board[r][c] for r in range(3)] for c in range(3)]
    lines.extend(cols)
    diag1 = [board[i][i] for i in range(3)]
    diag2 = [board[i][2-i] for i in range(3)]
    lines.append(diag1)
    lines.append(diag2)
    for line in lines:
        if line[0] and line.count(line[0]) == 3:
            return line[0]
    if all(all(cell for cell in row) for row in board):
        return 'Draw'
    return None

def main():
    parser = argparse.ArgumentParser(description='Jogo da Velha Muito Maneiro')
    parser.add_argument('--host', default='localhost', help='Server IP address')
    parser.add_argument('--server', action='store_true', help='Run as server')
    args = parser.parse_args()

    board = [[None]*3 for _ in range(3)]
    winner = None

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + 50)) 
    pygame.display.set_caption('Jogo da Velha Muito Maneiro')
    
    try:
        net = Network(args.host, is_server=args.server)
    except Exception as e:
        print(f"Failed to initialize network: {e}")
        pygame.quit()
        return

    is_my_turn = args.server  
    mark = 'X' if args.server else 'O'
    
    screen.fill(BG_COLOR)
    draw_lines(screen)
    draw_game_status(screen, is_my_turn, winner, mark)
    pygame.display.update()
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        clock.tick(30) 
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if is_my_turn and event.type == pygame.MOUSEBUTTONDOWN and winner is None:
                x, y = pygame.mouse.get_pos()
                if y < HEIGHT: 
                    row, col = y // (HEIGHT//3), x // (WIDTH//3)
                    if board[row][col] is None:
                        board[row][col] = mark
                        net.send((row, col))
                        is_my_turn = False
                        winner = check_winner(board)
                        if winner:
                            print(f"Game over: {winner}")

        data = net.receive(timeout=0.01)
        if data and not is_my_turn and winner is None:
            r, c = data
            board[r][c] = 'X' if mark == 'O' else 'O'
            is_my_turn = True
            winner = check_winner(board)
            if winner:
                print(f"Game over: {winner}")

        screen.fill(BG_COLOR)
        draw_lines(screen)
        draw_marks(screen, board)
        draw_game_status(screen, is_my_turn, winner, mark)
        pygame.display.update()

    pygame.quit()

if __name__ == '__main__':
    main()