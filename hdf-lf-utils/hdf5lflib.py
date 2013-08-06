# This is a collection of useful functions used across our Python tools
# working with HDF5 lightfield files.

def compute_maxu(imageGroup):
    """
    Determine the maximum slope for looking through a lens, commonly
    referred to as `maxu`. Takes imageGroup (the HDF5 node carrying
    required .attrs[]) as a parameter, returns a tuple of
    (maxu, maxu_explicit).
    """
    maxu_explicit = False
    if 'op_maxu' in imageGroup.attrs:
        maxu = float(imageGroup.attrs['op_maxu'])
        maxu_explicit = True
    elif 'op_flen' in imageGroup.attrs:
        imagena = float(imageGroup.attrs['op_na']) / float(imageGroup.attrs['op_mag'])
        if imagena < 1.0:
            ulenslope = 1.0 * float(imageGroup.attrs['op_pitch']) / float(imageGroup.attrs['op_flen'])
            naslope = imagena / (1.0-imagena*imagena)**0.5
            maxu = float(naslope / ulenslope)
            if verboseMode:
                print "Using image-specific maxu of " + str(maxu)
        else:
            print "!!! Ignoring inconsistent optical parameters in the HDF5 file"
    else:
        maxu = 0.4667937556007068 #calculated from only optics data available at the time, serves as default
    return (maxu, maxu_explicit)
