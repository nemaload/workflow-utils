#!/usr/bin/env python

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

#Note: PIL has a bug when it comes to 16 bit images. I found a workaround here: http://stackoverflow.com/questions/7684695/numpy-array-of-an-i16-image-file
# This is why you might see some strange code.
import sys, argparse, os, ctypes, numpy, h5py, glob
from time import gmtime, strftime

from wand.image import Image as wandImage
#from scipy import misc
import scipy
import Image
#apparently ^that module has a bug with uncompressed 16 bit tiffs... might as well throw in another dependency
import matplotlib.pyplot as plt
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
		self.currentImage = 0
		self.img = None

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
			#self.numImages = img.frame_num #really unsure about this one
			self.numImages = 0
			tempImage = Image.open(self.location)
			try:
				while 1:
					tempImage.seek(self.numImages)
					self.numImages +=1
			except EOFError:
				tempImage.seek(0)
				pass
			#tempImage.close()
			print "Width: " + str(self.width)
			print "Height: " + str(self.height)
			print "Bit depth: " + str(self.bitdepth)
			print "Format: " + str(self.format)
			print "Color mode: " + str(self.colormode)
			print "Frames: " + str(self.numImages)



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

	def loadImageFromFile(self):
		self.img = Image.open(self.location)
		#self.img = plt.imread(self.location)
	def loadImageFrameToArray(self):
		# REQUIRES: file is valid, image to be opened
		# MODIFIES: self.rawImage
		# EFFECTS: Pulls the current frame, then SEEKS to the next one using try
		#to get

		#this doesn't work for some reason self.rawImage = numpy.array(self.img)
		self.rawImage = plt.imread(self.location)
		print "Converted to array. Dimensions: " + str(self.rawImage.shape)
		#print "Array width: " + str(self.rawImage.shape[0])
		#print "Array height: " + str(self.rawImage.shape[1])
		#this is the work around to the shitty PIL library

		try:
			self.img.seek(self.currentImage)
			self.currentImage += 1
			#break
		except EOFError:
			print "Reached end of stacked image..."


		#now the image is a numpy array which can be manipulated
		#http://stackoverflow.com/questions/384759/pil-and-numpy
		#.seek() will change frames

	def saveAsRawNumpyArray(self):
		# REQUIRES: rawImage must be set
		# MODIFIES: disk
		# EFFECTS: Saves the numpy array to disk with the filename of the iamge
		numpy.save(self.location, self.rawImage)

	def printMax(self):
		print numpy.amax(self.rawImage)

class fileObject:
	def __init__(self, name, width, height):
	# REQUIRES: Name be a filename CONTAINING PATH of the HDF5 set to be created.
	# MODIFIES: self

		self.name = name
		self.filename = self.name + '.hdf5'
		self.width = width
		self.height = height
		self.dtype = ''
		self.bitdepth = 0
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
	def setBitDepth(self, bits):
		self.bitdepth = bits

	def createFile(self):
	# REQUIRES: self.filename is set
	# EFFECTS: Initializes the self.file object
		self.file = h5py.File(self.filename, 'w')
	def createImageGroup(self):
	# REQUIRES: self.file is initialized
	# MODIFIES: self.file
	# EFFECTS: Creates an image group called "images" within the HDF5 file.
		self.imageGroup = self.file.create_group("images")
	def createNewDataset(self, datasetName, data):
	# REQUIRES: image group is already created
	# MODIFIES: self.imageGroup
	# EFFECTS: Creates a new dataset, and stores it in the self.currentDataset variable
	# NOTE: This corresponds to a frame in a stack typically
		dt = 'uint' + str(self.bitdepth)
		#self.currentDataset = self.imageGroup.create_dataset(
		#	datasetName,
		#	(self.width, self.height),
		#	dt)
		self.currentDataset = self.imageGroup.create_dataset(
			datasetName,
			data=data,
			dtype=dt)
	def setAttribute(self, attributeName, stringContent):
	#Requires: current group must be set
		self.imageGroup.attrs[attributeName] = stringContent

	def saveImageToDataset(self, imageToSave):
	# REQUIRES: Image must be a numpy dataset
		if self.currentDataset.shape[0] == imageToSave.width and self.currentDataset.shape[1] == imageToSave.height:
		#if self.currentDataset.shape == tuple(imageToSave.width, imageToSave.height)
			print "Setting current dataset equal"
			self.currentDataset = imageToSave.rawImage
		else:
			print "Dimension mismatch! Exiting..."
			sys.exit(1)


if __name__ == '__main__':
	#usage related code
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
		help="""WARNING THIS IS NOT FUNCTIONAL: Convert all TIFF files to HDF5 datasets with N bit integers,
		where N is a valid number of bits (8, 16, 32, or 64 bits)
		The default bit depth is 16 bits.""",
		nargs=1)

	args = parser.parse_args()

	inputPlace = args.input
	outputPlace = args.output
	#checking if -s flag is properly used
	if args.single:
		#first, check that input file exists.
		if not os.path.isfile(inputPlace):
			sys.exit("Input file does not exist.")
		#second, check that output file does NOT exist, and outputPlace is not a directory.
		if os.path.isfile(outputPlace) and not args.overwrite:
			sys.exit("Output file exists. To overwrite, use the -o flag.")
	if not args.single:
		if not (os.path.isdir(inputPlace) and os.path.isdir(outputPlace)):
			sys.exit("Both input and output directories must exist.")
	#First, check if the input directory and output directory exist.
		print "Finding tiff files..."
		#first format the string to remove a trailing slash
		if inputPlace[-1] is '/':
			inputPlace = inputPlace[:-1]
		if outputPlace[-1] is '/':
			outputPlace = outputPlace[:-1]
		fileList = glob.glob(inputPlace+'/*.tif') + glob.glob(inputPlace+'/*.tiff')
		if len(fileList) is 0:
			sys.exit("There are no files in the input directory")
	#Then, if it does, grab a list of files from the input.
		#If directory contains no TIFF files, break
		for imageFileIndex in range(len(fileList)):
			root, ext = os.path.splitext(fileList[imageFileIndex])
			name = os.path.basename(root)
			if not args.overwrite and os.path.isfile(outputPlace + '/' + name + '.hdf5'):
				print "File " + name + '.hdf5' + ' already exists. Skipping because -o flag is not set'
				del fileList[imageFileIndex]



		#For each file, check if the HDF5 file already exists in output directory.
			#(actually this functionality is contained within the fileObject interface)
			#If one is, check if -o flag is set. 
				#If o flag is set, keep it in the file list.
				#If not, then print out a message, remove it from the file list, and continue.

	#checking for valid bit depth
	#If bit depth is set, first check if it's valid.
	if args.bitdepth and (args.bitdepth not in (8,16,32,64)):
		sys.exit("Invalid number of bits set(must be 8,16,32, or 64")



	#testing block
	#For each image
	for imageFile in fileList:
		#Create an image conversion object
		imageToConvert = imageConversion()
		#Set the image's location to the proper place
		imageToConvert.setImageLocation(imageFile)
		#Get the image's details
		imageToConvert.getImageDetails()
		#Create a file object and initialize
		root, ext = os.path.splitext(fileList[imageFileIndex])
		name = os.path.basename(root)
		name = outputPlace + '/' + name 
		#fileToSave = fileObject(os.path.splitext(imageFile)[0],imageToConvert.width, imageToConvert.height)
		fileToSave = fileObject(name,imageToConvert.width, imageToConvert.height)
		fileToSave.createFile()
		fileToSave.setBitDepth(imageToConvert.bitdepth)
		if not imageToConvert.grayscaleCheck:
			print "ERROR: Image " + imageToConvert.name + " is not grayscale."
			print "Only grayscale images are supported. Please convert to grayscale and try again."
			sys.exit(1)

		#Load the image from the file
		imageToConvert.loadImageFromFile()
		#Create a group called image
		fileToSave.createImageGroup()
		#For each frame
		for frameIndex in range(0, imageToConvert.numImages):
			imageToConvert.loadImageFrameToArray()
			#Load the frame to an array

			# Do any alterations(bit casting) to that frame
				#Generate lookup tables
			#Create a new dataset
			ds = fileToSave.createNewDataset(str(frameIndex),imageToConvert.rawImage)
			#Put the frame in that dataset
			#fileToSave.saveImageToDataset(imageToConvert)
		#r

		fileToSave.imageGroup.attrs['originalName'] =  name
		print "Saved file with original name: " + name 
		#get time
		fileToSave.imageGroup.attrs['createdAt'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		print "Converted at " + strftime("%Y-%m-%d %H:%M:%S", gmtime())
		fileToSave.imageGroup.attrs['numFrames'] = imageToConvert.numImages
		print "Converted " + imageToConvert.numImages


