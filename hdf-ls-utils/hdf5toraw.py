#!/usr/bin/python
#
# Generate a raw image for each frame in inputFile, suitable e.g. for
# consumption by the pose extractor.
#
# Both channels are superimposed.
#
# Usage: hdf5toraw.py inputFile outputDir ["raw"|"png"]

import os
import sys

import numpy
import scipy.misc
import tables


framesize_last = []

def processFrame(i, nodes, outputBase, imgfmt):
    # TODO: We should choose a fixed Z slice step and interpolate to this step;
    # for now, we just plaster the slices one after another directly.

    imgdata = None

    slices = [
        sorted(nodes[0]._v_children.items(), key = lambda i: i[1].attrs['ls_z_measured']),
        sorted(nodes[1]._v_children.items(), key = lambda i: i[1].attrs['ls_z_measured'])
    ]

    for ((j, slice0), (jj, slice1)) in zip(slices[0], slices[1]):
        # Superimpose slices
        sliceSum = slice0.read()/2 + slice1.read()/2

        if imgdata is None:
            imgdata = sliceSum
        else:
            imgdata = numpy.vstack((imgdata, sliceSum))

    global framesize_last
    framesize_last = (len(slices[0]), imgdata.shape[0] / len(slices[0]), imgdata.shape[1])
    print framesize_last

    if imgfmt == 'png':
        scipy.misc.imsave(outputBase + '-' + str(i) + '.png', imgdata)
    else:
        f = open(outputBase + '-' + str(i) + '.raw', 'wb')
        imgdata.tofile(f)
        f.close()

def processFile(filename, outputDirectoryPath, imgfmt):
    h5file = tables.open_file(filename, mode = "r")
    outputBase = outputDirectoryPath + os.path.splitext(os.path.basename(filename))[0]
    nodes = [
        sorted(h5file.get_node('/', '/images/.ch0')._v_children.items(), key = lambda j: int(j[0])),
        sorted(h5file.get_node('/', '/images/.ch1')._v_children.items(), key = lambda j: int(j[0]))
    ]
    for ((i, node0), (ii, node1)) in zip(nodes[0], nodes[1]):
        print outputBase, i
        processFrame(i, [node0, node1], outputBase, imgfmt)
    return True

if __name__ == '__main__':
    filename = sys.argv[1]
    outputDirectoryPath = os.path.normpath(sys.argv[2]) + os.sep
    if sys.argv[3]:
        imgfmt = sys.argv[3]
    else:
        imgfmt = 'raw'
    if not processFile(filename, outputDirectoryPath, imgfmt):
        sys.exit(1)
    print 'output dimensions', framesize_last
