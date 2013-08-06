#!/usr/bin/python

import os
import sys
import fnmatch
import generateRawAndJSON

# USAGE
# ./massGenerateRawAndJSON.py [inputDirectoryName] [outputDirectoryName]


directoryPath = os.path.normpath(
    sys.argv[1]) + os.sep  # needed to standardize file path
print "Generating JSON for HDF5 files in directory " + directoryPath
outputDirectoryPath = os.path.normpath(sys.argv[2]) + os.sep

hdf5files = []
for file in os.listdir(directoryPath):
    if fnmatch.fnmatch(file, '*.hdf5'):  # get all HDF5 files in directory
        if "autorectify" not in file:  # but not autorectification files
            hdf5files.append(file)

print "Found " + str(len(hdf5files)) + " HDF5 files. Processing..."

for file in hdf5files:
    generateRawAndJSON.processFile(directoryPath + file, outputDirectoryPath)

print "Program finished execution"
