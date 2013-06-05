package main

import "fmt"

import "github.com/sbinet/go-hdf5/pkg/hdf5"
import "os"
import "flag"

func main() {

	displayFlagPtr := flag.Bool("d", false, "Prints autorectification data to screen instead of file")
	manualFlagPtr := flag.Bool("m", false, "Takes optical parameters from user instead of defaults")
	overwriteFlagPtr := flag.Bool("o", false, "Overwrites existing output file")
	flag.Parse()

	//check for correct argument length
	if flag.NArg() != 2 {
		fmt.Println("Expecting two non-flag arguments.")
		fmt.Println("Please see the documentation for details.")
		os.Exit(1)
	}
	inputFilePath := flag.Arg(0)
	outputFilePath := flag.Arg(1)

	//file handling
	//check if input file exists and is correct format

	if _, err := os.Stat(inputFilePath); err != nil {
		fmt.Println("File does not exist at location", inputFilePath)
		os.Exit(1)
	}
	if !hdf5.IsHdf5(inputFilePath) {
		fmt.Println("File is not HDF5(may be corrupted)")
	}
	//input file checks done

	if _, err := os.Stat(outputFilePath); err == nil && !*overwriteFlagPtr {
		fmt.Println("Output file exists and overwrite flag is not set.")
		os.Exit(1)
	}
	//output file checks are done
	//open file
	if inputFile, err := hdf5.OpenFile(inputFile, F_ACC_RDONLY); err !=nil {
		fmt.Println("There was an error opening the input file. Exiting")
		os.Exit(1)
	}

	if imagesGroup, err := hdf5.OpenGroup("images",0)



	if *manualFlagPtr {
		//get optical parameters from input
	} else {
		//get optical parameters from file attribute
	}

	if *displayFlagPtr {
		fmt.Println("Display flag was used")
	}

}
