'''General image functions'''

from io import BytesIO
from PIL import Image

def makeThumbnailBinary(picpath):
	'''Load the given picture file and make a binary from the jpeg thumbnail'''
	with open(picpath, "rb") as f:
		im = Image.open(f)
		im.thumbnail((200, 200), Image.ANTIALIAS)
		byteFile = BytesIO()
		im.save(byteFile, format="JPEG")
	return byteFile.getvalue()

def hexStr(b):
	'''Turn a byte value into a two-digit hex code'''
	codes = "0123456789abcdef"
	return codes[(b//16)%16] + codes[b%16]

def bytesToString(b):
	'''Turn a series of bytes into a string'''
	if b:
		return "".join([hexStr(i) for i in b])

def stringToBytes(s):
	'''Turn a string into a series of bytes'''
	pairs = [s[i]+s[i+1] for i in range(len(s)) if i%2 == 0]
	result = bytearray()
	codes = "0123456789abcdef"
	for p in pairs:
		currByte = codes.index(p[0]) * 16 + codes.index(p[1])
		result.append(currByte)
	return result
