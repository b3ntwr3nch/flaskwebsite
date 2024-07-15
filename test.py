# Mapping emojis to binary values
emoji_to_binary = {'😞': '0', '😄': '1'}

# Define your large emoji sequence as a single string
emoji_sequence = "😞😄😞😞😄😞😞😞😞😄😞😄😞😄😄😞😞😄😞😞😞😞😄😄😞😄😞😞😄😞😄😄😞😞😄...😄😞"

# Convert the sequence of emojis to a binary string
binary_string = ''.join(emoji_to_blogTo_numbers(emoji) for emoji in emoji_sequence)

# Helper function to split the binary string into 8-bit chunks
def split_into_chunks(binary_string, n):
    return [binary_string[i:i+n] for i in range(0, len(binary_string), n)]

# Convert binary data to ASCII text
def binary_to_text(binary_string):
    return ''.join(chr(int(binary_chunk, 2)) for binary_chunk in split_into_chunks(binary_string, 8))

# Process the binary string to text
decoded_text = binary_to_text(binary_string)
print(decoded_text)
