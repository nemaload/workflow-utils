#!/usr/bin/python
#
# Usage: hdf5display.py FILENAME OBJPATH...
#
# Example: hdf5display.py 16_4-15_27.hdf5 images/.ch0/0/0 images/.ch1/0/0

import sys

import tables

import matplotlib.pyplot as plt


filename = sys.argv[1]

for objpath in sys.argv[2:]:
    h5file = tables.open_file(filename, mode = "r")
    node = h5file.get_node('/', objpath)

    f = plt.figure(objpath + " t=" + str(node.attrs['ls_time']) + " n=" + str(node.attrs['ls_n']) + " z=" + str(node.attrs['ls_z_measured']))
    imgplot = plt.imshow(node.read(), cmap = plt.cm.gray)

plt.show()
