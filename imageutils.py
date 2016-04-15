'''General image functions'''

from io import BytesIO
from PIL import Image

def makeThumbnailBinary(picpath):
	'''Load the given picture file and make a binary from the jpeg thumbnail'''
	im = Image.open(picpath)
	im.thumbnail((200, 200), Image.ANTIALIAS)
	byteFile = BytesIO()
	im.save(byteFile, format="JPEG")
	return byteFile.getvalue()
