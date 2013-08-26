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

def processFrameUV(i, node, outputBase, ofs_U, ofs_V, ar, imgfmt):
    imgdata = node.read()
    # scipy.misc.imsave('rawimage.png', imgdata)

    gridsize = (int(imgdata.shape[0] / ar._v_attrs['down_dy']), int(imgdata.shape[1] / ar._v_attrs['right_dx']))
    global gridsize_last
    gridsize_last = gridsize
    corner = hdf5lflib.lenslets_offset2corner(ar)

    # We also rotate the image by 90\deg during the processing to maintain
    # compatibility with other parts of our toolchain.

    uvframe = numpy.zeros(shape=(gridsize[1], gridsize[0]), dtype='short')

    (right_dx, right_dy) = ar._v_attrs['right_dx'], ar._v_attrs['right_dy']
    (down_dx, down_dy) = ar._v_attrs['down_dx'], ar._v_attrs['down_dy']

    for y in range(int(gridsize[0])):
        for x in range(int(gridsize[1])):
            cx = corner[1] + x * right_dx + y * down_dx + ofs_U
            cy = corner[0] + x * right_dy + y * down_dy + ofs_V
            try:
                uvframe[gridsize[1]-1 - x][y] = imgdata[int(round(cy))][int(round(cx))]
                #print cx, cy, gridsize[1]-1 - x, y, int(uvframe[gridsize[1]-1 - x][y])
            except IndexError:
                #print cx, cy, gridsize[1]-1 - x, y, '---'
                pass

    if imgfmt == 'png':
        scipy.misc.imsave(outputBase + '-' + str(i) + '.png', uvframe)
    else:
        f = open(outputBase + '-' + str(i) + '.raw', 'wb')
        uvframe.tofile(f)
        f.close()

def processFileUV(filename, outputDirectoryPath, ofs_U, ofs_V, imgfmt):
    h5file = tables.open_file(filename, mode = "r")
    ar = h5file.get_node('/', '/autorectification')
    outputBase = outputDirectoryPath + os.path.splitext(os.path.basename(filename))[0]
    for (i, node) in sorted(h5file.get_node('/', '/images')._v_children.items(), key = lambda j: int(j[0])):
        print outputBase, i
        processFrameUV(i, node, outputBase, ofs_U, ofs_V, ar, imgfmt)
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