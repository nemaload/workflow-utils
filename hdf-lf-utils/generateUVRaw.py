#!/usr/bin/python
#
# Generate a raw image with the sample view from a certain U,V viewpoint
# from a lightfield image
#
# Usage: ./generateUVRaw.py inputFile outputDir ofs_U ofs_V ["raw"|"png"]
#
# FIXME: Generates a PNG image now

import math
import os
import sys

import numpy
import scipy.misc
import tables
import hdf5lflib

gridsize_last = []

def processFrameUV(i, node, outputBase, ofs_U, ofs_V, ar, cw, imgfmt):
    uvframe = hdf5lflib.compute_uvframe(node, ar, cw, ofs_U, ofs_V)

    global gridsize_last
    gridsize_last = uvframe.shape

    if imgfmt == 'png':
        scipy.misc.imsave(outputBase + '-' + str(i) + '.png', uvframe)
    else:
        f = open(outputBase + '-' + str(i) + '.raw', 'wb')
        uvframe.tofile(f)
        f.close()

def processFileUV(filename, outputDirectoryPath, ofs_U, ofs_V, imgfmt):
    h5file = tables.open_file(filename, mode = "r")
    ar = h5file.get_node('/', '/autorectification')
    try:
        cw = h5file.get_node('/', '/cropwindow')
    except tables.NoSuchNodeError:
        cw = None
    outputBase = outputDirectoryPath + os.path.splitext(os.path.basename(filename))[0]
    for (i, node) in sorted(h5file.get_node('/', '/images')._v_children.items(), key = lambda j: int(j[0])):
        print outputBase, i
        processFrameUV(i, node, outputBase, ofs_U, ofs_V, ar, cw, imgfmt)
    return True

if __name__ == '__main__':
    filename = sys.argv[1]
    outputDirectoryPath = os.path.normpath(sys.argv[2]) + os.sep
    ofs_U = sys.argv[3]
    ofs_V = sys.argv[4]
    if sys.argv[5]:
        imgfmt = sys.argv[5]
    else:
        imgfmt = 'raw'
    if not processFileUV(filename, outputDirectoryPath, float(ofs_U), float(ofs_V), imgfmt):
        sys.exit(1)
    print 'output dimensions', gridsize_last
