#!/usr/bin/python
#
# autorectify-independent.py -m will save autorectification data
# to the Mongo database - this is how the autorectification of most
# currently used datasets has been generated. This will back-annotate
# the HDF5 file with the autorectification data TODO: and maxu information
# (in case that has been modified in the database).
#
# Usage: ./autorectifyMongo2hdf.py filename
#
# Note that this will add an 'autorectification' group to the main
# HDF5 file instead of using the convention of a separate HDF5 file.

import os
import sys
import h5py
import hdf5lflib

import pymongo
import bson

# Open HDF5 file
filename = sys.argv[1]
try:
    h5file = h5py.File(filename, 'r+')
except:
    sys.exit("Cannot open file " + filename)

# Load image record from Mongo
mongo = pymongo.Connection('localhost', 3002)
db = mongo.meteor
images = db.images
basename = os.path.basename(filename)
imageInfo = images.find({'baseName': basename})[0]

# Store autorectification data in HDF5 file
autorectificationGroup = h5file.require_group("autorectification")
autorectificationGroup.attrs['x_offset'] = imageInfo['op_x_offset']
autorectificationGroup.attrs['y_offset'] = imageInfo['op_y_offset']
autorectificationGroup.attrs['right_dx'] = imageInfo['op_right_dx']
autorectificationGroup.attrs['right_dy'] = imageInfo['op_right_dy']
autorectificationGroup.attrs['down_dx'] = imageInfo['op_down_dx']
autorectificationGroup.attrs['down_dy'] = imageInfo['op_down_dy']

# TODO: also update maxu if set in database
