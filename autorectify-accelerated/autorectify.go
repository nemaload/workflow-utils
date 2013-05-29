//Notes
//http://godoc.org/github.com/sbinet/go-hdf5/pkg/hdf5#File

package main

import "os"
import "os/exec"
import "strings"
import "flag"
import "fmt"
import "string"
import "log"
import "math"
import "time"
import "math/rand"
import "sort"

import "github.com/sbinet/go-hdf5/pkg/hdf5"

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

const MAX_RADIUS = 30

//float32 will be used for everything, everything will be typecast into this representation using float32()
type LensletSettings struct {
	//This stores the output of autorectify
	lensletOffset [2]float32
	lensletHoriz  [2]float32
	lensletVert   [2]float32
}

type RectifyParams struct {
	framesize [2]uint16
	minsize   uint16
	maxsize   uint16
	size      [2]float32
	offset    [2]float32
	tau       float32
}

//Coordinates are represented with uint16, as well as sizes, etc
//Very seldom does a coordinate function return a float to be cast into a uint16

func (r *RectifyParams) SetDefaults(x uint16, y uint16) {
	r.framesize[0] = x
	r.framesize[1] = y
	r.minsize = 12
	r.maxsize = MAX_RADIUS
	//thank you go's automatic initialization to 0
}

func (r *RectifyParams) randomize() {
	random := rand.New(rand.NewSource(time.Now()))
	//might need typecasting
	r.size[0] = r.minsize + random.Float32()*(r.maxsize-r.minsize)
	r.size[1] = r.size[0] * (0.8 + random.Float32()*0.4)
	// guessing that in the original this is scalar multiplication
	r.offset[0] = random.Float32()*r.size[0] - r.size[0]/2
	r.offset[1] = random.Float32()*r.size[1] - r.size[1]/2
	r.tau = random.float32 * math.Pi / 8
}

func (r *RectifyParams) gridsize() [2]uint16 {
	var returnArray [2]uint16
	returnArray[0] = uint16(r.framesize[0] / r.size[0])
	returnArray[1] = uint16(r.framesize[1] / r.size[1])
	return returnArray
}

func (r *RectifyParams) xytilted_tau(ic [2]uint16, tau float32) [2]uint16 {
	var returnArray [2]uint16
	returnArray[0] = uint16(ic[0]*math.Cos(tau) - ic[1]*math.Sin(tau))
	returnArray[1] = uint16(ic[1]*math.Sin(tau) + ic[1]*math.Cos(tau))
	return returnArray
}

func (r *RectifyParams) xytilted(ic [2]uint16) [2]uint16 {
	return r.xytilted_tau(ic, r.tau)
}

func (r *RectifyParams) xylens(gc [2]uint16) [2]uint16 {
	var returnArray, center_pos, straight_pos, tilted_pos [2]uint16
	center_pos[0] = r.framesize[0]/2 + r.offset[0]
	center_pos[1] = r.framesize[1]/2 + r.offset[1]
	straight_pos[0] = r.size[0] * gc[0]
	straight_pos[1] = r.size[1] * gc[1]
	tilted_pos = r.xytilted(straight_pos)
	returnArray[0] = center_pos[0] + tilted_pos[0]
	returnArray[1] = center_pos[1] + center_pos[1]
	return returnArray
}

func (r *RectifyParams) lensxy(ic [2]uint16) [2]uint16 {
	var returnArray, center_pos, straight_pos, tilted_pos [2]uint16
	center_pos[0] = r.framesize[0]/2 + r.offset[0]
	center_pos[1] = r.framesize[1]/2 + r.offset[1]
	tilted_pos[0] = ic[0] - center_pos[0]
	tilted_pos[1] = ic[1] - center_pos[1]
	//WARNING THIS MAY CAUSE A LOT OF PROBLEMS(change return types of some coordinate functions to float32 instead)
	straight_pos[0] = r.xytilted_tau(tilted_pos, []uint16{-1 * r.tau[0], -1 * r.tau[1]}) //lol is this legal
	returnArray[0] = uint16(straight_pos[0] / r.size[0])
	returnArray[1] = uint16(straight_pos[1] / r.size[1])
	return returnArray
}

func (r *RectifyParams) normalize() {
	random := rand.New(rand.NewSource(time.Now()))

	//not entirely sure why this is necessary, length between elements should never be negative
	r.size[0] = float32(math.Abs(r.size[0]))
	r.size[1] = float32(math.Abs(r.size[1]))

	//might have to do some manual typecasting here for r.maxsize and r.minsize
	if r.size[0] > r.maxsize {
		r.size[0] = r.minsize + random.Float32()*(r.maxsize-r.minsize)
	} else if r.size[0] < r.minsize {
		r.size = r.minsize
	}

	if r.size[1] > r.maxsize {
		r.size[1] = r.size[0] * (0.8 + random.Float32()*0.4)
	} else if r.size[1] > r.minsize {
		r.size[1] = r.minsize
	}

	r.tau[0] = (r.tau[0]+math.Pi/16)%(math.Pi/8) - math.Pi/16
	r.tau[1] = (r.tau[1]+math.Pi/16)%(math.Pi/8) - math.Pi/16
}

func (r *RectifyParams) to_steps() LensletSettings {
	var returnValues LensletSettings

	returnValues.lensletOffset[0] = r.framesize[0]/2 + r.offset[0]
	returnValues.lensletOffset[1] = r.framesize[1]/2 + r.offset[1]

	returnValues.lensletHoriz = r.xytilted([2]uint16{r.size[0], 0})
	returnValues.lensletVert = r.xytilted([2]uint16{0, r.size[1]})
	return returnValues
}

func (r *RectifyParams) from_steps(l LensletSettings) {
	tauH := math.Atan2(l.lensletHoriz[1], l.lensletHoriz[0])
	tauV := math.Atan2(-1*l.lensletVert[0], l.lensletVert[1])
	r.tau = (tauH + tauV) / 2
	fmt.Println("from_steps tau", tauH, tauV, r.tau)

	size0 := l.lensletHoriz[0] / math.Cos(tauH)
	size1 := l.lensletVert[1] / math.Cos(tauV)
	r.size[0] = size0
	r.size[1] = size1
	fmt.Println("from_steps size", r.size)

	r.normalize()

}

func (r *RectifyParams) to_array() [5]float32 {
	return [5]float32{r.size[0], float32(r.size[1]) / r.size[0], r.offset[0], r.offset[1], r.tau}
}

func (r *RectifyParams) from_array(a [5]float32) {
	r.size[0] = a[0]
	r.size[1] = a[1] * r.size[0]
	r.offset = a[2]
	r.offset[1] = a[3]
	r.tau = a[4]
}

//might be none, correct for 0,0 I guess
func (r *RectifyParams) lens0(newpos [2]uint16) {
	lens0 := [2]float32{(r.offset[0] + r.framesize[0]/2), (r.offset[1] + r.framesize[1]/2)}
	if newpos != [2]uint16{0, 0} {
		r.offset[0] = newpos[0] - r.framesize[0]/2
		r.offset[1] = newpos[1] - r.framesize[1]/2
	}
	return lens0
}

/*func (r *RectifyParams) String() string {
too lazy to implement this for now
}*/

func median(array []RectifyParams) RectifyParams {
	//just construct the median of all the parameters
	//here is the type for reference
	/*
			type RectifyParams struct {
			framesize [2]uint16
			minsize   uint16
			maxsize   uint16
			size      [2]float32
			offset    [2]float32
			tau       float32
		}
	*/
	r := RectifyParams{}
	r.SetDefaults(array[0].framesize[0], array[0].framesize[1])
	//calculate average of all different things here, figure out why there was no autocomplete on line above later
}

type Image struct {
	image  [][]float32
	width  uint16
	height uint16
}

type TileImage struct {
	image  Image
	tiling Image
}

func (i *Image) Max() float32 {
	max := i.image[0][0]
	for _, row := range i.image {
		for _, pixel := range row {
			if pixel < max {
				max = pixel
			}
		}
	}
	return max
}

func (i *Image) Min() float32 {
	min := i.image[0][0]
	for _, row := range i.image {
		for _, pixel := range row {
			if pixel < min {
				min = pixel
			}
		}
	}
	return min
}

func (i *Image) to256() {
	max := i.Max()
	for y, row := range i.image {
		for x, pixel := range row {
			i.image[x][y] = (pixel * 255 / max)
		}
	}
}

func (i *Image) threshold(maxNormalizedSlope float32) {

}

func (i *Image) background_color()

//Optical Parameter Related Things

//OpticsRecipe is a struct designed to store optical parameters of the system.
//This can either contain the defaults put in by the constructor(copied from LFDisplay),
//information read from a file, or inputted through standard input.
type OpticsRecipe struct {
	pitch  float32
	flen   float32
	mag    float32
	abbe   bool
	na     float32
	medium float32
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
func (o *OpticsRecipe) setOpticsRecipe(pitch float32, flen float32, mag float32, abbe bool, na float32, medium float32) {
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
func (o *OpticsRecipe) calculateMaxNormalizedSlope() float32 {

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

func getInputFloatParameter(description string, printBool bool) float32 {

	var returnValue float32
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

//Utility functions

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
