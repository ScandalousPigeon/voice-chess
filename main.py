import io
import customtkinter as ctk
from PIL import Image, ImageTk
import chess, chess.svg
import cairosvg
from vosk import Model, KaldiRecognizer
import pyaudio
import json

# ---------- helpers ----------
def board_svg_to_pil(board: chess.Board, size: int = 480) -> Image.Image:
    """Converts SVG images to a format that tkinter can display.
    
    Args:
        board (chess.Board): the Board object that we want to display.
        size (int): the size in pixels of the display.

    Returns:
        
    
    """
    svg = chess.svg.board(board, size=size)
    png_bytes = cairosvg.svg2png(bytestring=svg)
    return Image.open(io.BytesIO(png_bytes))

class VoiceChessApp(ctk.CTk):
    """GUI for our app.
       Includes a functioning board.
    """
    
    def __init__(self):
        super().__init__()
        self.title("Voice Chess")
        self.geometry("720x560")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # model
        self.board = chess.Board()

        # layout: left = board, right = controls
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # board image
        self.board_label = ctk.CTkLabel(self, text="")
        self.board_label.grid(row=0, column=0, padx=16, pady=16)
        self._tk_img = None  # keep reference to avoid GC
        self.refresh_board()

        # control panel
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        panel.grid_rowconfigure(10, weight=1)

        self.status = ctk.CTkLabel(panel, text="Ready", anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        # move entry
        self.move_entry = ctk.CTkEntry(panel, placeholder_text="Enter move (SAN), e.g. e4, Nf3, Qh5+")
        self.move_entry.grid(row=1, column=0, sticky="ew", padx=12)
        self.move_entry.bind("<Return>", lambda e: self.make_move())

        btn_row = ctk.CTkFrame(panel)
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        btn_row.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btn_row, text="Play Move", command=self.make_move).grid(row=0, column=0, padx=4)
        ctk.CTkButton(btn_row, text="Undo", command=self.undo).grid(row=0, column=1, padx=4)
        ctk.CTkButton(btn_row, text="New Game", command=self.new_game).grid(row=0, column=2, padx=4)

        # mic toggle (replace with speech recognition later)
        self.mic_on = False
        self.mic_btn = ctk.CTkButton(panel, text="Start Listening", command=self.toggle_mic)
        self.mic_btn.grid(row=3, column=0, sticky="ew", padx=12, pady=(8, 4))

        self.hint = ctk.CTkLabel(
            panel,
            text="Tip: moves are Standard Algebraic Notation (e.g. e4, Nf3, O-O).",
            wraplength=280, justify="left")
        self.hint.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 12))

    # methods for the board display
    def refresh_board(self):
        img = board_svg_to_pil(self.board, size=512)
        self._tk_img = ImageTk.PhotoImage(img)
        self.board_label.configure(image=self._tk_img)

    def set_status(self, text: str):
        self.status.configure(text=text)

    def make_move(self):
        san = self.move_entry.get().strip()
        if not san:
            return
        try:
            move = self.board.parse_san(san)
            self.board.push(move)
            self.refresh_board()
            self.set_status(f"Played: {san}   |   Turn: {'White' if self.board.turn else 'Black'}")
            self.move_entry.delete(0, "end")
        except Exception as e:
            self.set_status(f"Invalid move: {san} ({e})")

    def undo(self):
        if self.board.move_stack:
            self.board.pop()
            self.refresh_board()
            self.set_status("Undid last move.")
        else:
            self.set_status("No moves to undo.")

    def new_game(self):
        self.board.reset()
        self.refresh_board()
        self.set_status("New game. White to move.")

    def toggle_mic(self):
        self.mic_on = not self.mic_on
        if self.mic_on:
            self.mic_btn.configure(text="Stop Listening")
            self.set_status("Listening...")
            # add speech recognition here later
        else:
            self.mic_btn.configure(text="Start Listening")
            self.set_status("Mic stopped.")

if __name__ == "__main__":
    app = VoiceChessApp()
    app.mainloop()
