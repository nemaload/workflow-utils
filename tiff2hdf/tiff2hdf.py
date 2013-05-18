#!/usr/bin/env python

# Note to davidad and pasky: 
# What license should we use? I just stuck the GPL in there as a placeholder.

# tiff2hdf converts TIFF images and image stacks to HDF5 datasets.
# Copyright (C) 2013 NEMALOAD

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Contact Information:
# NEMALOAD
# nemaload.com

import sys, argparse, os, ctypes, numpy, h5py, Image, subprocess

from wand.image import Image

class imageConversion:
	def __init__(self):
	#MODIFIES: self
	#EFFECTS: Initializes self

		self.width = 0
		self.height = 0
		self.bitdepth = 0
		self.colormode = 'undefined'
		self.rawImage = 0
		self.location = ''
		self.name = ''
		self.destination = ''
		self.format = ''
		self.numImages = 0

	def getImageDetails(self):
	#REQUIRES: self.setImageLocation must already be called
	#MODIFIES: self
	#EFFECTS: Gets various details about the input image
		with Image(filename=self.location) as img:
			self.width = img.width
			self.height = img.height
			self.bitdepth = img.depth
			self.format = img.format
			self.colormode = img.type
			self.numImages = img.frame_num #really unsure about this one


	def setImageLocation(self, inputPlace):
	#REQUIRES: inputPlace must be a path of a file.
	#MODIFIES: self
	#EFFECTS: Parses the inputPlace directory string.

		#check if input file is actually file
		if not os.path.isfile(inputPlace):
			sys.exit("Unexpected file error occurred while setting image location."
				+ " Exiting...")
		#get filename
		self.name = os.path.basename(inputPlace)
		self.location = inputPlace
	def setImageDestination(self, outputPlace):
	#REQUIRES: outputPlace to be a valid directory and setImageLocation to 
	#	already have been called.
	#MODIFIES: self
	#EFFECTS: Sets the proper output file on the image object.

		if os.path.isdir(outputPlace):
			self.destination = outputPlace + self.name
		else:
			self.destination = outputPlace
	def grayscaleCheck(self):
	#REQUIRES: self.getImageDetails must have already been called
	#EFFECTS: Return true if image is grayscale, false otherwise

		if self.type is 'grayscale':
			return true
		else:
			return false
	def colorCanBeConverted(self):
	#REQUIRES: self.getImageDetails must have already been called
	#EFFECTS: returns true if image can be converted to grayscale,
	# 	false otherwise.
		if self.type in ('truecolor', 'truecolormatte'):
			return true
		else:
			return false

	def setBitDepth(self, bitDepth):
		self.bitdepth = bitDepth

	def convertToGrayscale(self):
	#REQUIRES: self is an RGB image, can be converted, and OpenCL is all set up
	#EFFECTS: converts RGB to grayscale image
		subprocess.call(["./tiff2hdfGrayscaleConvert", self.location])
	
	def loadImageFrameToArray(self):
		img = Image.open(self.location)
		img.load()
		self.rawImage = numpy.asarray(img, dtype='uint' + self.bitdepth)
	
	def saveImageToBinaryFile(self):
		self.rawImage.astype(self.bitdepth).tofile(destination)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		prog='hdf5convert.py', 
		description='A tool to convert TIFF files to HDF5 datasets.')
	parser.add_argument("input", type=str,
		help="""The input directory to be converted. This can also
		be a filename in the case that the -s flag is set.""")
	parser.add_argument("output", type=str,
		help="""The directory to which the file should be output. This can also
		be a filename in the case that the -s flag is set.""")
	parser.add_argument(
		'-s',
		'--single',
		help="""Converts a single image.""",
		action="store_true")
	parser.add_argument(
		'-a', 
		'--all', 
		help="""Convert all TIFFs in current directory to HDF5 datasets, 
		output in current directory.""",
		action="store_true")
	parser.add_argument('-o', 
		'--overwrite', 
		help="""Overwrite all existing HDF5 files in directory.""",
		action="store_true")
	parser.add_argument('-r', 
		'--raw', 
		help='Convert TIFFs to raw images, not HDF5 datasets.',
		action="store_true")
	parser.add_argument('-c', 
		'--opencl', 
		help="""Accelerate RGB to grayscale conversionsion with 
		OpenCL(requires OpenCL dependencies)""",
		action="store_true")
	parser.add_argument('-b', 
		'--bitdepth', 
		help="""Convert all TIFF files to HDF5 datasets with N bit integers,
		where N is a valid number of bits (8, 16, 32, or 64 bits) 
		The default bit depth is 16 bits.""",
		nargs=1)

	args = parser.parse_args()

	inputPlace = args.input
	outputPlace = args.output
	#checking if -s flag is properly used
	if args.single and not (os.path.isfile(inputPlace) and os.path.isfile(outputPlace)):
		sys.exit("In singular mode both input and output must be files, not directories.")
	if not args.single and not (os.path.isdir(inputPlace) and os.path.isdir(outputPlace)):
		sys.exit("If not in singular mode, both input and output must be directory")
	#checking for valid bit depth
	if args.bitdepth and (args.bitdepth not in (8,16,32,64)):
		sys.exit("Invalid number of bits set(must be 8,16,32, or 64")

	#checking if openCL C lib is in directory if c flag is set
	if args.opencl and not os.path.isfile('./libtiff2hdf.so'):
		sys.exit("Please place the libtiff2hdf.so file in the same directory" +  
			" with the tiff2hdf.py file if using OpenCL.")









