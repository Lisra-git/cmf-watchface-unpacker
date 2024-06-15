import lz4.block
import os
from PIL import Image
import numpy as np


def unpacklz4(data):
	return lz4.block.decompress(data,uncompressed_size=0x99FFFF)

def getsize(header):
	hexArray = bytearray.fromhex(header)
	hexArray[0], hexArray[1], hexArray[2], hexArray[3] = hexArray[3], hexArray[2], hexArray[1], hexArray[0]
	header_32bit = int.from_bytes(hexArray, byteorder='big')
	width = (header_32bit >> 10) & 0x3FF
	height = (header_32bit >> 21) & 0x7FF
	return width, height

def write_rgb565_to_png(data, width, height, filename):
	"""
	Writes RGB565 data to a PNG file.

	Args:
	  data: A bytes-like object containing the RGB565 data.
	  width: The width of the image in pixels.
	  height: The height of the image in pixels.
	  filename: The name of the output PNG file.
	"""
	# Convert the RGB565 data to RGB tuples
	pixels = []
	for i in range(0, len(data), 2):
		# Swapping bytes for little endian
		value = (data[i + 1] << 8) | data[i]
		r = (value >> 11) & 0x1F
		g = (value >> 5) & 0x3F
		b = value & 0x1F
		# Scaling values from 5 or 6 bits to 8 bits
		r = (r << 3) | (r >> 2)
		g = (g << 2) | (g >> 4)
		b = (b << 3) | (b >> 2)
		pixels.append((r, g, b))

	# Create the image object
	img = Image.new("RGB", (width, height))
	img.putdata(pixels)

	# Save the image as a PNG
	img.save(filename)

def write_rgb32_to_png(data, width, height, filename):
	"""
	Writes RGBA data to a PNG file.

	Args:
	  data: A bytes-like object containing the RGBA data.
	  width: The width of the image in pixels.
	  height: The height of the image in pixels.
	  filename: The name of the output PNG file.
	"""
	# Convert the RGBA data to RGB tuples
	pixels = []
	for i in range(0, len(data), 4):
		r = data[i]
		g = data[i + 1]
		b = data[i + 2]
		a = data[i + 3]
		pixels.append((b,g,r, a))

	# Create the image object
	img = Image.new("RGBA", (width, height))
	img.putdata(pixels)

	# Save the image as a PNG
	img.save(filename)


def convert_cf_alpha_4bit_to_png(data_block, width, height, filename):
    """Decodes a 4-bit alpha format to a PNG image.

    Args:
        data_block: The byte array containing the encoded data.
        width: The width of the image in pixels.
        height: The height of the image in pixels.
        filename: The output filename for the PNG image.
    """

    # Set fixed color to white (all channels 255)
    fixed_color = (255, 255, 255)

    # Create PNG writer object
    with open(filename, "wb") as f:
        img = Image.new("RGBA", (width, height), fixed_color)
        # Iterate over each pixel and extract alpha value
        pixels = []
        for y in range(height):
            for x in range(width):
                # Calculate index and extract byte from data block
                byte_index = y * ((width + 1) // 2) + x // 2
                byte_value = data_block[byte_index]

                # Extract alpha value based on odd/even pixel
                alpha = (byte_value >> (4 * (1 - x % 2))) & 0xF

                # Pixel is greyscale based on alpha
                pixel = (255, 255, 255, alpha * 16)

                # Append pixel to output data
                pixels.append(pixel)

        img.putdata(pixels)
        img.save(f, "PNG")

def main():
#parse .bin file
	subwidgetStreams = []
	assets = []
	totalElements = 0
	#get .bin file in current folder
	watchface = ""
	files = [f for f in os.listdir('.') if os.path.isfile(f)]
	for f in files:
		if f.endswith(".bin"):
			watchface = open(f, 'rb').read()
	watchface = bytearray(watchface)
	wf_totalsize = len(watchface)
	#get subwidget lenght at 0x25-26
	subwidgetLenght = watchface[0x25:0x27]
	subwidgetLenght = int.from_bytes(subwidgetLenght, byteorder='little')
	subwidgetLenght = subwidgetLenght + 0x27
	#check if dir extracted exist
	if not os.path.exists('extracted'):
		os.makedirs('extracted')
	#extract subwidget to a file 
	subwidget = watchface[0x27:subwidgetLenght]
	subwidgetFile = open("extracted/FunctionStore.bin", 'wb')
	subwidgetFile.write(subwidget)

	assetStoreLenght = watchface[0x1c:0x1f]
	assetStoreLenght = int.from_bytes(assetStoreLenght, byteorder='little')
	#export asset Store to a file
	assetStore = watchface[subwidgetLenght:subwidgetLenght + assetStoreLenght]
	assetStoreFile = open("extracted/assetStore.bin", 'wb')
	assetStoreFile.write(assetStore)
	curLenAsset = 0
	while curLenAsset < assetStoreLenght:
		assetLenght = watchface[subwidgetLenght + curLenAsset + 4:subwidgetLenght + curLenAsset + 8]
		assetLenght = int.from_bytes(assetLenght, byteorder='little')
		assets.append(subwidgetLenght + curLenAsset)
		curLenAsset = curLenAsset + assetLenght + 8

	for asset in assets:
		#get header (first 4bytes)
		header = watchface[asset:asset+4]
		print('header')
		print(header.hex())
		#get size from header
		width, height = getsize(header.hex())
		print("width: " + str(width))
		print("height: " + str(height))
		#get compressed lenght at 4th bytes and 4th long
		print("decompressing")
		compressedLenght = watchface[asset+4:asset+8]
		print(compressedLenght.hex())
		#print(compressedLenght.hex())
		assetExtracted = watchface[asset+8:asset+8+int.from_bytes(compressedLenght, byteorder='little')]
		#print(assetExtracted.hex())
		try:
			assetDecompressed = unpacklz4(bytearray(assetExtracted))
			if not os.path.exists('assets'):
				os.makedirs('assets')
			#save to file with asset name
			assetFile = open("assets/" + str(asset)+'.bin', 'wb')
			assetFile.write(assetDecompressed)
			if (header[0:1] == b'\x18'):
				write_rgb32_to_png(assetDecompressed, width, height, "assets/" + str(asset) +'.png')
			elif (header[0:1] == b'\x04'):
				write_rgb565_to_png(assetDecompressed, width, height, "assets/" + str(asset) +'.png')
			elif (header[0:1] == b'\x0d'):
				convert_cf_alpha_4bit_to_png(assetDecompressed, width, height, "assets/" + str(asset) +'.png')
			assetDecompressed = ""
			assetExtracted = ""
		except Exception as e:
			print("error decompressing")
			print(e)
			#assetDecompressed = assetExtracted
		#check if assets folder exist
	

	#print(subwidgetStreams)
	#for bitarray in subwidgetStreams:
		#print(bitarray.hex())
	watchface = watchface[0x32:0x1000]
	#print(watchface.hex())
	print("expected elements: " + str(totalElements))
	#len of assets
	print("assets: " + str(len(assets)))


if __name__ == "__main__":
	os.chdir(os.path.dirname(__file__))
	main()