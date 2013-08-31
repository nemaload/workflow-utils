# This is a collection of useful functions used across our Python tools
# working with HDF5 lightfield files.

import numpy

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


def lenslets_offset2corner(ar):
    """
    Walk from the lenslets offset point to the point of the grid
    nearest to the top left corner.
    """
    corner = [ar._v_attrs['y_offset'], ar._v_attrs['x_offset']]

    changed = True
    while changed:
        changed = False
        if corner[1] > corner[0] and corner[0] > ar._v_attrs['down_dx'] and corner[1] > ar._v_attrs['down_dy']:
            corner[0] -= ar._v_attrs['down_dx']
            corner[1] -= ar._v_attrs['down_dy']
            changed = True
        if corner[0] > ar._v_attrs['right_dx'] and corner[1] > ar._v_attrs['right_dy']:
            corner[0] -= ar._v_attrs['right_dx']
            corner[1] -= ar._v_attrs['right_dy']
            changed = True
        if corner[1] > corner[0] and corner[0] > ar._v_attrs['down_dx'] and corner[1] > ar._v_attrs['down_dy']:
            corner[0] -= ar._v_attrs['down_dx']
            corner[1] -= ar._v_attrs['down_dy']
            changed = True
    # FIXME: Note that we might get stuck at a point where we e.g. still have
    # some room to go many steps up at the cost of going one step right.

    return corner


def compute_uvframe(node, ar, ofs_U = 0., ofs_V = 0.):
    """
    Generate a view of the sample from a particular (U,V) viewpoint
    from the lightsheet data (as stored in HDF5 @node). The view
    is returned as a numpy 2D array.
    """
    imgdata = node.read()
    # scipy.misc.imsave('rawimage.png', imgdata)

    gridsize = (int(imgdata.shape[0] / ar._v_attrs['down_dy']), int(imgdata.shape[1] / ar._v_attrs['right_dx']))
    corner = lenslets_offset2corner(ar)

    # We also rotate the image by 90\deg during the processing to maintain
    # compatibility with other parts of our toolchain.

    uvframe = numpy.zeros(shape=(gridsize[1], gridsize[0]), dtype='short')

    (right_dx, right_dy) = ar._v_attrs['right_dx'], ar._v_attrs['right_dy']
    (down_dx, down_dy) = ar._v_attrs['down_dx'], ar._v_attrs['down_dy']

    for y in range(int(gridsize[0])):
        for x in range(int(gridsize[1])):
            cx = corner[1] + x * right_dx + y * down_dx + ofs_U
            cy = corner[0] + x * right_dy + y * down_dy + ofs_V
            try:
                uvframe[gridsize[1]-1 - x][y] = imgdata[int(round(cy))][int(round(cx))]
                #print cx, cy, gridsize[1]-1 - x, y, int(uvframe[gridsize[1]-1 - x][y])
            except IndexError:
                #print cx, cy, gridsize[1]-1 - x, y, '---'
                pass

    return uvframe
