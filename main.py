import io
import customtkinter as ctk
from PIL import Image, ImageTk
import chess, chess.svg
import cairosvg
import voice
import chess_clock

# helpers
def board_svg_to_pil(board: chess.Board, size: int = 480) -> Image.Image:
    svg = chess.svg.board(board, size=size)
    png_bytes = cairosvg.svg2png(bytestring=svg)
    return Image.open(io.BytesIO(png_bytes))

def fmt_time(secs: int) -> str:
    secs = max(0, int(secs))
    m, s = divmod(secs, 60)
    return f"{m}:{s:02d}"

TARGET_W, TARGET_H = 480, 320  # to fit the 3.5 inch screen
SIDEBAR_W   = 112     # wider, comfy bar
INNER_PAD   = 6       # the padx you use in grid()
BTN_W       = SIDEBAR_W - 2*INNER_PAD   # fits inside bar
BTN_H       = 34


class VoiceChessApp(ctk.CTk):
    """Board centered, clocks top & bottom, buttons on left/right sidebars."""
    def __init__(self):
        super().__init__()
        self.title("Voice Chess")
        self.attributes("-fullscreen", True)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # model
        self.board = chess.Board()
        self.listener = voice.VoiceListener(self.make_move)

        # Grid: 3 cols (L sidebar | board, clock | R sidebar)
        self.pad = 6
        self.grid_columnconfigure(0, weight=0)   # left sidebar
        self.grid_columnconfigure(1, weight=1)   # center board
        self.grid_columnconfigure(2, weight=0)   # right sidebar
        self.grid_rowconfigure(1, weight=1)      # middle grows

        # Top clock (full width)
        self.black_clock_label = ctk.CTkLabel(self, text="Black: 3:00", font=("Default", 16))
        self.black_clock_label.grid(row=0, column=0, columnspan=3,
                                    padx=self.pad, pady=(self.pad, 2), sticky="ew")

        # Left sidebar
        self.left_bar = ctk.CTkFrame(self, width=SIDEBAR_W)
        self.left_bar.grid(row=1, column=0, sticky="nsw", padx=(self.pad, 2), pady=2)
        self.left_bar.grid_propagate(False)

        self.status = ctk.CTkLabel(self.left_bar, text="Ready", anchor="w",
                                wraplength=SIDEBAR_W - 2*INNER_PAD, justify="left")
        self.status.grid(row=0, column=0, sticky="ew", padx=INNER_PAD, pady=(INNER_PAD, 4))

        self.move_entry = ctk.CTkEntry(self.left_bar, placeholder_text="e.g. e4",
                                    width=BTN_W)  # keep it inside the bar
        self.move_entry.grid(row=1, column=0, sticky="w", padx=INNER_PAD, pady=(0, 6))
        self.move_entry.bind("<Return>", lambda e: self.make_move(self.move_entry.get().strip()))

        self.btn_play = ctk.CTkButton(self.left_bar, text="Play", width=BTN_W, height=BTN_H,
                                    command=lambda: self.make_move(self.move_entry.get().strip()))
        self.btn_undo = ctk.CTkButton(self.left_bar, text="Undo", width=BTN_W, height=BTN_H,
                                    command=self.undo)
        self.btn_new  = ctk.CTkButton(self.left_bar, text="New",  width=BTN_W, height=BTN_H,
                                    command=self.new_game)

        # NOTE: do NOT use sticky="ew" on the buttons
        self.btn_play.grid(row=2, column=0, padx=INNER_PAD, pady=(0, 4), sticky="w")
        self.btn_undo.grid(row=3, column=0, padx=INNER_PAD, pady=(0, 4), sticky="w")
        self.btn_new.grid (row=4, column=0, padx=INNER_PAD, pady=(0, 4), sticky="w")

        # Center board
        self.board_label = ctk.CTkLabel(self, text="")
        self.board_label.grid(row=1, column=1, padx=2, pady=2, sticky="n")
        self._tk_img = None  # keep reference

        # Right sidebar
        self.right_bar = ctk.CTkFrame(self, width=SIDEBAR_W)
        self.right_bar.grid(row=1, column=2, sticky="nse", padx=(2, self.pad), pady=2)
        self.right_bar.grid_propagate(False)  # keep exact width

        self.mic_on = False
        self.mic_btn = ctk.CTkButton(
            self.right_bar,
            text="Start\nListening",
            width=BTN_W,         # <-- explicitly size the button
            height=60,
            command=self.toggle_mic
        )
        # don't use sticky="ew", keep it centered or aligned left
        self.mic_btn.grid(row=0, column=0, padx=INNER_PAD, pady=(INNER_PAD, 4), sticky="w")

        self.hint = ctk.CTkLabel(
            self.right_bar,
            text="Tip:\nSAN like e4,\nNf3, O-O",
            justify="left",
            wraplength=SIDEBAR_W - 2*INNER_PAD
        )
        self.hint.grid(row=1, column=0, padx=INNER_PAD, pady=(0, INNER_PAD), sticky="w")

        # Bottom clock (full width)
        self.white_clock_label = ctk.CTkLabel(self, text="White: 3:00", font=("Default", 16))
        self.white_clock_label.grid(row=2, column=0, columnspan=3,
                                    padx=self.pad, pady=(2, self.pad), sticky="ew")

        # Chess clock wiring
        self.clock = chess_clock.ChessClock(
            scheduler_root=self,
            white_time=180, black_time=180, increment=2,
            on_tick=self.on_tick, on_switch=self.on_switch, on_flag=self.on_flag,
        )
        self.on_tick("white", 180)
        self.on_tick("black", 180)

        # Draw initial board and keep it sized correctly
        self.after(0, self.refresh_board)   # after layout -> real sizes
        self.bind("<Configure>", self._on_resize)

    # sizing
    def _measure(self, w):
        h = w.winfo_height()
        return h if h > 1 else w.winfo_reqheight()
    def _measure_w(self, w):
        ww = w.winfo_width()
        return ww if ww > 1 else w.winfo_reqwidth()

    def _compute_board_size(self) -> int:
        self.update_idletasks()

        total_w = max(1, self.winfo_width())
        total_h = max(1, self.winfo_height())

        # take actual occupied widths/heights
        left_w  = self._measure_w(self.left_bar)
        right_w = self._measure_w(self.right_bar)
        top_h   = self._measure(self.black_clock_label)
        bot_h   = self._measure(self.white_clock_label)

        # paddings that flank board area
        vertical_margins = self.pad + 2 + 2 + self.pad
        horizontal_margins = 2 + 2  # around the board label within col 1

        avail_w = total_w - (left_w + right_w + horizontal_margins)
        avail_h = total_h - (top_h + bot_h + vertical_margins)

        size = max(140, min(avail_w, avail_h))  # keep usable minimum
        return int(size)

    # board render
    def refresh_board(self, forced_size: int | None = None):
        board_size = forced_size if forced_size else self._compute_board_size()
        img = board_svg_to_pil(self.board, size=board_size)
        self._tk_img = ImageTk.PhotoImage(img)
        self.board_label.configure(image=self._tk_img, width=board_size, height=board_size)

    def _on_resize(self, _e):
        self.after_idle(self.refresh_board)

    # status + actions
    def set_status(self, text: str):
        self.status.configure(text=text)

    def make_move(self, san):
        if not san:
            return
        try:
            move = self.board.parse_san(san)
            self.board.push(move)
            self.refresh_board()
            self.set_status(f"Played: {san} | Turn: {'White' if self.board.turn else 'Black'}")
            self.move_entry.delete(0, "end")
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
        self.clock.reset(white_time=180, black_time=180, increment=2)
        self.clock.start_clock()

    def toggle_mic(self):
        self.mic_on = not self.mic_on
        if self.mic_on:
            self.mic_btn.configure(text="Stop\nListening")
            self.listener.start()
            self.set_status("Listening...")
        else:
            self.mic_btn.configure(text="Start\nListening")
            self.listener.stop()
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
        self.set_status(f"{color.capitalize()} flagged!")

if __name__ == "__main__":
    app = VoiceChessApp()
    app.mainloop()