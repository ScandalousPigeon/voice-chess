from vosk import Model, KaldiRecognizer
import pyaudio
import json
import threading

WORD_MAP = {
    "queen": "Q", "king": "K", "bishop": "B", "knight": "N", "rook": "R",
    "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8",
    "takes": "x", "equals": "=",
    "castle king side": "O-O", "castle queen side": "O-O-O"
}

# replacing grammar with a list of allowed words to recognise chess notation
# fixes tested issues; e.g. e4 mistaken for evil
# add commands to vocab?? e.g. resign, new game, etc.
letters = ["a", "b", "c", "d", "e", "f", "g", "h"]
numbers = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
coords = [f"{letter} {number}" for number in numbers for letter in letters]
allowed = [
    "king", "queen", "bishop", "knight", "rook",
    "takes", "castle", "equals", "to", "side"
] + coords
_GRAMMAR = json.dumps(allowed)

def _normalise(raw: str) -> str:
    """
    Convert raw recognizer output into SAN.

    Examples:
      - 'castle king side' -> 'O-O'
      - 'castle queen side' -> 'O-O-O'
      - 'e four' -> 'e4'
      - promotions: 'e eight equals queen' -> 'e8=Q'
      - basic piece letters: 'knight f three' -> 'Nf3'
    """
    if not raw:
        return ""
    # draw offer or resigning??
    parsed_string = ""
    if raw == "castle king side":
        return "O-O"
    if raw == "castle queen side":
        return "O-O-O"
    for word in raw.split():
        if word in WORD_MAP:
            parsed_string += WORD_MAP[word]
        else:
            parsed_string += word
    return parsed_string

class VoiceListener:
    """
    Class that listens to voice input and passes it off to something else.

    "Something else" being the on_text parameter. This should be a function that decides what to do with the output.

    Fields:
        on_text (function): the callback function to which the input is passed.
        model:              loads the voice recognition model from file path.
        recognizer:         loads the recognizer.
        pa:                 loads pyaudio, which is responsible for communicating with the microphone.
        stream:             placeholder for when the microphone starts streaming.
        th:                 placeholder for when the thread is started (threading is needed to avoid interfering with GUI).
        stop:               placeholder for stopping the thread.
    """

    def __init__(self, on_text):
        self._on_text = on_text
        self._model = Model("model")
        self._recognizer = KaldiRecognizer(self._model, 16000, _GRAMMAR)
        self._recognizer.SetWords(True)

        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._th = None
        self._stop = threading.Event()

    def start(self):
        """
        Method to start the listening thread.
        """
        if self._th and self._th.is_alive():
            return

        self._stop.clear()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8192,
        )
        self._stream.start_stream()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        """Request the listener thread to stop and wait for it to finish."""
        self._stop.set()
        if self._th and self._th.is_alive():
            self._th.join(timeout=1.0)
        self._th = None

    def _run(self):
        try:
            while not self._stop.is_set():
                data = self._stream.read(4096, exception_on_overflow=False)
                if self._recognizer.AcceptWaveform(data):
                    result = json.loads(self._recognizer.Result())
                    text = result.get("text", "")
                    self._on_text(_normalise(text))
        finally:
            # safely close the audio stream here
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None

if __name__ == "__main__":
    import time

    def on_text_received(text):
        print(f"Recognised: {text}")

    listener = VoiceListener(on_text_received)

    print("Starting listener... Speak into the microphone.")
    listener.start()

    try:
        time.sleep(20)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected — stopping listener.")
    finally:
        listener.stop()
        print("Listener stopped cleanly.")
    