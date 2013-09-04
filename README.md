# Workflow Utilities
This repository stores a number of tools to help facilitate *NEMALOAD*'s workflow. See below for details of each tool.

## tiff2hdf

This tool takes 16-bit grayscale images or image stacks in the **TIFF** format and converts them into **HDF5** datasets with associated metadata. It supports a number of features, such as:

* Single image or batch processing modes

* Automatic optic metadata writing

* Image conversion safety checks

### Technical Implementation
This tool is written in Python, and leverages the ImageMagick library, written in **C**. 

### Dependencies
* **ImageMagick**
* **Python** 2.6+
* **Wand**(ctypes-based **Python ImageMagick** binding)
* **H5py Python** library

### User Guide
```
usage: tiff2hdf.py [-h] [-s] [-o] [-p PARAMETERS] [-l] input output

A tool to convert TIFF files to HDF5 datasets.

positional arguments:
  input                 The input directory to be converted. This can also be
                        a filename in the case that the -s flag is set.
  output                The directory to which the file should be output. This
                        can also be a filename in the case that the -s flag is
                        set.

optional arguments:
  -h, --help            show this help message and exit
  -s, --single          Converts a single image.
  -o, --overwrite       Overwrite all existing HDF5 files in directory.
  -p PARAMETERS, --parameters PARAMETERS
                        Specify the location of an LFDisplay-formatted optical
                        parameter text file
  -l, --lightsheet      Specifies the input images are light-sheet images

```

## autorectify-independent
This tool analyzes microlens array images and computes parameters describing the size, spacing, and location of lenses. It takes an HDF5 file as input, and then outputs another HDF5 file with autorectification metadata.

### Technical Implementation
autorectify-independent is written in Python. It was originally written to be a component of LFDisplay, but has been modified to function as a command line tool.
### Dependencies
* **numpy** library
* **OpenCV** Python bindings
* **Matplotlib** 
* **h5py** library


### User Guide
```
usage: autorectify-independent.py [-h] [-v] [-p PERCENT] [-o OUTPUT] input

A command-line tool to calculate lenslet rectifications

positional arguments:
  input                 The input file(HDF5).

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode
  -p PERCENT, --percent PERCENT
                        The percentage of images to be processed for a sample
                        in a multi image dataset
  -o OUTPUT, --output OUTPUT
                        The filename or path of the output file(must have HDF5
                        extension, not exist)

```
## autorectify-accelerated

This tool is under development, and is a concurrent Go port of autorectify. It is not functional at the moment, as priority has shifted to other tasks.

## hdf-utils

This is a set of scripts that can examine the lightsheet (and possibly lightfield?) HDF5 files
and convert them to other formats.

## pose-extract

This tool analyses a pose of the captured worm and outputs a set of control points for the virtual backbone (i.e. central axis) of the worm.
