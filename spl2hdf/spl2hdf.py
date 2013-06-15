#!/usr/bin/env python

# spl2hdf.py converts SPL files to HDF5 datasets.
# Copyright (C) 2013 NEMALOAD

# Authored by Michael Schmatz

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


import sys, argparse, os, numpy, h5py, glob, Image, shutil, json
import datetime
import time

from wand.image import Image as wandImage
from subprocess import call

#for ISO 8601 timezone calculation without external libraries
class LocalTZ(datetime.tzinfo):
    _unixEpochOrdinal = datetime.datetime.utcfromtimestamp(0).toordinal()

    def dst(self, dt):
        return datetime.timedelta(0)

    def utcoffset(self, dt):
        t = (dt.toordinal() - self._unixEpochOrdinal)*86400 + dt.hour*3600 + dt.minute*60 + dt.second + time.timezone
        utc = datetime.datetime(*time.gmtime(t)[:6])
        local = datetime.datetime(*time.localtime(t)[:6])
        return local - utc


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

		self.rawImage = numpy.array(self.img.getdata(), dtype=numpy.dtype('uint16')).reshape(self.img.size[::-1])
		#this is the work around to the shitty PIL library

		try:
			self.img.seek(self.currentImage)
			self.currentImage += 1
			#break
		except EOFError:
			print "Experienced an EOF error, indicates irregular TIFF frame from SPL image..."
			return -1
		return 0


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
		prog='spl2hdf.py',
		description="""A tool to convert SPL files to HDF5 datasets. 
		Note: The SPL data format is proprietary, so this program depends on an external jar file.""")
	parser.add_argument("jar", type=str,
		help="The path of the SPL conversion jar.")
	parser.add_argument("input", type=str,
		help="""The input directory to be converted. This can also
		be a filename in the case that the -s flag is set.""")
	parser.add_argument("output", type=str,
		help="""NOTE: This is non-functional due to a bug in the python STL. Files are output in directory script is run from.""")
	parser.add_argument(
		'-s',
		'--single',
		help="""Converts a single image.""",
		action="store_true")
	parser.add_argument('-o',
		'--overwrite',
		help="""Overwrite all existing HDF5 files in directory.""",
		action="store_true")




	args = parser.parse_args()

	inputPlace = args.input
	outputPlace = args.output
	jarPath = args.jar


	imageType = "LS"
	

	#checking if -s flag is properly used
	if args.single:
		#first, check that input file exists.
		if not os.path.isfile(inputPlace):
			sys.exit("Input file does not exist.")
		#second, check that output file does NOT exist, and outputPlace is not a directory.
		if os.path.isfile(outputPlace) and not args.overwrite:
			sys.exit("Output file exists. To overwrite, use the -o flag.")
		fileList = [inputPlace]
	if not args.single:
		if not (os.path.isdir(inputPlace) and os.path.isdir(outputPlace)):
			sys.exit("Both input and output directories must exist.")
	#First, check if the input directory and output directory exist.
		print "Finding SPL files..."
		#first format the string to remove a trailing slash
		if inputPlace[-1] is '/':
			inputPlace = inputPlace[:-1]
		if outputPlace[-1] is '/':
			outputPlace = outputPlace[:-1]
		fileList = glob.glob(inputPlace+'/*.spl') 
		if len(fileList) is 0:
			sys.exit("There are no input files in the input directory")
	#Then, if it does, grab a list of files from the input.
		#If directory contains no TIFF files, break
		imageFileIndex = 0
		while imageFileIndex < len(fileList):
			root, ext = os.path.splitext(fileList[imageFileIndex])
			name = os.path.basename(root)
			if not args.overwrite and os.path.isfile(outputPlace + '/' + name + '.hdf5'):
				print "File " + name + '.hdf5' + ' already exists. Skipping because -o flag is not set'
				del fileList[imageFileIndex]
				continue
			imageFileIndex += 1




	#work SPL magic here
	#check jar file exists here:
	frameTotal = 0
	#create temp dir
	try:
		os.mkdir("./spltmp") #make temporary directory to generate tiffs in
	except:
		sys.exit("Error creating spltmp directory. Does it already exist? Do you have the correct permissions?")

	for splFileIndex in range(len(fileList)): #this is the conversion loop
		shutil.copy2(fileList[splFileIndex], "./spltmp") #copy SPL file into directory
		#make parameters customizable
		fileBaseName = os.path.basename(fileList[splFileIndex])
		print "Converting file " + fileBaseName
		fileCallString = "scala -cp " + args.jar + " ichi.apps.SplToTiff 4000 59 " + "./spltmp/" + fileBaseName
		print "Calling: " + fileCallString
		retcode = call(fileCallString, shell=True) #FILE BASE
		if retcode is not 0:
			print "There was a problem converting " + fileBaseName + ". Skipping..."
			continue
		root, ext = os.path.splitext(fileBaseName)

		#now that the files are in tiff format, find json files and use them to parse the data
		jsonFileList = glob.glob("./spltmp/*.json")
		width = 128
		height = 128
		filename = root
		fileToSave = fileObject(filename, width, height)
		fileToSave.createFile()
		fileToSave.createImageGroup()
		print "Converting SPL chunks..."
		for jsonFile in jsonFileList:
			print "Extracting data using " + jsonFile
			#create HDF5 file here
			root, ext = os.path.splitext(jsonFile)
			root, ext = os.path.splitext(root)
			#ext now contains channel 
			channelGroup = fileToSave.imageGroup.create_group(ext)
			
			json_data = open(jsonFile)
			data = json.load(json_data)
			for chunkIndex in range(len(data)):
				chunkGroup = channelGroup.create_group(str(chunkIndex))
				chunkGroup.attrs['ls_chunk_filename'] = str(data[chunkIndex]['filename'])
				imageToConvert = imageConversion()
				imageToConvert.setImageLocation("./spltmp/" + data[chunkIndex]['filename'])
				imageToConvert.loadImageFromFile()
				for frameIndex in range(len(data[chunkIndex]['data'])):
					convertRet = imageToConvert.loadImageFrameToArray()
					if convertRet is not 0:
						print "Frame in question is: " + str(frameIndex) + " in chunk " + str(chunkIndex)
					ds = chunkGroup.create_dataset(str(frameIndex), data=imageToConvert.rawImage, dtype='uint16')
					frameDict = data[chunkIndex]['data'][frameIndex]
					ds.attrs['ls_channel'] = frameDict['channel']
					ds.attrs['ls_offset'] = frameDict['offset']
					ds.attrs['ls_time'] =  frameDict['time']
					ds.attrs['ls_ver']  = frameDict['ver']
					ds.attrs['ls_n'] = frameDict['n']
					ds.attrs['ls_z_request'] = frameDict['z'][0]
					ds.attrs['ls_z_measured'] = frameDict['z'][1]
					frameTotal += 1

		fileToSave.imageGroup.attrs['originalName'] =  fileBaseName
		root, ext = os.path.splitext(fileBaseName)
		print "Saved file " + root + '.hdf5'
		#get time
		fileToSave.imageGroup.attrs['createdAt'] = str(datetime.datetime.now(LocalTZ()).isoformat('T')) 
		fileToSave.imageGroup.attrs['numFrames'] = frameTotal
		fileToSave.imageGroup.attrs['opticalSystem'] = imageType
		#moveCall = "sudo mv ./"+ root + ".hdf5 \"" + outputPlace + "\""
		#shutil.move("./" + root + ".hdf5", outputPlace)
		print "Converted file " + root + ".hdf5"
		call("sudo rm ./spltmp/*.tiff", shell=True)
		call("sudo rm ./spltmp/*.json", shell=True)
		call("sudo rm ./spltmp/*.spl", shell=True)
		print "Removed conversion byproducts"


	#copy HDF5 back to input directory and delete temporary folder

		
	call("sudo rm -rf ./spltmp")









