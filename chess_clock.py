import time

class ChessClock():
    def __init__(self, white_time=180, black_time=180, increment=2, to_move="white"):
        """
        Time in seconds
        """
        self.white_time = white_time
        self.black_time = black_time
        self.increment = increment
        self.to_move = to_move

    def start_countdown(self):
        pass

    def pause(self):
        pass

    def press_clock(self):
        pass
    
    def set_white_time(self, new_time):
        self.white_time = new_time

    def set_black_time(self, new_time):
        self.black_time = new_time

