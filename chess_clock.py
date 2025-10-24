import time

class ChessClock:
    """
    Chess clock driven by a tkinter's .after(), to avoid having to use threading.
    """

    def __init__(self, scheduler_root, white_time=180, black_time=180, increment=2,
                 on_tick=None, on_switch=None, on_flag=None):
        self.root = scheduler_root
        self.white_time = white_time
        self.black_time = black_time
        self.increment = increment

        self.ticking = None  # "white", "black" or None
        self.to_move = "white" # store side to move (otherwise we lose this information when self.ticking = None)

        self._after_id = None
        self._last_tick_monotonic = None

        self.on_tick = on_tick or (lambda colour, secs: None)
        self.on_switch = on_switch or (lambda colour: None)
        self.on_flag = on_flag or (lambda colour: None)

    # public API
    def reset(self, white_time=180, black_time=180, increment=2):
        self.cancel()
        self.white_time = white_time
        self.black_time = black_time
        self.increment = increment
        self.ticking = None
        self.to_move = "white"
        self.on_tick("white", self.white_time)
        self.on_tick("black", self.black_time)

    def start_clock(self):
        """Start from self.to_move without blocking."""
        self.ticking = self.to_move
        self._last_tick_monotonic = time.perf_counter()
        self._schedule_next_tick(1000)

    def pause(self):
        """Pause whichever side is ticking and remembers whose move it is."""
        self.to_move = self.ticking or self.to_move
        self.ticking = None
        self.cancel()

    def press_clock(self):
        """
        Press the clock: add increment to the side that just moved and switch sides.
        Works whether the clock is running or paused / not started.
        """
        if self.ticking is None:
            mover = self.to_move
            if mover == "white":
                self.white_time += self.increment
                self.ticking = "black"
            else:
                self.black_time += self.increment
                self.ticking = "white"

            self.on_switch(self.ticking)
            self._restart_ticks()
            return

        if self.ticking == "white":
            self.white_time += self.increment
            self.ticking = "black"
        else:
            self.black_time += self.increment
            self.ticking = "white"

        self.on_switch(self.ticking)
        self._restart_ticks()


    def set_clock(self, new_white_time, new_black_time, new_increment):
        """Update the control values and refresh UI."""
        self.white_time = new_white_time
        self.black_time = new_black_time
        self.increment = new_increment
        self.on_tick("white", self.white_time)
        self.on_tick("black", self.black_time)

    def cancel(self):
        """Cancel any scheduled tick."""
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None

    # internals
    def _restart_ticks(self):
        self.cancel()
        self._last_tick_monotonic = time.perf_counter()
        self._schedule_next_tick(1000)

    def _schedule_next_tick(self, delay_ms):
        self._after_id = self.root.after(delay_ms, self._tick_once)

    def _tick_once(self):
        """Called by Tk every second."""
        if self.ticking is None:
            self._after_id = None
            return

        now = time.perf_counter()
        elapsed = now - (self._last_tick_monotonic or now)
        self._last_tick_monotonic = now

        if self.ticking == "white":
            self.white_time = max(0, self.white_time - int(round(elapsed)))
            remaining = self.white_time
        else:
            self.black_time = max(0, self.black_time - int(round(elapsed)))
            remaining = self.black_time

        self.on_tick(self.ticking, remaining)

        if remaining <= 0:
            flagged = self.ticking
            self.ticking = None
            self.cancel()
            self.on_flag(flagged)
            return

        self._schedule_next_tick(1000)
