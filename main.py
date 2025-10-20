import io
import customtkinter as ctk
from PIL import Image, ImageTk
import chess, chess.svg
import cairosvg
import voice
import chess_clock
import threading

# ---------- helpers ----------
def board_svg_to_pil(board: chess.Board, size: int = 480) -> Image.Image:
    """Converts SVG images to a format that tkinter can display."""
    svg = chess.svg.board(board, size=size)
    png_bytes = cairosvg.svg2png(bytestring=svg)
    return Image.open(io.BytesIO(png_bytes))

def fmt_time(secs: int) -> str:
    secs = max(0, int(secs))
    m, s = divmod(secs, 60)
    return f"{m}:{s:02d}"

TARGET_W, TARGET_H = 480, 320  # 3.5" landscape

class VoiceChessApp(ctk.CTk):
    """GUI for our app. Includes a functioning board. We use SAN."""
    
    def __init__(self):
        super().__init__()
        self.title("Voice Chess")
        self.geometry(f"{TARGET_W}x{TARGET_H}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # model
        self.board = chess.Board()
        self.listener = voice.VoiceListener(self.make_move)

        # ---------- layout: single column ----------
        # [0] Black clock (top bar)
        # [1] Board (square, auto-resizes)
        # [2] White clock (bottom bar)
        # [3] Controls (buttons + entry)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # board expands

        pad = 8

        # ---- clocks + board area ----
        self.black_clock_label = ctk.CTkLabel(self, text="Black: 3:00", font=("Default", 16))
        self.black_clock_label.grid(row=0, column=0, padx=pad, pady=(pad, 0), sticky="ew")

        # Board container: keep a label that we redraw with a scaled image
        self.board_label = ctk.CTkLabel(self, text="")
        self.board_label.grid(row=1, column=0, padx=pad, pady=4, sticky="n")
        self._tk_img = None  # keep reference to avoid GC

        self.white_clock_label = ctk.CTkLabel(self, text="White: 3:00", font=("Default", 16))
        self.white_clock_label.grid(row=2, column=0, padx=pad, pady=(0, 4), sticky="ew")

        # ---- control panel (now below the board) ----
        panel = ctk.CTkFrame(self)
        panel.grid(row=3, column=0, sticky="ew", padx=pad, pady=(0, pad))
        panel.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(panel, text="Ready", anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        # move entry
        self.move_entry = ctk.CTkEntry(panel, placeholder_text="Enter move (SAN), e.g. e4, Nf3, O-O")
        self.move_entry.grid(row=1, column=0, sticky="ew", padx=12)
        self.move_entry.bind("<Return>", lambda e: self.make_move(self.move_entry.get().strip()))

        # buttons row
        btn_row = ctk.CTkFrame(panel)
        btn_row.grid(row=2, column=0, sticky="ew", padx=12, pady=8)
        btn_row.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btn_row, text="Play",  height=40,
                      command=lambda: self.make_move(self.move_entry.get().strip())).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btn_row, text="Undo",  height=40,
                      command=self.undo).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(btn_row, text="New",   height=40,
                      command=self.new_game).grid(row=0, column=2, padx=4, sticky="ew")

        # mic toggle
        self.mic_on = False
        self.mic_btn = ctk.CTkButton(panel, text="Start Listening", height=40, command=self.toggle_mic)
        self.mic_btn.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

        self.hint = ctk.CTkLabel(
            panel,
            text="Tip: SAN moves like e4, Nf3, O-O. Use the button or press Enter.",
            wraplength=TARGET_W - 2*pad, justify="left")
        self.hint.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))

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
        self.on_tick("white", 180)
        self.on_tick("black", 180)

        # Draw the initial board at a size that fits the current window
        self.refresh_board()  # will compute a fitting board size

        # Recompute board size whenever the window changes (rotation/resize)
        self.bind("<Configure>", self._on_resize)

    # ---------- sizing logic ----------
    def _compute_board_size(self) -> int:
        """Compute the largest square that fits between clocks and above controls."""
        # Current inner size
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())

        # Reserve vertical space for: top clock (~36), bottom clock (~36), controls (~120), plus paddings
        top_clock_h    = 36
        bottom_clock_h = 36
        controls_h     = 120  # entry + buttons + mic + hint
        vertical_margins = 8 + 4 + 4 + 8  # padding around elements

        available_h = h - (top_clock_h + bottom_clock_h + controls_h + vertical_margins)
        available_w = w - 2*8  # side padding

        size = max(160, min(available_w, available_h))
        return int(size)

    # ---------- board display ----------
    def refresh_board(self, forced_size: int | None = None):
        board_size = forced_size if forced_size else self._compute_board_size()
        img = board_svg_to_pil(self.board, size=board_size)
        self._tk_img = ImageTk.PhotoImage(img)
        self.board_label.configure(image=self._tk_img)
        # prevent the label from growing past the image
        self.board_label.configure(width=board_size, height=board_size)

    def _on_resize(self, _event):
        # Debounce fast resizes by scheduling once; .after_idle is enough here
        self.after_idle(self.refresh_board)

    def set_status(self, text: str):
        self.status.configure(text=text)

    # ---------- game actions ----------
    def make_move(self, san):
        if not san:
            return
        try:
            move = self.board.parse_san(san)
            self.board.push(move)
            self.refresh_board()
            self.set_status(f"Played: {san}   |   Turn: {'White' if self.board.turn else 'Black'}")
            self.move_entry.delete(0, "end")
            self.clock.press_clock()  # switch + increment
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
        self.clock.reset(white_time=180, black_time=180, increment=2)
        self.clock.start_clock()

    def toggle_mic(self):
        self.mic_on = not self.mic_on
        if self.mic_on:
            self.mic_btn.configure(text="Stop Listening")
            self.listener.start()
            self.set_status("Listening...")
        else:
            self.mic_btn.configure(text="Start Listening")
            self.listener.stop()
            self.set_status("Mic stopped.")

    # ---------- clock callbacks ----------
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
