from vosk import Model, KaldiRecognizer
import pyaudio
import json

model = Model("model")
cap = pyaudio.PyAudio()

format_dict = {
    "queen": "Q",
    "king": "K",
    "bishop": "B",
    "knight": "N",
    "rook": "R",
    "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8",
    "takes": "x"
}

# replacing grammar with a list of allowed words to recognise chess notation
# fixes tested issues; e.g. e4 mistaken for evil
letters = ["a", "b", "c", "d", "e", "f", "g", "h"]
numbers = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
coords = [f"{letter} {number}" for number in numbers for letter in letters]
allowed = [
    "king", "queen", "bishop", "knight", "rook",
    "takes", "castle", "kingside", "queenside",
    "equals", "to"
] + coords
grammar = json.dumps(allowed)
recognizer = KaldiRecognizer(model, 16000, grammar)
recognizer.SetWords(True)

def start_listening():

    stream = cap.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8192
    )
    stream.start_stream()

    while True:
        data = stream.read(4096)
        
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")

            # add logic for castling

            parsed_string = ""
            for word in text.split():
                if word in format_dict:
                    parsed_string += format_dict[word]
                else:
                    parsed_string += word
            print(parsed_string)

if __name__ == "__main__":
    start_listening()