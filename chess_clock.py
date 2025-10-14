import time

class ChessClock:
    """ChessClock object that represents one side; white or black."""
    def __init__(self, white_time=180, black_time=180, increment=2):
        """
        Parameters:
            white_time (int): how many seconds white has remaining.
            black_time (int): how many seconds black has remaining.
            increment (int): how many seconds should be added on each move.
            ticking (string): which side's timer is running.
            to_move (string): stores which side's move it should be, on the event of self.pause().
        """
        self.white_time = white_time
        self.black_time = black_time
        self.increment = increment
        self.ticking = None
        self.to_move = "white"

    def reset(self):
        """Resets the clock back to its default 3|2 time control."""
        self.white_time = 180
        self.black_time = 180
        self.increment = 2
        self.ticking = None
        self.to_move = "white"
    
    def start_clock(self):
        """Initial start clock action."""
        self.ticking = self.to_move
        while self.white_time > 0 and self.ticking == "white":
            print(f"Time left: {self.white_time} seconds", end="\r")
            self.white_time -= 1
            time.sleep(1)            

    def pause(self):
        """
        This method pauses the clock for both sides.

        to_move parameter created since self.ticking is set to None and
        nothing else is keeping track of which side's move it is.
        """
        self.to_move = self.ticking
        self.ticking = None

    def press_clock(self):
        if self.ticking == "white":
            self.ticking = "black"
            while self.black_time > 0 and self.ticking == "black":
                print(f"Time left: {self.black_time} seconds", end="\r")
                self.black_time -= 1
                time.sleep(1)
        elif self.ticking == "black":
            self.ticking == "white"
            while self.white_time > 0 and self.ticking == "white":
                print(f"Time left: {self.white_time} seconds", end="\r")
                self.white_time -= 1
                time.sleep(1)
    
    def set_clock(self, new_white_time, new_black_time, new_increment):
        self.new_white_time = new_white_time
        self.new_black_time = new_black_time
        self.new_increment = new_increment

if __name__ == "__main__":
    pass