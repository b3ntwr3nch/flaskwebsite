
emoji_to_binary = {'😞': '0', '😄': '1'}

emoji_sequence = "😞😄😞😞😄😞😞😞😞😄😞😄😞😄😄😞😞😄😞😞😞😞😄😄😞😄😞😞😄😞😄😄😞😞😄...😄😞"

binary_string = ''.join(emoji_to_blogTo_numbers(emoji) for emoji in emoji_sequence)

def split_into_chunks(binary_string, n):
    return [binary_string[i:i+n] for i in range(0, len(binary_string), n)]

def binary_to_text(binary_string):
    return ''.join(chr(int(binary_chunk, 2)) for binary_chunk in split_into_chunks(binary_string, 8))

decoded_text = binary_to_text(binary_string)
print(decoded_text)
