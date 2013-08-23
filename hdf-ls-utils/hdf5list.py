#!/usr/bin/python
#
# Usage: hdf5list.py FILENAME
#
# Example: ./hdf5list.py 16_4-15_27.hdf5

import sys

import tables

import numpy
import scipy.misc
import matplotlib.pyplot as plt

import json


filename = sys.argv[1]

h5file = tables.open_file(filename, mode = "r")

ls = {}

channel_list = [i for (i, node) in h5file.get_node('/', '/images')._v_children.items()]
for ch in channel_list:
    group_list = [i for (i, node) in h5file.get_node('/', '/images/' + ch)._v_children.items()]
    group_list = map(int, group_list)
    group_list.sort()
    ls[ch] = group_list

print json.dumps(ls)
