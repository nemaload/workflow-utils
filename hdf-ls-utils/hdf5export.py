#!/usr/bin/python
#
# Usage: hdf5export.py FILENAME OBJPATH
#
# Export a set of frames from HDF5 file in a way suitable for WebGL
# visualization. The output is a file `rawls.png` with a tiling
# of frames stored in the subgroup at OBJPATH (i.e., frames of the
# same object at different z). At the same time, JSON with some
# metadata is printed on stdout.
#
# Example: ./hdf5export.py 16_4-15_27.hdf5 /images/.ch0/0 >rawls.json

import sys

import tables

import numpy
import scipy.misc
import matplotlib.pyplot as plt

import json


filename = sys.argv[1]
objpath = sys.argv[2]

h5file = tables.open_file(filename, mode = "r")

node0 = h5file.get_node('/', objpath + '/0')

imgdata = None
metadata = {'size_x': int(node0.shape[0]), 'size_y': int(node0.shape[1]), 'framedata': []}

for (i, node) in sorted(h5file.get_node('/', objpath)._v_children.items(), key = lambda i: i[1].attrs['ls_z_measured']):
    if imgdata is None:
        imgdata = node.read()
    else:
        imgdata = numpy.vstack((imgdata, node.read()))
    metadata['framedata'].append({'t': int(node.attrs['ls_time']), 'n': int(node.attrs['ls_n']), 'z_r': float(node.attrs['ls_z_request']), 'z': float(node.attrs['ls_z_measured'])})

scipy.misc.imsave('rawls.png', imgdata)
print json.dumps(metadata)
