import os
import re
import math
import nltk
from nltk.corpus import words
import random
from flask import Flask, render_template, request, jsonify, redirect, url_for
from google.cloud import firestore

nltk.download('words', quiet=True)

app = Flask(__name__)
db = firestore.Client()

def rot13_cipher(text, key=None, decode=False):
    return text.translate(str.maketrans(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'))

def atbash_cipher(text, key=None, decode=False):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    reversed_alphabet = alphabet[::-1]
    trans = str.maketrans(alphabet + alphabet.lower(), reversed_alphabet + reversed_alphabet.lower())
    return text.translate(trans)


def affine_cipher(text, key, decode=False):
    try:
        a, b = map(int, key.split(','))
    except ValueError:
        return "Invalid key. Please provide a key in the format 'a,b'"

    if a % 2 == 0 or a % 13 == 0:
        return "Invalid 'a' value. 'a' must be coprime with 26."

    m = 26

    def encrypt_char(char):
        if char.isalpha():
            x = ord(char.upper()) - ord('A')
            return chr(((a * x + b) % m) + ord('A'))
        return char

    def decrypt_char(char):
        if char.isalpha():
            y = ord(char.upper()) - ord('A')
            a_inv = pow(a, -1, m)
            return chr(((a_inv * (y - b)) % m) + ord('A'))
        return char

    result = ''
    for char in text:
        if decode:
            result += decrypt_char(char)
        else:
            result += encrypt_char(char)

    return result


def rail_fence_cipher(text, key, decode=False):
    try:
        rails = int(key)
    except ValueError:
        return "Invalid key. Please provide a numerical key."

    if rails < 2:
        return "Invalid number of rails. Must be at least 2."

    if not decode:
        # Encryption
        fence = [[None for _ in range(len(text))] for _ in range(rails)]
        rail = 0
        direction = 1
        for i, char in enumerate(text):
            fence[rail][i] = char
            rail += direction
            if rail == 0 or rail == rails - 1:
                direction *= -1
        return ''.join(char for rail in fence for char in rail if char is not None)
    else:
        # Decryption
        fence = [[None for _ in range(len(text))] for _ in range(rails)]
        rail = 0
        direction = 1
        for i in range(len(text)):
            fence[rail][i] = '*'
            rail += direction
            if rail == 0 or rail == rails - 1:
                direction *= -1
        index = 0
        for i in range(rails):
            for j in range(len(text)):
                if fence[i][j] == '*':
                    fence[i][j] = text[index]
                    index += 1
        result = []
        rail = 0
        direction = 1
        for _ in range(len(text)):
            result.append(fence[rail][_])
            rail += direction
            if rail == 0 or rail == rails - 1:
                direction *= -1
        return ''.join(result)


def columnar_transposition_cipher(text, key, decode=False):
    key = key.upper()
    key_order = sorted(range(len(key)), key=lambda k: key[k])

    if not decode:
        # Encryption
        cols = [''] * len(key)
        for i, char in enumerate(text):
            cols[key_order[i % len(key)]] += char
        return ''.join(cols)
    else:
        # Decryption
        cols = [''] * len(key)
        rows, remainder = divmod(len(text), len(key))
        for i in range(len(key)):
            if i < remainder:
                cols[key_order[i]] = text[i * (rows + 1):(i + 1) * (rows + 1)]
            else:
                cols[key_order[i]] = text[remainder * (rows + 1) + (i - remainder) * rows:
                                          remainder * (rows + 1) + (i - remainder + 1) * rows]
        result = ''
        for i in range(rows + (1 if remainder else 0)):
            for col in cols:
                if i < len(col):
                    result += col[i]
        return result

def emoji_cipher(text, key=None, decode=False):
    emoji_to_binary = {'😞': '0', '😄': '1'}
    binary_to_emoji = {'0': '😞', '1': '😄'}
    if decode:
        binary_string = ''.join(emoji_to_binary[emoji] for emoji in text if emoji in emoji_to_binary)
        return ''.join(chr(int(binary_chunk, 2)) for binary_chunk in [binary_string[i:i+8] for i in range(0, len(binary_string), 8)])
    else:
        binary_string = ''.join(format(ord(char), '08b') for char in text)
        return ''.join(binary_to_emoji[bit] for bit in binary_string)

def binary_cipher(text, key=None, decode=False):
    if decode:
        return ''.join(chr(int(binary, 2)) for binary in text.split())
    return ' '.join(format(ord(char), '08b') for char in text)

def vigenere_cipher(text, key, decode=False):
    key = key.upper()
    key_length = len(key)
    key_as_int = [ord(i) - ord('A') for i in key]
    result = ''
    i = 0
    for char in text:
        if char.isalpha():
            # Determine the shift
            shift = key_as_int[i % key_length]
            # Determine the ASCII offset (65 for uppercase, 97 for lowercase)
            ascii_offset = 65 if char.isupper() else 97
            # Apply the cipher
            if decode:
                result += chr((ord(char) - ascii_offset - shift) % 26 + ascii_offset)
            else:
                result += chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset)
            i += 1
        else:
            result += char
    return result

def caesar_cipher(text, key, decode=False):
    try:
        shift = int(key)
    except ValueError:
        return "Invalid key. Please provide a numerical key."
    if decode:
        shift = -shift
    return ''.join(chr((ord(char) - 65 + shift) % 26 + 65) if char.isupper() else
                   chr((ord(char) - 97 + shift) % 26 + 97) if char.islower() else char
                   for char in text)
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ciphers', methods=['GET', 'POST'])
def ciphers():
    descriptions = {
        'rot13': """
    <b>ROT13 Cipher</b><br>
    <p>The ROT13 cipher is a simple way to scramble text. Each letter in the text is replaced by the letter that is 13 places after it in the alphabet. Because there are 26 letters in the alphabet, doing this twice will get you back to the original text. It's often used as a basic way to hide text.</p>
    <p><b>How it Works:</b> Imagine the alphabet in a circle. For each letter in your text, move 13 steps forward. If you reach the end, continue from the start. For example, 'A' becomes 'N' and 'N' becomes 'A'.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Encrypted: "URYYB"<br>
    - Decryption is the same process: "URYYB" -> "HELLO"</p>
    """,
        'emoji': """
    <b>Emoji Cipher</b><br>
    <p>The Emoji cipher turns your text into a fun sequence of emojis. Each character in the text is first turned into its binary (computer language) form, and then each 0 or 1 in that binary code is replaced with an emoji.</p>
    <p><b>How it Works:</b> Each character is translated into an 8-bit binary string (e.g., 'A' becomes '01000001'). Each '0' in the binary string is replaced with a sad emoji (😞) and each '1' is replaced with a happy emoji (😄).</p>
    <p><b>Example:</b><br>
    - Original: "HI"<br>
    - Binary: "01001000 01001001"<br>
    - Encrypted: "😄😞😞😄😄😄😄😞 😄😞😄😄😞😞😄😞"<br>
    - Decryption involves converting the emojis back to binary, then to text.</p>
    """,
        'binary': """
    <b>Binary Cipher</b><br>
    <p>The Binary cipher converts text into binary code, which is a series of 0s and 1s used in computing. Each character in the text is translated into its binary (ASCII) representation.</p>
    <p><b>How it Works:</b> Each character is translated into an 8-bit binary string (e.g., 'A' becomes '01000001'). The binary strings for each character are then joined with spaces in between.</p>
    <p><b>Example:</b><br>
    - Original: "HI"<br>
    - Encrypted: "01001000 01001001"<br>
    - Decryption involves converting the binary strings back to characters.</p>
    """,
        'vigenere': """
    <b>Vigenère Cipher</b><br>
    <p>The Vigenère cipher is a way to encrypt alphabetic text using a keyword. The keyword helps to shift the letters of the text differently, making the encryption more complex than simple ciphers like Caesar.</p>
    <p><b>How it Works:</b> Each letter in the text is shifted according to the corresponding letter in the keyword. If the keyword is shorter than the text, it is repeated to match the length of the text. For example, if the text is 'HELLO' and the keyword is 'KEY', the keyword is repeated to 'KEYKE'.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Key: "KEY"<br>
    - Encrypted: "RIJVS"<br>
    - Decryption reverses the process using the same key.</p>
    """,
        'caesar': """
    <b>Caesar Cipher</b><br>
    <p>The Caesar cipher is a simple and famous method of encryption where each letter in the text is shifted a fixed number of places in the alphabet. It was named after Julius Caesar, who used it in his private correspondence.</p>
    <p><b>How it Works:</b> Each letter in the text is replaced by a letter some fixed number of positions down the alphabet. For example, with a shift of 3, 'A' becomes 'D', 'B' becomes 'E', and so on. If the shift moves past 'Z', it wraps around to the beginning of the alphabet.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Shift: 3<br>
    - Encrypted: "KHOOR"<br>
    - Decryption involves shifting in the opposite direction.</p>
    """,
        'atbash': """
    <b>Atbash Cipher</b><br>
    <p>The Atbash cipher is a simple substitution cipher where each letter of the alphabet is replaced by the letter at the same position from the end of the alphabet. It's like writing the alphabet backward and matching each letter from the start to the end.</p>
    <p><b>How it Works:</b> Each letter in the text is replaced by the letter that is the same distance from the end of the alphabet. For example, 'A' is replaced by 'Z', 'B' by 'Y', and so on.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Encrypted: "SVOOL"<br>
    - Decryption is the same process as encryption.</p>
    """,
        'affine': """
    <b>Affine Cipher</b><br>
    <p>The Affine cipher is a type of substitution cipher that uses mathematical functions to encrypt the text. It uses a pair of keys (a and b) to transform each letter into a new one. This makes it more complex than the Caesar cipher.</p>
    <p><b>How it Works:</b> Each letter in the plaintext is encrypted with the function (a * x + b) mod 26, where 'a' and 'b' are keys, and 'x' is the position of the letter in the alphabet (A=0, B=1, etc.). The 'a' value must be coprime with 26. Decryption uses the modular multiplicative inverse of 'a'.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Key: '5,8' (a=5, b=8)<br>
    - Encrypted: "RCLLA"<br>
    - Decryption reverses the process using the same key.</p>
    """,
        'rail_fence': """
    <b>Rail Fence Cipher</b><br>
    <p>The Rail Fence cipher is a type of transposition cipher that arranges the text in a zigzag pattern across multiple rows (or "rails") and then reads it off row by row. This scrambles the letters in a way that's different from substitution ciphers.</p>
    <p><b>How it Works:</b> The text is written diagonally in a zigzag pattern across multiple rows, and then read off row by row to create the encrypted text. To decrypt, you need to recreate the zigzag pattern and read the text horizontally.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Rails: 3<br>
    - Encrypted: "HOELL"<br>
    - Decryption involves reconstructing the zigzag pattern and reading the text horizontally.</p>
    """,
        'columnar_transposition': """
    <b>Columnar Transposition Cipher</b><br>
    <p>The Columnar Transposition cipher is a type of transposition cipher where the text is written out in rows and then read off in columns according to a keyword. This rearranges the order of the letters, making the text harder to read without the keyword.</p>
    <p><b>How it Works:</b> The plaintext is written out in rows under the keyword. The columns are then rearranged based on the alphabetical order of the keyword's letters. The ciphertext is read off column by column. To decrypt, you need to rearrange the columns back to their original order based on the keyword.</p>
    <p><b>Example:</b><br>
    - Original: "HELLO"<br>
    - Key: "KEY"<br>
    - Arranged in columns: 
      K E Y
      H E L
      L O
    - Rearranged columns:
      E K Y
      E H L
      O L
    - Encrypted: "EOHLL"<br>
    - Decryption involves rearranging the columns back to their original order using the key.</p>
    """
    }

    results = {}
    keys = {}
    if request.method == 'POST':
        for cipher_name in descriptions.keys():
            input_text = request.form.get(f'input_{cipher_name}', '')
            cipher_key = request.form.get(f'key_{cipher_name}', '')
            operation = request.form.get(f'operation_{cipher_name}', 'encode')
            decode = operation == 'decode'
            try:
                cipher_function = globals()[f"{cipher_name}_cipher"]
                results[cipher_name] = cipher_function(input_text, key=cipher_key, decode=decode)
            except Exception as e:
                results[cipher_name] = f"Error processing {cipher_name}: {str(e)}"
            keys[cipher_name] = cipher_key
        return jsonify(results)
    else:
        return render_template('ciphers.html', keys=keys, descriptions=descriptions, results=results)


# Placeholder routes for future pages
@app.route('/pwnagotchi')
def pwnagotchi():
    return render_template('pwnagotchi.html')


@app.route('/sdr')
def sdr():
    return render_template('sdr.html')


@app.route('/audio_cipher')
def audio_cipher():
    return render_template('audio_cipher.html')


import math
import re
import random
from nltk.corpus import words

common_passwords = set(["password", "123456", "qwerty", "admin", "letmein", "welcome", "123123", "admin123"])
english_words = set(words.words())

def calculate_entropy(password):
    return len(password) * math.log2(94)  # Assuming 94 printable ASCII characters

def estimate_crack_time(entropy):
    # Assuming 1 billion guesses per second
    guesses = 2 ** entropy
    seconds = guesses / 1_000_000_000

    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        return f"{seconds / 60:.2f} minutes"
    elif seconds < 86400:
        return f"{seconds / 3600:.2f} hours"
    elif seconds < 31536000:
        return f"{seconds / 86400:.2f} days"
    elif seconds < 3153600000:  # 100 years
        return f"{seconds / 31536000:.2f} years"
    else:
        return "more than 100 years"

def is_common_password(password):
    return password.lower() in common_passwords

def is_single_word(password):
    return password.lower() in english_words

def detect_keyboard_pattern(password):
    common_patterns = [
        "qwerty", "asdfgh", "zxcvbn", "123456", "qwertz", "azerty"
    ]
    lower_pass = password.lower()
    return any(pattern in lower_pass for pattern in common_patterns)

def get_fun_fact():
    facts = [
        "The most common password is still '123456'. Facepalm moment!",
        "It would take 22 billion years to crack a 20-character password using current methods.",
        "The average person has 100 passwords. That's a lot of 'forgot password' clicks!",
        "Passwords '123456' and 'password' are so common, they'd be cracked in less than a second!",
        "The strongest passwords are actually passphrases - a string of random words.",
        "69% of people admit to sharing their passwords with others. Don't be one of them!",
        "A 12-character password takes 62 trillion times longer to crack than a 6-character password."
    ]
    return random.choice(facts)

def get_absurd_scenario(entropy):
    if entropy < 40:
        return ("Your password is so weak, it's like trying to protect your house with a "
                "door made of wet paper. A determined toddler could break in while taking a nap.")
    elif entropy < 60:
        return ("If your password were a fortress, it would be made of LEGO. Sure, stepping "
                "on it hurts, but a motivated attacker with a vacuum cleaner could dismantle it "
                "in about the time it takes to microwave a burrito.")
    elif entropy < 80:
        return ("Your password is like a medieval castle... in Minecraft. It looks impressive, "
                "but a team of bored teenagers could probably crack it over a long weekend, "
                "fueled by energy drinks and pizza.")
    elif entropy < 100:
        return ("Congratulations! Your password is like the Death Star. Extremely secure, "
                "unless someone finds that one tiny exhaust port. It would take a computer "
                "the size of Jupiter about as long as it takes for a sloth to run a marathon "
                "to crack this password.")
    else:
        return ("Wow! Your password is so strong, it's like trying to break into Fort Knox "
                "if it were guarded by ninjas, on the moon. By the time someone cracks this, "
                "we'll probably be communicating telepathically with our AI overlords.")


def check_password(password):
    entropy = calculate_entropy(password)

    if is_common_password(password):
        return {
            "strength": "weak",
            "scenario": "Your password is so common, it's like using 'Open Sesame' to guard Fort Knox.",
            "crack_time": {"online": "Instantly", "offline_slow": "Instantly", "offline_fast": "Instantly"},
            "has_keyboard_pattern": False,
            "fun_fact": "Your password is more common than a 'Live, Laugh, Love' sign!",
            "entropy_explanation": f"Your password has {entropy:.2f} bits of entropy. Common passwords have effectively zero entropy.",
            "advice": ["This password is extremely common. Please choose a completely different password!"],
            "entropy": entropy  # Add this line
        }

    if is_single_word(password):
        return {
            "strength": "weak",
            "scenario": "Your password is a single word? That's like using a paper airplane to cross the Atlantic!",
            "crack_time": {"online": estimate_crack_time(entropy / 100),
                           "offline_slow": estimate_crack_time(entropy / 10),
                           "offline_fast": estimate_crack_time(entropy)},
            "has_keyboard_pattern": False,
            "fun_fact": "Single word passwords are like using a paper airplane to cross the Atlantic!",
            "entropy_explanation": f"Your password has {entropy:.2f} bits of entropy. Single word passwords are vulnerable to dictionary attacks.",
            "advice": ["Avoid using single words. Try a phrase with multiple words and some numbers or symbols!"],
            "entropy": entropy  # Add this line
        }

    scenario = get_absurd_scenario(entropy)

    has_uppercase = re.search(r"[A-Z]", password) is not None
    has_lowercase = re.search(r"[a-z]", password) is not None
    has_digit = re.search(r"\d", password) is not None
    has_special = re.search(r"[!@#$%^&*(),.?\":{}|<>]", password) is not None

    advice = []
    if not has_uppercase:
        advice.append("Add some uppercase letters. It's like adding a moat to your LEGO fortress!")
    if not has_lowercase:
        advice.append("Throw in some lowercase letters. It's like adding camouflage to your Death Star!")
    if not has_digit:
        advice.append("Sprinkle in some numbers. It's like giving your ninja guards laser eyes!")
    if not has_special:
        advice.append("Use special characters. It's like adding a force field to your moon base!")

    result = {
        "strength": "strong" if entropy >= 80 else "moderate" if entropy >= 60 else "weak",
        "scenario": scenario,
        "crack_time": {
            "online": estimate_crack_time(entropy / 100),
            "offline_slow": estimate_crack_time(entropy / 10),
            "offline_fast": estimate_crack_time(entropy)
        },
        "has_keyboard_pattern": detect_keyboard_pattern(password),
        "fun_fact": get_fun_fact(),
        "entropy_explanation": f"Your password has {entropy:.2f} bits of entropy. "
                               "Password entropy is a measure of how unpredictable a password is. "
                               "The higher the entropy, the stronger the password!",
        "advice": advice,
        "entropy": entropy  # Add this line
    }

    if result["has_keyboard_pattern"]:
        result["advice"].append(
            "Avoid keyboard patterns in your password. They're easier to guess than the plot of a soap opera!")

    return result

@app.route('/password-checker', methods=['GET', 'POST'])
def password_checker():
    if request.method == 'POST':
        password = request.form['password']
        result = check_password(password)
        print("Returning result:", result)
        return jsonify(result)
    return render_template('password_checker.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)