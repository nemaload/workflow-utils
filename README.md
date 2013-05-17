# Workflow Utilities
This repository stores a number of tools to help facilitate *NEMALOAD*'s workflow. See below for details of each tool.

## tiff2hdf

This tool takes images or image stacks in the **TIFF** format (normally 16-bit grayscale) and converts them into **HDF5** datasets. It supports a number of features, such as:
* Tolerance for multiple bit depths and color modes

* **GPU**-accelerated **RGB** to grayscale conversion

* Customizable **HDF** bit depth and data representation

* Single image or batch processing modes

* Image conversion safety checks

### Technical Implementation
This tool is written in **C** and **Python**, and leverages the ImageMagick library, written in **C**. It also utilizes the **OpenCL** libraries to accelerate **RGB** to grayscale conversion.

### Dependencies
* **ImageMagick**
* **Python** 2.6+
* **Wand**(ctypes-based **Python ImageMagick** binding)
* **H5py Python** library
* **OpenCL** libraries(if **OpenCL** flag is used)

### User Guide
#### Name
*tiff2hdf* - Converts tiff files to HDF5 datasets.
#### Synopsis
`tiff2hdf \[OPTIONS\] \[INPUT FILE(S)…\] \[OUTPUT FILE(S)…\]`
`tiff2hdf \[LONG-OPTION\]`
#### Options
**-a** 
Convert all TIFFs in current directory to HDF5 datasets, output in current directory.
**-o** 
Overwrite all existing HDF5 files in directory.
**-r**
Convert TIFFs to raw images, not HDF5 datasets.
**-c**
Accelerate RGB to grayscale conversionsion with OpenCL(requires OpenCL dependencies)
**-b N**
Convert all TIFFsFF files to HDF5 datasets with _N_ bit integers, where _N_ is a valid number of bits (see HDF5 documentation.) The default bit depth is 16 bits.
**--help** 
Shows documentationcumentation.

## autorectify-accelerated
This tool is an **OpenCL C** port of *pasky*'s autorectify code originally for *LFDisplay*. It processes **HDF5** images and **TIFF** stacks, and outputs rectification data. Some features of this program include:

* **OpenCL** acceleration of autorectification

 * **HDF5** metadata support

* Support for **HDF5** videos.

### Technical Implementation
autorectify-accelerated is written in **OpenCL C**, and is optmized for the **GPU** architecture. 
### Dependencies
* **HDF5** header files
* **OpenCL** libraries
### User Guide
#### Name
*autorectify-accelerated* - generates lenslet rectification data.
#### Synopsis
`autorectify-accelerated \[OPTIONS\] \[INPUT FILE(S)…\] \[OUTPUT FILE(S)…\]`
`autorectify-accelerated \[LONG-OPTION\]`
#### Options
**-t**
Output autorectification data to text files instead of **HDF5** metadata.






