//Notes
//http://godoc.org/github.com/sbinet/go-hdf5/pkg/hdf5#File

package main

import "os"
import "os/exec"
import "strings"
import "flag"
import "fmt"
import "log"
import "math"

//import "github.com/sbinet/go-hdf5/pkg/hdf5"
//import "runtime" //http://stackoverflow.com/questions/1739614/what-is-the-difference-between-gos-multithreading-and-pthread-or-java-threads
//http://golang.org/doc/effective_go.html#parallel

//Sample optical parameter file
/*
pitch 150
flen 3000
mag 60
abbe false
na 1.4
medium 1.515
*/

//Optical Parameter Related Things

//OpticsRecipe is a struct designed to store optical parameters of the system.
//This can either contain the defaults put in by the constructor(copied from LFDisplay),
//information read from a file, or inputted through standard input.
type OpticsRecipe struct {
	pitch  float64
	flen   float64
	mag    float64
	abbe   bool
	na     float64
	medium float64
}

//createOpticsRecipe outputs an initialixed OpticsRecipe
//struct which contains optical parameters about the optical system.
func createOpticsRecipe() OpticsRecipe {
	var o OpticsRecipe
	o.pitch = 125.0
	o.flen = 2500.0
	o.mag = 40.0
	o.abbe = true
	o.na = 0.95
	o.medium = 1.0
	return o
}

//setOpticsRecipe is a setter routine for an optics recipe.
//This is usually used when manually inputing optical parameters
//before autorectification.
func (o *OpticsRecipe) setOpticsRecipe(pitch float64, flen float64, mag float64, abbe bool, na float64, medium float64) {
	o.pitch = pitch   //pitch
	o.flen = flen     // focal length
	o.mag = mag       // magnification
	o.abbe = abbe     //Abbe number(dispersion)/abberation? was bool in LFDisplay source
	o.na = na         //numerical aperture
	o.medium = medium //optical medium(intrinsic impedance?)
}

//calculateMaxNormalizedSlope takes an initialized optics recipe
//and returns the maximum normalized slope. This is an optical calculation
//which Google tells me nothing about.
func (o *OpticsRecipe) calculateMaxNormalizedSlope() float64 {

	imagena := o.na / o.mag
	if imagena < 1.0 {
		ulenslope := o.pitch / o.flen
		naslope := imagena / math.Pow((1.0-imagena*imagena), 0.5)
		return naslope / ulenslope
	}
	return 0.0
}

//End Optical Parameter Related Things

//Autorectification related things

//LensletSettings is a struct designed to hold the results of the autorectification.
type LensletSettings struct {
	//This stores the output of autorectify
	lensletOffset float64
	lensletHoriz  float64
	lensletVert   float64
}

//End Autorectification related things

//Misc. input things

//checkInputCorrectness is a helper routine which validates the input from 
//fmt.Scan. It returns a boolean value; true if the input was valid, and
//false if it was not.
func checkInputCorrectness(numScanned int, numExpected int, inputError error, print bool) bool {
	if inputError != nil {
		if print {
			fmt.Println("There was an error scanning the input. Please try again.")
		}
		return false
	} else if numScanned != numExpected {
		if print {
			fmt.Println("Expecting", numExpected, "input(s) and detected", numScanned)
		}
		return false
	}
	return true

}

func getInputFloatParameter(description string, printBool bool) float64 {

	var returnValue float64
	var inputError error
	var numScanned int
	fmt.Println(description)
	numScanned, inputError = fmt.Scan(&returnValue)
	if !checkInputCorrectness(numScanned, 1, inputError, printBool) {
		getInputFloatParameter(description, printBool)
	}
	return returnValue
}

//End Misc. input things

//HDF5 related things

func hdf5_getAttribute(attribute string, group string, filepath string) {
	//var getAttributeCmd exec.Cmd
	//getAttributeCmd.Path = "h5dump"
	//getAttributeCmd.Args = []string{"-a", "/" + group + "/" + attribute}
	//out, err := getAttributeCmd.Output()
	out, err := exec.Command("h5dump", "-a", "/"+group+"/"+attribute, filepath).Output()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Output is: %s\n", out)
}

//End HDF5 related things

//BUG(schmatz): What the abbe value represents is still a mystery. It isn't used so I won't worry too much
//about it.

//BUG(schmatz): Unsure about the file format of input. Do we want to read this from a text file or 
//HDF5?

func main() {
	hdf5_getAttribute("numFrames", "images", "/Users/schmatz/Epi_63xZeiss_1.4_3beads_w_lenses1.hdf5")
	//Have function have syntax ./autorectify [-h] [-d] [-m] INPUT OUTPUT
	displayFlagPtr := flag.Bool("display", false, "Prints autorectification data to screen instead of file")
	manualFlagPtr := flag.Bool("manual", false, "Takes optical parameters from user instead of defaults")
	//set default number of args expected before parsing flags
	expectedNumberOfArgs := 3 //name, input, output
	if *manualFlagPtr == true {
		expectedNumberOfArgs += 1
	}
	if *displayFlagPtr == true {
		expectedNumberOfArgs += 1
	}
	//check for correct argument length
	if len(os.Args) != expectedNumberOfArgs {
		fmt.Println("The program expected", expectedNumberOfArgs, "and detected", len(os.Args))
		fmt.Println("Please see the documentation for details.")
		os.Exit(1)
	}
	//deal with the optical parameters
	opticalParameters := createOpticsRecipe()
	var inputPitch, inputFocalLength, inputMag, inputNA, inputMedium float64
	var inputAbbe bool
	if *manualFlagPtr == true {
		inputPitch = getInputFloatParameter("Please enter the pitch:", true)
		inputFocalLength = getInputFloatParameter("Please enter the focal length:", true)
		inputMag = getInputFloatParameter("Please enter the magnification:", true)
		//getting the true/false input
		abbeInputSuccessful := false
		for abbeInputSuccessful != true {
			fmt.Println("Is the Abbe/abberation/whatever value true or false?(T/F): ")
			var abbeInputTrueFalse string
			fmt.Scanln(&abbeInputTrueFalse)
			abbeValue := strings.TrimSpace(strings.ToUpper(abbeInputTrueFalse))
			if abbeValue != "T" || abbeValue != "F" {
				fmt.Println("There was an error parsing your input. Try again.")
				continue
			} else {
				abbeInputSuccessful = true
				if abbeValue == "T" {
					inputAbbe = true
				} else {
					inputAbbe = false
				}
			}
		}
		inputNA = getInputFloatParameter("Please enter the numerical aperture:", true)
		inputMedium = getInputFloatParameter("Please enter the medium value:", true)

	} else {
		//now you have to read the input from a file(either text or HDF5?)
	}
	opticalParameters.setOpticsRecipe(inputPitch, inputFocalLength, inputMag, inputAbbe, inputNA, inputMedium)

	//now that we have the optical parameters we can start doing the fun stuff

	//end with output
	if *displayFlagPtr == true {
		//print data here
	} else {
		//output to file
	}

}
