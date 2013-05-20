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

#To install PIL,
#http://athenageek.wordpress.com/2009/06/09/easy_install-pil-not-so-easy/

import sys, argparse, os, ctypes, numpy, h5py

from wand.image import Image as wandImage
from scipy import misc
import Image

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
		with wandImage(filename=self.location) as img:
			self.width = img.width
			self.height = img.height
			self.bitdepth = img.depth
			self.format = img.format
			self.colormode = img.type
			# using PIL, seek until EOF error is experienced, and set numImages to how many
			# 	iterations it got through before that
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

	def loadImageFrameToArray(self):
		img = Image.open(self.location)
		#to get 		
		self.rawImage = numpy.array(img)
		#now the image is a numpy array which can be manipulated
		#http://stackoverflow.com/questions/384759/pil-and-numpy
		#.seek() will change frames

	def saveAsRawNumpyArray(self):
	# REQUIRES: rawImage must be set
	# MODIFIES: disk
	# EFFECTS: Saves the numpy array to disk with the filename of the iamge
		numpy.save(self.location, self.rawImage)


class fileObject:
	def __init__(self, name):
	# REQUIRES: Name be a filename CONTAINING PATH of the HDF5 set to be created.
	# MODIFIES: self
		
		self.name = name
		self.filename = self.name + 'hdf5'
		self.width = 0
		self.height = 0
		self.dtype = ''
		self.file = None

	def __del__(self):
		if self.file != None:
			self.file.close()

	def checkIfFileExists(self):
	# REQUIRES: self.filename is set
	# EFFECTS: Returns true if file to be created already exists
		if os.path.isfile(self.filename):
			return true
		else:
			return false
	def createFile(self):
	# REQUIRES: self.filename is set
	# EFFECTS: Initializes the self.file object	
		self.file = h5py.File(self.filename, 'w')
	def createImageGroup(self):
	# REQUIRES: self.file is initialized
	# MODIFIES: self.file
	# EFFECTS: Creates an image group called "images" within the HDF5 file.
		self.imageGroup = self.file.create_group("images")
	def createNewDataset(self, datasetName):
	# REQUIRES: image group is already created
	# MODIFIES: self.imageGroup
	# EFFECTS: Creates a new dataset, and stores it in the self.currentDataset variable
	# NOTE: This corresponds to a frame in a stack typically
		self.currentDataset = self.imageGroup.create_dataset(
			datasetName, 
			(self.width, self.height),
			dtype='i' + str(self.bitdepth/8))
	def setAttribute(self, attributeName, stringContent):
	#Requires: current group must be set
		self.imageGroup.attrs[attributeName] = stringContent

	def saveImageToDataset(self, imageToSave):
	# REQUIRES: Image must be a numpy dataset
		if self.currentDataset.shape = (imageToSave.width, imageToSave.height)
			self.currentDataset = imageToSave.rawImage
		else:
			print "Dimension mismatch! Exiting..."
			sys.exit(1)


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
	#parser.add_argument('-c', 
	#	'--opencl', 
	#	help="""Accelerate RGB to grayscale conversion with 
	#	OpenCL(requires OpenCL dependencies)""",
	#	action="store_true")
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
	#if args.opencl and not os.path.isfile('./libtiff2hdf.so'):
	#	sys.exit("Please place the libtiff2hdf.so file in the same directory" +  
	#		" with the tiff2hdf.py file if using OpenCL.")
	
	#File conversion routine for one file
	#Create the image we are going to convert
	imageToConvert = imageConversion()
	#Tell the program where the file to convert is
	imageToConvert.setImageLocation(inputPlace)
	#Get various details about the image
	imageToConvert.getImageDetails()
	#Image must be grayscale, check for this
	if not imageToConvert.grayscaleCheck:
		print "ERROR: Image " + imageToConvert.name + " is not grayscale."
		print "Only grayscale images are supported. Please convert to grayscale and try again."
		sys.exit(1)

	#We've got to create a file now
	
	for framenumber in range(0, imageToConvert.numImages - 1):
		#grab current frame and put in rawImage array
		imageToConvert.loadImageFrameToArray()













