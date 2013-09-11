#!/usr/bin/python
#
# Usage: hdf5display.py FILENAME OBJPATH...
#
# Example: hdf5display.py punc31_gCAMP5_td_video32_global_gfpfilter.hdf5 images/190
#
# Display a particular frame with the crop window overlaid.
# Note that the data is not rotated by 90 degrees like it is
# during later processing. Also, the image is rescaled to high
# brightness (by setting absolute white level as fairly low
# value, adjust that below).

import sys

import tables

import matplotlib.pyplot as plt
import matplotlib.patches


WHITE_LEVEL = 4096
GAIN_LEVEL = 8.

filename = sys.argv[1]

for objpath in sys.argv[2:]:
    h5file = tables.open_file(filename, mode = "r")
    try:
        cw = h5file.get_node('/', '/cropwindow')
    except tables.NoSuchNodeError:
        cw = None

    node = h5file.get_node('/', objpath)
    data = node.read()
    data *= GAIN_LEVEL

    f, axes = plt.subplots(ncols = 2)
    imgplot = axes[0].imshow(data, vmin = 0, vmax = WHITE_LEVEL, cmap = plt.cm.gray)

    if cw is not None:
        (x0, y0, x1, y1) = (cw._v_attrs[j] for j in ('x0', 'y0', 'x1', 'y1'))
        print 'data shape', data.shape, 'crop window', x0, y0, x1, y1
        rect = matplotlib.patches.Rectangle((x0, y0),
                height = y1 - y0, width = x1 - x0,
                edgecolor='green', fill=0)
        axes[0].add_patch(rect)

        imgplot = axes[1].imshow(data[y0:y1 , x0:x1], vmin = 0, vmax = WHITE_LEVEL, cmap = plt.cm.gray)

plt.show()
