'''General image functions'''

from io import BytesIO
from PIL import Image

def make_thumbnail_binary(picpath):
    '''Load the given picture file and make a binary from the jpeg thumbnail'''
    with open(picpath, "rb") as picfile:
        image = Image.open(picfile)
        image.thumbnail((200, 200), Image.ANTIALIAS)
        byte_file = BytesIO()
        image.save(byte_file, format="JPEG")
    return byte_file.getvalue() if byte_file else None

def hex_str(byteval):
    '''Turn a byte value into a two-digit hex code'''
    codes = "0123456789abcdef"
    return codes[(byteval//16)%16] + codes[byteval%16]

def bytes_to_string(in_bytes):
    '''Turn a series of bytes into a string'''
    if in_bytes:
        return "".join([hex_str(i) for i in in_bytes])
    return None

def string_to_bytes(in_str):
    '''Turn a string into a series of bytes'''
    pairs = [in_str[i]+in_str[i+1] for i in range(len(in_str)) if i%2 == 0]
    result = bytearray()
    codes = "0123456789abcdef"
    for pair in pairs:
        curr_byte = codes.index(pair[0]) * 16 + codes.index(pair[1])
        result.append(curr_byte)
    return result
