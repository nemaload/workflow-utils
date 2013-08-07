import h5hash
import os
import fnmatch
import sys
import shutil
#REQUIRES: A directory containing at least one HDF5 file somewhere in its directory tree
#MODIFIES: Creates a cache directory at outputDirectoryName and new files as appropriate
#EFFECTS: Creates an HDF5 cache directory based on HDF5 *data* hashes


# USAGE
# ./generateHashCache.py [inputDirectoryPath] [cacheDirectoryPath]

inputDirectoryPath = os.path.normpath(sys.argv[1]) + os.sep
cacheDirectoryName = os.path.normpath(sys.argv[2]) + os.sep

#check above directories

if not os.path.isdir(inputDirectoryPath):
	print "Input path given does not specify a directory."
	raise IOError

if not os.path.isdir(cacheDirectoryName) and not os.path.exists(cacheDirectoryName):
	print "Creating cache directory..."
	os.makedirs(cacheDirectoryName)
elif not os.path.isdir(cacheDirectoryName) and os.path.exists(cacheDirectoryName):
	print "Cache path given is not a directory."
	raise IOError
else:
	print "Cache directory exists, proceeding..."


print "Searching directory tree for files..."

hdf5files = []
#matching pattern, disregard autorectify files
for root, dirs, files in os.walk(inputDirectoryPath):
	for filename in fnmatch.filter(files, "*.hdf5"):
		if "autorectify" not in filename:
			hdf5files.append(os.path.join(root,filename))

#print to user how many files were found
if len(hdf5files) == 0:
	print "No HDF5 data files were found in input directory"
	sys.exit()
else:
	print str(len(hdf5files)) + " HDF5 data files were found."

for file in hdf5files:
	print "Processing file " + file
	print "File has size " + str(os.path.getsize(file) >> 20) + "MB"
	currentFile = h5hash.H5HashFile(file)
	hashValue = currentFile.process()
	
	#Cache prefix directory stuff
	if os.path.isdir(cacheDirectoryName + hashValue[:2] + os.sep):
		#exists already, no need to make it
		print "Cache prefix directory already exists"
	elif os.path.exists(cacheDirectoryName + hashValue[:2] + os.sep):
		raise IOError
	else:
		print "Creating cache prefix directory"
		os.makedirs(cacheDirectoryName + hashValue[:2] + os.sep)

	#Cache file stuff
	#overwrite by default, due to changing versions of attributes
	print "Copying file to cache directory..."
	shutil.copy(file, cacheDirectoryName + hashValue[:2] + os.sep + hashValue[2:])
	print "Finished processing " + file



