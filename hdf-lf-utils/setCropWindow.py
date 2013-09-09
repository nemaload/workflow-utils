#!/usr/bin/env python
#
# Store a crop window setup with given dimensions in HDF5 file.
#
# Usage: setCropWindow.py HDF5FILE X0 Y0 X1 Y1
#
# Caution: The images you usually see have the X and Y coordinates
# swapped compared to what's stored in the dataset! To determine
# this tool's parameters from values measured on the rotated version
# (e.g. as shown as nemashow), pass them as:
#
#   setCropWindow.py HDF5FILE $((2160-Y1)) X0  $((2560-Y0)) X1
#
# (Assuming pre-rotation dataset dimensions 2160x2560.)
#
# You can verify the crop window visually with the hdf5display.py tool
# (which shows the unrotated image).

import h5py
import sys

if __name__ == '__main__':
    h5file = h5py.File(sys.argv[1], 'r+')
    cropwindowGroup = h5file.require_group("cropwindow")
    cropwindowGroup.attrs['x0'] = int(sys.argv[2])
    cropwindowGroup.attrs['y0'] = int(sys.argv[3])
    cropwindowGroup.attrs['x1'] = int(sys.argv[4])
    cropwindowGroup.attrs['y1'] = int(sys.argv[5])
    h5file.close()
