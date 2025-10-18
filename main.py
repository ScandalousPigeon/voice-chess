import io
import customtkinter as ctk
from PIL import Image, ImageTk
import chess, chess.svg
import cairosvg
import voice
import chess_clock
import threading

# helpers
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

def fmt_time(secs: int) -> str:
    secs = max(0, int(secs))
    m, s = divmod(secs, 60)
    return f"{m}:{s:02d}"

class VoiceChessApp(ctk.CTk):
    """GUI for our app.
       Includes a functioning board.
       Note: we strictly use SAN.
    """
    
    def __init__(self):
        super().__init__()
        self.title("Voice Chess")
        self.geometry("720x560")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # model
        self.board = chess.Board()

        # layout: left = board+clocks, right = controls
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)  # board row

        # ---- clocks + board area (column 0) ----
        # top clock (Black)
        self.black_clock_label = ctk.CTkLabel(self, text="Black: 3:00", font=("Default", 18))
        self.black_clock_label.grid(row=0, column=0, padx=16, pady=(16, 0))

        # board image (moved to row=1 to place clocks above/below)
        self.board_label = ctk.CTkLabel(self, text="")
        self.board_label.grid(row=1, column=0, padx=16, pady=8)
        self._tk_img = None  # keep reference to avoid GC
        self.refresh_board()

        # bottom clock (White)
        self.white_clock_label = ctk.CTkLabel(self, text="White: 3:00", font=("Default", 18))
        self.white_clock_label.grid(row=2, column=0, padx=16, pady=(0, 16))

        # control panel (column 1)
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=(0, 16), pady=16)
        panel.grid_rowconfigure(10, weight=1)

        self.status = ctk.CTkLabel(panel, text="Ready", anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        # move entry
        self.move_entry = ctk.CTkEntry(panel, placeholder_text="Enter move (SAN), e.g. e4, Nf3, Qh5+")
        self.move_entry.grid(row=1, column=0, sticky="ew", padx=12)
        self.move_entry.bind("<Return>", lambda e: self.make_move(self.move_entry.get().strip()))

        btn_row = ctk.CTkFrame(panel)
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        btn_row.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btn_row, text="Play Move", command=lambda: self.make_move(self.move_entry.get().strip())).grid(row=0, column=0, padx=4)
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

        # ---- Chess clock wiring ----
        self.clock = chess_clock.ChessClock(
            scheduler_root=self,
            white_time=180,  # 3 minutes
            black_time=180,
            increment=2,
            on_tick=self.on_tick,
            on_switch=self.on_switch,
            on_flag=self.on_flag,
        )
        # Initialize clock labels to starting values
        self.on_tick("white", 180)
        self.on_tick("black", 180)

    # methods for the board display
    def refresh_board(self):
        img = board_svg_to_pil(self.board, size=512)
        self._tk_img = ImageTk.PhotoImage(img)
        self.board_label.configure(image=self._tk_img)

    def set_status(self, text: str):
        self.status.configure(text=text)

    def make_move(self, san):
        # add an argument here, connect from toggle_mic
        # following lines allow manual (typed) input too
        if not san:
            return
        try:
            move = self.board.parse_san(san)
            self.board.push(move)
            self.refresh_board()
            self.set_status(f"Played: {san}   |   Turn: {'White' if self.board.turn else 'Black'}")
            self.move_entry.delete(0, "end")

            # press the clock after a move
            self.clock.press_clock()

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
        # reset and start the clock (White to move)
        self.clock.reset(white_time=180, black_time=180, increment=2)
        self.clock.start_clock()

    def toggle_mic(self):
        self.mic_on = not self.mic_on
        listener = voice.VoiceListener(self.make_move)
        if self.mic_on:
            self.mic_btn.configure(text="Stop Listening")
            listener.start()
            self.set_status("Listening...")
        else:
            self.mic_btn.configure(text="Start Listening")
            listener.stop()
            self.set_status("Mic stopped.")

    # clock callbacks
    def on_tick(self, color, remaining_secs):
        if color == "white":
            self.white_clock_label.configure(text=f"White: {fmt_time(remaining_secs)}")
        else:
            self.black_clock_label.configure(text=f"Black: {fmt_time(remaining_secs)}")

    def on_switch(self, color):
        self.set_status(f"Clock: {color.capitalize()} to move")

    def on_flag(self, color):
        self.set_status(f"{color.capitalize()} flagged on time!")

if __name__ == "__main__":
    app = VoiceChessApp()
    app.mainloop()
