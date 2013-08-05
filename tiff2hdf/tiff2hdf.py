#!/usr/bin/env python

# tiff2hdf converts TIFF images and image stacks to HDF5 datasets.
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


import sys, argparse, os, numpy, h5py, glob, Image
import datetime
import time

from wand.image import Image as wandImage

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
            #   iterations it got through before that
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
        #   already have been called.
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
            print "Reached end of stacked image..."


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
            dtype=dt,
            compression='gzip')
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
        prog='tiff2hdf.py',
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
    parser.add_argument('-o',
        '--overwrite',
        help="""Overwrite all existing HDF5 files in directory.""",
        action="store_true")
    parser.add_argument('-p',
        '--parameters',
        help="Specify the location of an LFDisplay-formatted optical parameter text file",
        nargs=1)
    parser.add_argument(
        '-u',
        '--maxu',
        help="Maximum tangens of the lens viewing angle",
        nargs=1)



    args = parser.parse_args()

    inputPlace = args.input
    outputPlace = args.output

    imageType = "LF"

    if args.parameters:
        #parses the optical parameters
        opticalProperties = args.parameters[0]

        parameterFile = open(opticalProperties)
        for line in parameterFile:
            if line[0:5] == "pitch":
                op_pitch = float(line[5:])
            if line[0:4] == "flen":
                op_flen = float(line[4:])
            if line[0:3] == "mag":
                op_mag = float(line[3:])
            if line[0:4] == "abbe":
                continue
            if line[0:2] == "na":
                op_na = float(line[2:])
            if line[0:6] == "medium":
                op_medium = float(line[6:])
    else:
        op_pitch = op_flen = op_mag = op_na = op_medium = 0



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
        imageFileIndex = 0
        while imageFileIndex < len(fileList):
            root, ext = os.path.splitext(fileList[imageFileIndex])
            name = os.path.basename(root)
            if not args.overwrite and os.path.isfile(outputPlace + '/' + name + '.hdf5'):
                print "File " + name + '.hdf5' + ' already exists. Skipping because -o flag is not set'
                del fileList[imageFileIndex]
                continue
            imageFileIndex += 1


        #For each file, check if the HDF5 file already exists in output directory.
            #(actually this functionality is contained within the fileObject interface)
            #If one is, check if -o flag is set.
                #If o flag is set, keep it in the file list.
                #If not, then print out a message, remove it from the file list, and continue.



    #testing block
    #For each image
    for imageFileIndex in range(len(fileList)):
        #Create an image conversion object
        imageToConvert = imageConversion()
        #Set the image's location to the proper place
        imageToConvert.setImageLocation(fileList[imageFileIndex])
        #Get the image's details
        imageToConvert.getImageDetails()
        #Create a file object and initialize

        if not args.single:
            root, ext = os.path.splitext(fileList[imageFileIndex])
            name = os.path.basename(root)
            name = outputPlace + '/' + name
        else:
            root, ext = os.path.splitext(outputPlace)
            name = root
        #fileToSave = fileObject(os.path.splitext(imageFile)[0],imageToConvert.width, imageToConvert.height)
        fileToSave = fileObject(name,imageToConvert.width, imageToConvert.height)
        print "Trying to open " + fileToSave.filename
        fileToSave.createFile()

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
            print "The shape of this frame is " + str(imageToConvert.rawImage.shape)
            ds = fileToSave.createNewDataset(str(frameIndex),imageToConvert.rawImage)
            #Put the frame in that dataset
            #fileToSave.saveImageToDataset(imageToConvert)

        fileToSave.imageGroup.attrs['originalName'] =  os.path.basename(name) + ext

        print "Saved file with original name: " + os.path.basename(name)
        #get time
        fileToSave.imageGroup.attrs['createdAt'] = str(datetime.datetime.now(LocalTZ()).isoformat('T'))
        fileToSave.imageGroup.attrs['numFrames'] = imageToConvert.numImages
        fileToSave.imageGroup.attrs['opticalSystem'] = imageType
        if args.maxu[0] is not None:
            fileToSave.imageGroup.attrs['op_maxu'] = float(args.maxu[0])
        fileToSave.imageGroup.attrs['op_pitch'] = op_pitch
        fileToSave.imageGroup.attrs['op_flen'] = op_flen
        fileToSave.imageGroup.attrs['op_mag'] = op_mag
        fileToSave.imageGroup.attrs['op_na'] = op_na
        fileToSave.imageGroup.attrs['op_medium'] = op_medium
