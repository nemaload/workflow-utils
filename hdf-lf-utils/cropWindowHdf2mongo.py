#!/usr/bin/python
#
# setCropWindow.py will save crop window information to the HDF5 file.
# In order for Nemashow to use the information, we need to store the
# information in Mongo too, and that's what this tool does.
#
# Usage: ./cropWindowHdf2mongo.py filename

import os
import sys
import h5py
import hdf5lflib

import pymongo
import bson

# Open HDF5 file
filename = sys.argv[1]
try:
    h5file = h5py.File(filename, 'r')
except:
    sys.exit("Cannot open file " + filename)

# Load cropwindow
cw = h5file.require_group('cropwindow')

# Initialize Mongo
mongo = pymongo.Connection('localhost', 3002)
db = mongo.meteor
images = db.images

# Store cropwindow data in Mongo
basename = os.path.basename(filename)
images.update({'baseName': basename}, {'$set': {
    'cw_x0': int(cw.attrs['x0']),
    'cw_x1': int(cw.attrs['y0']),
    'cw_y0': int(cw.attrs['x1']),
    'cw_y1': int(cw.attrs['y1'])}})
