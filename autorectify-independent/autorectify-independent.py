#!/usr/bin/env python

# autorectify-independent analyzes microlens array images and computes parameters
# describing the size, spacing, and location of lenses.
# Copyright (C) 2013 NEMALOAD

# Original autorectify code by Petr Baudis
# Independence modifications by Michael Schmatz

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Contact Information:
# NEMALOAD
# nemaload.com


import math
import numpy
import random
import time

import cv
import cv2
import matplotlib.pyplot as plt
import matplotlib.patches

#various file processing/OS things
import h5py
import os
import sys
import argparse
import random

import pymongo
import bson

MIN_RADIUS = 12
MAX_RADIUS = 30
# These are colors of frames shown in debug image plots
colors = [ "lightsalmon", "lightgreen", "lightblue", "red", "green", "blue" ]


def autorectify(frame, maxu, verbose):
    """
    Automatically detect lenslets in the given frame with the
    given optics parameters (maxu==maxNormalizedSlope) and return
    a tuple of (lensletOffset, lensletHoriz, lensletVert).
    Frame is a numpy array(this is different from the original autorectify)
    """
    # solution = autorectify_de(frame, maxu)
    start_t = time.asctime()
    solution = autorectify_cv(frame, maxu, verbose)
    if verbose:
        print "start", start_t, "end", time.asctime()
    return solution.to_steps()


def autorectify_cv(frame, maxu, verbose):
    """
    Autorectification based on computer vision analysis.
    """
    #image = frame.to_numpy_array()
    image = frame

    tiling = ImageTiling(image, MAX_RADIUS * 5)
    tiling.scan_brightness()

    n_samples = 16
    tiles = range(n_samples)
    rps = range(n_samples)
    for i in range(n_samples):
      while True:
       try:
        (tiles[i], rps[i]) = sample_rp_from_tiling(frame, tiling, maxu, i, verbose)

       except IndexError:
        # IndexError can be thrown in case one of the areas reaches
        # to one edge of the tile; try with another tile
        if verbose:
            print ">>> bad region, retrying"
        continue

       else:
        break

    # Show window with whole image, tile parts highlighted
    #f = plt.figure("whole")
    #imgplot = plt.imshow(image.reshape(image.shape[0], image.shape[1]), cmap = plt.cm.gray)
    #for i in range(n_samples):
    #    (ul, br) = tiles[i]
    #    ax = f.add_subplot(111)
    #    rect = matplotlib.patches.Rectangle((ul[1],ul[0]),
    #            width=tiling.tile_step, height=tiling.tile_step,
    #            edgecolor=colors[i % len(colors)], fill=0)
    #    ax.add_patch(rect)
    #plt.show()

    rp = RectifyParams.median(rps, verbose)

    # Fine-tune central lens position
    lens0 = rp.lens0()
    try:
        lens0 = finetune_lens_position(image, maxu, rp, lens0,verbose)
    except IndexError:
        # This went horrendously wrong. Just retry the whole operation.
        if verbose:
            print "!!! Index error when finetuning lens0; retrying autorectification"
        return autorectify_cv(frame, maxu, verbose)
    rp.lens0(lens0)

    # Incrementally look at and fine-tune more lens in four directions
    delta = 2
    TRAIN_GRID_DIAMETER = 64
    TRAINING_STEPS = 8
    while delta <= TRAIN_GRID_DIAMETER:
        if verbose:
            print "retuning delta", delta, "rp", rp
            # Show window with whole image and some lens dotting
            #punched = image.reshape(image.shape[0], image.shape[1]).copy() / 8
            #for dird in numpy.array([[1,0], [-1,0], [0,1], [0,-1]]):
            #    for dirm in range(-TRAIN_GRID_DIAMETER, TRAIN_GRID_DIAMETER):
            #        try:
            #            punched[tuple(rp.xylens(dird * dirm))] = 255
            #        except IndexError:
            #            pass
            #figdpi = 80.0
            #fig = plt.figure("Image with lens dotting", figsize=(image.shape[0] / figdpi, image.shape[1] / figdpi), dpi=figdpi)
            #fig.figimage(punched, cmap=plt.cm.gray)
            #plt.show()

        try:
            rp = refine_rp_by_lens_finetune(image, maxu, rp, delta, verbose)
        except IndexError:
            print "out of bounds, stopping early"
            break

        delta = delta + TRAIN_GRID_DIAMETER / TRAINING_STEPS

    if verbose:
        print "final rp", rp
    return rp


def swapxy(a):
    """
    If a is array[2] with coordinates, swap the elements.
    This allows for transforming Y,X to X,Y coordinates
    and vice versa.
    """
    return numpy.array([a[1], a[0]])

def sample_rp_from_tiling(frame, tiling, maxu, i, verbose):
    t = tiling.random_tile()
    s = tiling.tile_step
    perturb = [numpy.random.randint(-s/4, s/4), numpy.random.randint(-s/4, s/4)]
    (ul, br) = tiling.tile_to_imgxy(t, perturb)
    if verbose:
        print tiling.image.shape, "t", t, "p", perturb, "ul", ul, "br", br
    # image pixels in the chosen tile
    timage = TileImage(tiling, tiling.image[ul[0]:br[0], ul[1]:br[1]].reshape(s, s).copy())
    timage.to256()

    # convert to black-and-white
    timage.threshold(maxu)

    # Show the tile
    #print("tile " + str(i) + ": " + colors[i % len(colors)])
    #print timage.image
    #plt.figure("Tile " + str(i) + ": " + colors[i % len(colors)])
    #imgplot = plt.imshow(timage.image, cmap=plt.cm.gray)
    #plt.show()

    # Smooth out noise
    timage.smooth()

    # Show the tile
    #plt.figure("Smooth tile " + str(i) + ": " + colors[i % len(colors)])
    #imgplot = plt.imshow(timage.image, cmap=plt.cm.gray)
    #plt.show()

    # Identify a lens grid hole
    holepos = timage.find_any_region(0)
    holec = timage.find_region_center(0, holepos)

    # Build 3x3 hole matrix
    matrixsize = 1
    holematrix = numpy.array([[timage.find_next_region_center(0, holec, dy, dx)
                               for dx in range(-matrixsize, matrixsize+1)]
                              for dy in range(-matrixsize, matrixsize+1)])

    # Show the holes
    #punched = timage.image.copy() / 2
    #for y in range(matrixsize*2 + 1):
    #    for x in range(matrixsize*2 + 1):
    #        # print y, " ", x
    #        # print "  ", holematrix[y, x]
    #        punched[tuple(holematrix[y, x])] = 255
    #plt.figure("Tile with hole center " + str(i) + ": " + colors[i % len(colors)])
    #imgplot = plt.imshow(punched, cmap=plt.cm.gray)
    #plt.show()

    lensmatrix = numpy.array([[timage.find_lens_from_holes(255, holematrix[y:y+2, x:x+2], y, x)
                               for x in range(0, matrixsize*2)]
                              for y in range(0, matrixsize*2)])

    # Show the lens
    #punched = timage.image.copy() / 2
    #for y in range(matrixsize*2):
    #    for x in range(matrixsize*2):
    #        punched[tuple(lensmatrix[y, x])] = 64
    #print "lensmatrix", lensmatrix
    #plt.figure("Tile with lens center " + str(i) + ": " + colors[i % len(colors)])
    #imgplot = plt.imshow(punched, cmap=plt.cm.gray)
    #plt.show()

    # Convert lens matrix to RectifyParams
    lens0 = lensmatrix[0,0] + ul
    rp = RectifyParams([frame.shape[1], frame.shape[0]])
    lensletOffset = tuple(swapxy(lens0))
    lensletHoriz = tuple(swapxy(numpy.average([lensmatrix[0,1] - lensmatrix[0,0],
                                               lensmatrix[1,1] - lensmatrix[1,0]], 0)))
    lensletVert = tuple(swapxy(numpy.average([lensmatrix[1,0] - lensmatrix[0,0],
                                              lensmatrix[1,1] - lensmatrix[0,1]], 0)))
    if verbose:
        print "o", lensletOffset, "h", lensletHoriz, "v", lensletVert
    rp.from_steps((lensletOffset, lensletHoriz, lensletVert), verbose)
    if verbose:
        print "###", rp

    return ((ul, br), rp)

def finetune_lens_position(image, maxu, rp, lens0,verbose):
    matrixsize = 2
    matrixshape = numpy.array([matrixsize*2+1, matrixsize*2+1])
    matrixcenter = numpy.array([matrixsize, matrixsize])

    shiftmatrix = numpy.zeros(tuple(matrixshape))
    gradient = numpy.array([1000, 1000])

    while True:
        if lens0[0] < 0 or lens0[1] < 0 or lens0[0] >= image.shape[0] or lens0[1] >= image.shape[1]:
            raise IndexError

        shiftmatrix2 = numpy.zeros(tuple(matrixshape))
        for y in range(-matrixsize, matrixsize+1):
            for x in range(-matrixsize, matrixsize+1):
                c2 = matrixcenter + [y, x]
                c1 = c2 + gradient
                if (c1 < [0,0]).any() or (c1 >= matrixshape).any():
                    shiftmatrix2[tuple(c2)] = measure_rectification_one(image, maxu, rp, lens0 + [y, x])
                else:
                    shiftmatrix2[tuple(c2)] = shiftmatrix[tuple(c1)]
        shiftmatrix = shiftmatrix2

        gradient = numpy.array(numpy.unravel_index(shiftmatrix.argmax(), tuple(matrixshape))) - matrixcenter
        if verbose:
            print "lens0", lens0, "shiftmatrix", shiftmatrix, "gradient", gradient

        if gradient[0] == 0 and gradient[1] == 0:
            break
        if shiftmatrix[tuple(matrixcenter + gradient)] <= shiftmatrix[tuple(matrixcenter)]:
            # If best candidate is as good as staying put, stop
            break
        lens0 += gradient

    return lens0

def refine_rp_by_lens_finetune(image, maxu, rp, delta, verbose):
    dirs = numpy.array([[1,0], [-1,0], [0,1], [0,-1]]) * delta

    (lensletOffset, lensletHoriz, lensletVert) = rp.to_steps()
    lens_before = [rp.xylens(d) for d in dirs]
    lens_after = [finetune_lens_position(image, maxu, rp, l.copy(), verbose) for l in lens_before]
    if verbose:
        print "  before", lens_before
        print "  after ", lens_after

    lensletHorizNew = (lens_after[0] - lens_after[1]) / (delta*2)
    lensletVertNew = (lens_after[2] - lens_after[3]) / (delta*2)

    # Adjusted hypothesis regarding central point
    lensletOffsetH = lens_after[1] + lensletHorizNew * delta;
    lensletOffsetV = lens_after[3] + lensletVertNew * delta;
    lensletOffsetNew = (lensletOffsetH + lensletOffsetV) / 2;

    print "  h,v,o before", lensletHoriz, lensletVert, lensletOffset
    print "  h,v,o after ", lensletHorizNew, lensletVertNew, lensletOffsetNew

    # Update central point + steps with some weight; this makes sure
    # one weird measurement will not ruin everything
    uwfactor = math.sqrt(2./delta) # later updates move coordinates somewhat less
    UPDATE_WEIGHT = numpy.array([0.8 * uwfactor, 0.8 * uwfactor]) # x,y
    lensletOffset = lensletOffsetNew * UPDATE_WEIGHT + lensletOffset * (1.0 - UPDATE_WEIGHT)
    lensletHoriz = lensletHorizNew * UPDATE_WEIGHT + lensletHoriz * (1.0 - UPDATE_WEIGHT)
    lensletVert = lensletVertNew * UPDATE_WEIGHT + lensletVert * (1.0 - UPDATE_WEIGHT)

    rp.from_steps((lensletOffset, lensletHoriz, lensletVert), verbose)
    return rp


class TileImage:
    """
    A holding class for image (numpy array) of a single tile
    analyzed.
    """
    def __init__(self, tiling, timage):
        self.tiling = tiling
        self.image = timage
    def to256(self):
        self.image = (self.image.astype('float32') * 255. / self.image.max())
        return self

    def threshold(self, maxu):
        # Threshold such that background is black, foreground is white
        # (you may want to turn this on/off based on the method below)
        background_color = self.tiling.background_color(self.image, maxu)
        foreground_i = self.image > background_color
        self.image[foreground_i] = 255.
        self.image[numpy.invert(foreground_i)] = 0.
        return self
    def smooth(self):
        # Smooooth - twice!
        self.image = cv2.medianBlur(self.image, 3);
        self.image = cv2.medianBlur(self.image, 3);
        return self

    def find_any_region(self, color):
        c = numpy.array([self.tiling.tile_step / 2, self.tiling.tile_step / 2])
        step = 5
        while self.image[tuple(c)] != color:
            # Random walk over the neighborhood
            c[0] += int(step*2 * numpy.random.random_sample() - step)
            c[1] += int(step*2 * numpy.random.random_sample() - step)
            # print c, " -> ", self.image[tuple(c)]
        return c

    def find_region_center(self, color, holepos):
        xshape = self.xshape()
        holepos = holepos.astype('float')
        xdist = self.xdist(holepos, color)

        # XXX: just for debug print
        xdistavg = numpy.array([-1,-1,-1,-1])
        dir = -1
        step = -1
        cstep = -1

        i = 0
        while abs(xdist.min() - xdist.max()) > 1 and i < 100:
            # Unbalanced X distance, adjust
            step = (xdist.max() - xdist.min())/(1.5 + math.sqrt(i))
            xdistavgval = numpy.average(xdist)
            xdistavg = numpy.abs(xdist - xdistavgval)
            dir = xdistavg.argmax()
            cstep = xshape[dir]
            if xdist[dir] < xdistavgval:
                cstep = -cstep
            # print "walking: ", holepos, " | xdist: ", xdist, " avg ", xdistavg, " == ", dir, " | <- ", step, cstep
            holepos += step * cstep
            xdist = self.xdist(holepos, color)
            i += 1
        # print "walked : ", holepos, " | xdist: ", xdist, " avg ", xdistavg, " == ", dir, " | <- ", step, cstep
        return holepos.astype('int')

    def find_next_region_center(self, color, holepos, dy, dx):
        if dy == 0 and dx == 0:
            return holepos
        xdist = numpy.average(self.xdist(holepos, color))
        delta = numpy.array([dy, dx])

        nexthole = holepos + delta * xdist*4
        while self.image[tuple(nexthole)] != color:
            nexthole += delta
        return self.find_region_center(color, nexthole)

    def find_lens_from_holes(self, color, holepos, y, x):
        lenspos = numpy.array([numpy.average(holepos[:,:,0]), numpy.average(holepos[:,:,1])]).astype('int')
        # print x, y, " holepos", holepos, " | ", holepos[:,:,0], " -- ", holepos[:,:,1], " -> lenspos ", lenspos
        return self.find_region_center(color, lenspos)

    def xdist(self, c, color):
        # Measure distances of black in four directions of an "X shape"
        xshape = self.xshape()
        dist = numpy.array([0, 0, 0, 0])
        for dir in range(4):
            for i in range(100):
                ccolor = self.image[tuple((c + xshape[dir] * i).astype('int'))]
                if ccolor != color:
                    dist[dir] = i
                    break
        return dist

    def xshape(self):
        return numpy.array([[-1,-1], [-1,1], [1,1], [1,-1]])


def autorectify_de(frame, maxu, verbose):
    """
    Autorectification based on differential evolution.
    """
    if verbose:
        print "init"
    # Work on a list of solutions, initially random
    solutions_n = 20
    solutions = [RectifyParams([frame.shape[1], frame.shape[0]]).randomize()
                     for i in range(solutions_n)]
    # 2160x2560 -> 1080x1280
    # (1284.367000,1190.300000,23.299000,-0.032000,-0.035000,23.262000)
    # (x-offset,y-offset,right-dx,right-dy,down-dx,down-dy)
    solutions[0].size[0] = 23.3
    solutions[0].size[1] = 23.3
    solutions[0].tau = 0.0137397938
    solutions[0].offset[0] = -8.907
    solutions[0].offset[1] = -6.303
    if verbose:
        print solutions[0].to_steps()

    #image = frame.to_numpy_array()
    image = frame
    tiling = ImageTiling(image, MAX_RADIUS * 5)
    tiling.scan_brightness()
    if verbose:
        print "best..."
    # Initialize the best solution info by something random
    sbest = solutions[0]
    value_best = measure_rectification(image, tiling, maxu, sbest)

    # Improve the solutions
    episodes_n = 50
    for e in range(episodes_n):
        if verbose:
            print "EPISODE ", e
        # We iterate through the solutions in a random order; this
        # allows us to reuse the same array to obtain recombination
        # solutions randomly and safely.
        permutation = numpy.random.permutation(solutions_n)
        for si in permutation:
            if verbose:
                print " solution ", si
            s = solutions[si]
            value_old = measure_rectification(image, tiling, maxu, s)
            if verbose:
                print "  value ", value_old

            # Cross-over with recombination solutions
            sa = s.to_array()
            r1a = solutions[(si + 1) % solutions_n].to_array()
            r2a = solutions[(si + 2) % solutions_n].to_array()
            r3a = solutions[(si + 3) % solutions_n].to_array()
            dim_k = 5
            CR = 0.5/dim_k
            F = 0.5 * (1 + numpy.random.random_sample()) # [0.5,1) random
            co_k = numpy.random.randint(dim_k);
            for k in range(dim_k):
                if k == co_k or numpy.random.random_sample() < CR:
                    #print " DE " + str(r1a[k]) + " " + str(r2a[k]) + " " + str(r3a[k])
                    sa[k] = r1a[k] + F * (r2a[k] - r3a[k])

            # Compare and swap if better
            s2 = s
            s2.from_array(sa).normalize()
            value_new = measure_rectification(image, tiling, maxu, s2)
            if verbose:
                print "  new value ", value_new
            if value_new > value_old:
                if verbose:
                    print "   ...better than before"
                solutions[si] = s2
                if value_new > value_best:
                    if verbose:
                        print "   ...and best so far!"
                    sbest = s2
                    value_best = value_new

    # Return the best solution encountered
    if verbose:
        print "best is ", sbest, " with value ", value_best
    return sbest


def measure_rectification(image, tiling, maxu, rparams):
    """
    Measure rectification quality of rparams on a random sample of lens.
    """
    gridsize = rparams.gridsize()
    n_samples = int(10 + round(gridsize[0] * gridsize[1] / 400))
    # print "  measuring ", rparams, " with grid ", gridsize, " and " ,n_samples ," samples"

    value = 0.

    # TODO: Draw all samples at once
    for i in range(n_samples):
        t = tiling.random_tile()
        s = tiling.tile_to_lens(t, rparams)
        # print "tile ", t, "lens ", s
        value += measure_rectification_one(image, maxu, rparams, rparams.xylens(s))

    return value / n_samples


def measure_rectification_one(image, maxu, rparams, lenspos):
    """
    Measure rectification of a single given lens.
    """
    lenssize = rparams.size * maxu

    # print "measuring (", lenspos, " - ", lenssize, ") with ", rparams

    value_inlens = 0.
    value_outlens = 0.

    for x in range(int(round(-rparams.size[0]/2)), int(round(rparams.size[0]/2))):
        for y in range(int(round(-rparams.size[1]/2)), int(round(rparams.size[1]/2))):
            # XXX: we could tilt the whole coordinate grid at once
            # (or actually the source image subspace) to speed things up
            inLensPos = rparams.xytilted([x, y])

            imgpos = lenspos + inLensPos
            # XXX: subpixel sampling?
            imgpos = imgpos.round()

            # print " ", [x, y], " in lens ", rparams, " is ", inLensPos, ", in-img is ", imgpos

            try:
                # sum() is not terribly good pixval, TODO maybe calculate
                # actual brightness?
                pixval = sum(image[int(imgpos[1])][int(imgpos[0])])
            except IndexError:
                # Do not include out-of-canvas pixels in the computation.
                # Therefore, out-of-canvas tiles will have both inlens
                # and outlens values left at zero.
                # print "index error for ", lenspos, " -> ", imgpos
                continue

            # Are we in the ellipsis defined by lenssize?
            if ((inLensPos / lenssize) ** 2).sum() <= 1.:
                # print " IN LENS pixval ", pixval, " for ", lenspos, " -> ", imgpos
                value_inlens += pixval
            else:
                # print "OUT LENS pixval ", pixval, " for ", lenspos, " -> ", imgpos
                value_outlens += pixval

    # Just avoid division by zero
    eps = numpy.finfo(numpy.float).eps
    return (value_inlens + eps) / (value_outlens + eps)


class RectifyParams:
    """
    This class is a container for microlens partitioning information
    (rectification parameters) in a format suitable for optimization:

    framesize[2] (size of the frame; constant)
    size[2] (size of a single lenslet, i.e. the lens grid spacing)
            (but what is evolved is single dimension and aspect ratio)
            size \in [5, 64] after normalize()
    offset[2] (shift of the lens grid center relative to image center)
            offset \in [-size/2, +size/2] after normalize()
    tau (tilt of the lens grid, i.e. rotation (CCW) by grid center in radians)
            tau \in [0, pi/8) after normalize()

    (...[2] are numpy arrays)
    """

    def __init__(self, framesize):
        self.framesize = numpy.array(framesize)
        self.minsize = MIN_RADIUS
        self.maxsize = MAX_RADIUS

    def randomize(self):
        """
        Initialize rectification parameters with random values
        (that would pass normalize() inact).
        """
        # XXX: Something better than uniformly random?
        self.size = numpy.array([0., 0.])
        self.size[0] = self.minsize + numpy.random.random_sample() * (self.maxsize - self.minsize)
        self.size[1] = self.size[0] * (0.8 + numpy.random.random_sample() * 0.4)
        self.offset = numpy.array([numpy.random.random_sample(), numpy.random.random_sample()]) * self.size - self.size/2
        self.tau = numpy.random.random_sample() * math.pi/8
        return self

    def gridsize(self):
        """
        Return *approximate* dimensions of the grid defined by an array
        of given lens. Tilt is not taken into account.
        """
        return numpy.array(self.framesize / self.size).round()

    def xytilted_tau(self, ic, tau):
        """
        Return image coordinates tilted by given tau.
        """
        return numpy.array([ic[0] * math.cos(tau) - ic[1] * math.sin(tau),
                            ic[0] * math.sin(tau) + ic[1] * math.cos(tau)])

    def xytilted(self, ic):
        """
        Return image coordinates tilted by self.tau.
        """
        return self.xytilted_tau(ic, self.tau)

    def xylens(self, gc):
        """
        Return image coordinates of a lens at given grid coordinates.
        [0, 0] returns offset[].
        """
        center_pos = self.framesize / 2 + self.offset
        straight_pos = self.size * gc
        tilted_pos = self.xytilted(straight_pos)
        # print "xylens(", gc, ") ", self.framesize, " / 2 = ", self.framesize / 2, " -> ", center_pos, " ... + ", straight_pos, " T", self.tau, " ", tilted_pos, " => ", center_pos + tilted_pos
        return center_pos + tilted_pos

    def lensxy(self, ic):
        """
        Return lens grid coordinates corresponding to given image coordinates.
        """
        center_pos = self.framesize / 2 + self.offset
        tilted_pos = ic - center_pos
        straight_pos = self.xytilted_tau(tilted_pos, -self.tau)
        return (straight_pos / self.size).astype(int)

    def normalize(self):
        """
        Normalize parameters so that the offset is by less than
        one lens size (i.e. 0 +- size/2) and tau is less than pi/8.
        """
        self.size = abs(self.size)

        # For <minsize we trim to minsize, but for >maxsize we
        # reset randomly so that our specimen do not cluster
        # around maxsize aimlessly.
        if self.size[0] > self.maxsize:
            self.size[0] = self.minsize + numpy.random.random_sample() * (self.maxsize - self.minsize)
        elif self.size[0] < self.minsize:
            self.size[0] = self.minsize
        if self.size[1] > self.maxsize:
            self.size[1] = self.size[0] * (0.8 + numpy.random.random_sample() * 0.4)
        elif self.size[1] < self.minsize:
            self.size[1] = self.minsize

        self.tau = (self.tau + math.pi/16) % (math.pi/8) - math.pi/16

        #diag_step = self.xytilted(self.size)
        #print "normalize pre: ", self.offset, self.size, diag_step
        #self.offset = (self.offset + self.size/2) % diag_step - self.size/2
        #print "normalize post: ", self.offset

        return self

    def to_steps(self):
        """
        Convert parameters to a tuple of
        (lensletOffset, lensletHoriz, lensletVert).
        """
        lensletOffset = self.framesize/2 + self.offset
        lensletHoriz = self.xytilted([self.size[0], 0])
        lensletVert = self.xytilted([0, self.size[1]])
        return (lensletOffset.tolist(), lensletHoriz.tolist(), lensletVert.tolist())

    def from_steps(self, steps, verbose):
        """
        Load parameters from a tuple of
        (lensletOffset, lensletHoriz, lensletVert).
        """
        (lensletOffset, lensletHoriz, lensletVert) = steps
        self.offset = numpy.array(lensletOffset) - self.framesize/2

        tauH = math.atan2(lensletHoriz[1], lensletHoriz[0])
        tauV = math.atan2(-lensletVert[0], lensletVert[1])
        self.tau = numpy.average([tauH, tauV]) # typically, tauH == tauV
        if verbose:
            print "from_steps tau ", tauH, tauV, self.tau

        size0 = lensletHoriz[0] / math.cos(tauH)
        size1 = lensletVert[1] / math.cos(tauV)
        self.size = numpy.array([size0, size1])
        if verbose:
            print "from_steps size ", self.size

        # normalize() seems to do things with .offset that are not proper
        #self.tau = self.tau % (math.pi/8)
        self.normalize()

        # Whew!
        return self

    def to_array(self):
        """
        Convert parameters to an array of values to be opaque
        for optimization algorithm; after optimization pass,
        call from_array to propagate the values back.

        One significant difference between RectifyParams attributes
        and the optimized values is that size is represented not
        as an [x,y] pair but rather [x,aspectratio] pair.
        """
        return numpy.array([self.size[0], float(self.size[1]) / self.size[0], self.offset[0], self.offset[1], self.tau])

    def from_array(self, a):
        """
        Restore parameters from the array serialization.
        """
        self.size[0] = a[0]; self.size[1] = a[1] * self.size[0]
        self.offset[0] = a[2]; self.offset[1] = a[3]
        self.tau = a[4]
        return self

    def lens0(self, newpos = None):
        """
        Retrieve the center coordinates of the central lens,
        and possibly update parameters with the new center
        coordinates of the central lens.
        """
        lens0 = self.offset + self.framesize/2
        if newpos is not None:
            self.offset = newpos - self.framesize/2
        return lens0

    def __str__(self):
        return "[size " + str(self.size) + " offset " + str(self.offset) + " tau " + str(self.tau * 180 / math.pi) + "deg]"

    @staticmethod
    def median(array, verbose):
        """
        From an array of RectifyParams[] objects, construct median parameters.
        An exception is offset; we prefer an offset nearest the center of
        the image.
        """

        size0 = numpy.array([array[i].size[0] for i in range(len(array))])
        size0.sort()
        size1 = numpy.array([array[i].size[1] for i in range(len(array))])
        size1.sort()
        offset = sorted([array[i].offset for i in range(len(array))], key = lambda o: o[0]**2 + o[1]**2)
        tau = numpy.array([array[i].tau for i in range(len(array))])
        tau.sort()

        rpmedian = RectifyParams(array[0].framesize)
        rpmedian.size = numpy.array([size0[len(size0)/2], size1[len(size1)/2]])
        rpmedian.offset = offset[0]
        rpmedian.tau = tau[len(tau)/2]
        if verbose:
            print "median:", rpmedian
        return rpmedian


class ImageTiling:
    """
    This class represents a certain tiling of the image (numpy 3D array)
    used for brightness data collection and sampling.
    """

    def __init__(self, image, tile_step):
        self.tile_step = tile_step
        self.height_t = int(image.shape[0] / tile_step)
        self.width_t = int(image.shape[1] / tile_step)

        # Adjust image view to be cropped on tile boundary
        self.height = self.height_t * tile_step
        self.width = self.width_t * tile_step
        self.image = image[0:self.height, 0:self.width]

    def scan_brightness(self):
        """
        Compute per-tile brightness data (mean, sd)
        and construct an empiric probability distribution based
        on this data (...that prefers tiles with average brightness).
        """

        # Create a brightness map from image
        # sum() is not terribly good brightness approximation
        brightmap = self.image.sum(2)

        # Group rows and columns by tiles
        tiledmap = brightmap.reshape([self.height_t, self.tile_step, self.width_t, self.tile_step])

        # brightavgtiles is brightness mean of specific tiles
        self.brightavgtiles = tiledmap.mean(3).mean(1)
        # rescale per-tile brightness mean so that minimum is 0
        # and maximum is 1
        minbrightness = self.brightavgtiles.min()
        maxbrightness = self.brightavgtiles.max()
        ptpbrightness = maxbrightness - minbrightness
        brightxavgtiles = (self.brightavgtiles - minbrightness) / ptpbrightness

        # brightstdtiles is brightness S.D. of specific tiles
        brightstdtiles = numpy.sqrt(tiledmap.var(3).mean(1))

        # distances from image center
        tilecenters = numpy.array([[[y, x]
                                    for x in range(self.tile_step/2, self.width, self.tile_step)]
                                   for y in range(self.tile_step/2, self.height, self.tile_step)])
        tilecdists = numpy.sqrt(numpy.sum((tilecenters - [self.height / 2, self.width / 2]) ** 2, 2))

        # construct probability distribution such that
        # xavg 0.5 has highest probability
        # also factored in is preference for central tiles
        # as there are fish eye deformities near the borders
        # TODO: Also consider S.D.? But how exactly?
        # We might want to maximize S.D. to focus on
        # areas with sharpest lens shapes, or minimize S.D.
        # to focus on areas with most uniform lens interior...
        # TODO: Nicer distribution shape?
        #self.pdtiles = (0.5*0.5*0.5 - numpy.power(0.5 - brightxavgtiles, 3)) / numpy.sqrt(tilecdists)
        self.pdtiles = numpy.power(brightstdtiles, 3) / numpy.sqrt(tilecdists)
        self.pdtiles_sum = self.pdtiles.sum()

        #for t in numpy.mgrid[0:self.height_t, 0:self.width_t].T.reshape(self.height_t * self.width_t, 2):
        #    # t = [y,x] tile index
        #    print(t[1], " ", t[0], ": ", self.pdtiles[t[0], t[1]], " (bavg ", self.brightavgtiles[t[0], t[1]], " bxavg ", brightxavgtiles[t[0], t[1]], ")")

        return self

    def random_tile(self):
        """
        Choose a random tile with regards to the brightness distribution
        among tiles (as pre-processed by scan_brightness().
        """

        stab = numpy.random.random_sample() * self.pdtiles_sum
        for t in numpy.mgrid[0:self.height_t, 0:self.width_t].T.reshape(self.height_t * self.width_t, 2):
            # t = [y,x] tile index
            prob = self.pdtiles[t[0], t[1]]
            if prob > stab:
                return numpy.array([t[1], t[0]])
            stab -= prob
        # We reach here only in case of float arithmetic imprecisions;
        # just pick a uniformly random tile
        #print "ImageTiling.random_tile(): fallback to random (warning)"
        return numpy.array([numpy.random.randint(self.height_t), numpy.random.randint(self.width_t)])

    def tile_to_imgxy(self, tile, perturb=[0,0]):
        """
        Return image coordinates corresponding to the top left
        and bottom right corner of a given tile. The origin
        is perturbed by the given offset.
        """
        origin = numpy.array([tile[0] * self.tile_step,
                              tile[1] * self.tile_step])
        origin += perturb
        numpy.clip(origin, 0, [self.image.shape[0] - self.tile_step, self.image.shape[1] - self.tile_step], origin)
        return (origin, origin + [self.tile_step, self.tile_step])

    def tile_to_lens(self, tile, rparams):
        """
        Return lens grid coordinates corresponding to the center
        of a given tile.
        """
        imgcoords = numpy.array([
            tile[0] * self.tile_step + self.tile_step/2,
            tile[1] * self.tile_step + self.tile_step/2])
        return rparams.lensxy(imgcoords)

    def background_color(self, timage, maxu):
        """
        Make an educated guess on the shade level corresponding to the
        background (non-lens) color.
        """
        # The lens radius shall correspond to maxu * grid step.
        # Therefore, lens array area is 2*maxu * total_area and
        # 1-lens_area shall be background color. In addition,
        # in the lens array area, single lens square is 4*r^2
        # while the lens circle is pi*r^2.
        # Therefore, background color should occupy roughly
        # (1-2*maxu + 1-pi/4) fraction of the whole area.
        background_fract = (1 - 2*maxu) + (1 - math.pi/4)

        # color_relcounts will contain relative counts of all
        # shades in timage
        color_nshades = 256
        (color_counts, color_bounds) = numpy.histogram(timage, color_nshades, (0., timage.max()))
        color_relcounts = color_counts.astype('float32') / float(self.tile_step ** 2)
        #print timage
        #print color_counts
        #print color_relcounts

        # find the boundary nearest to background_fract
        sum_fract = 0.
        for i in range(color_nshades):
            #print "bg " + str(background_fract) + " i " + str(i) + " rc " + str(color_relcounts[i]) + " +> " + str(sum_fract)
            sum_fract_2 = sum_fract + color_relcounts[i]
            if sum_fract_2 > background_fract:
                # good, we are over the boundary! but maybe it's
                # a closer shot if we choose the previous shade
                if i > 0 and background_fract - sum_fract < sum_fract_2 - background_fract:
                    return (color_bounds[i-1] + color_bounds[i]) / 2
                elif i < color_nshades-1:
                    return (color_bounds[i+1] + color_bounds[i]) / 2
                else:
                    return color_bounds[i-1]
            sum_fract = sum_fract_2
        #print "???"
        return 0.5 # unf, what else to do?

#This is the command line stuff
#Output format:
#(1710.000000,1148.000000,20.000000,0.000000,0.000000,20.000000)
# (x-offset,y-offset,right-dx,right-dy,down-dx,down-dy)
#when HDF5 is standardized, import optical parameters from HDF5 file.
if __name__ == '__main__':
    #usage related code
    parser = argparse.ArgumentParser(
        prog='autorectify-independent.py',
        description='A command-line tool to calculate lenslet rectifications')
    parser.add_argument("input", type=str,
        help="""The input file(HDF5).""")
    parser.add_argument(
        '-v',
        '--verbose',
        help="""Verbose mode""",
        action="store_true")

    parser.add_argument('-p',
        '--percent',
        help="""The percentage of images to be processed for a sample in a multi image dataset""",
        nargs=1)
    parser.add_argument(
        '-o',
        '--output',
        help="The filename or path of the output file(must have HDF5 extension, not exist)",
        nargs=1)
    parser.add_argument(
        '-m',
        '--mongodb',
        help="Store data in MongoDB (of a nemashow Meteor instance) instead of a HDF5 file",
        action="store_true")
    parser.add_argument(
        '-r',
        '--randomseed',
        help="Random generator seed (for reproducible autorectification runs)",
        nargs=1)

    args = parser.parse_args()
    if args.verbose:
        verboseMode = True
    else:
        verboseMode = False

    if args.randomseed is not None:
        numpy.random.seed(args.randomseed)

    inputPlace = args.input
    #check that input file exists, and is a valid HDF5 file
    if not os.path.isfile(inputPlace):
        sys.exit("Input file does not exist.")
    root, ext = os.path.splitext(inputPlace)
    if ext != ".hdf5":
        sys.exit("Invalid file extension(must be '.hdf5'")
    #now open the file
    try:
        f = h5py.File(inputPlace,'r')
    except:
        sys.exit("There was an error opening the file. Perhaps it is corrupted. Exiting...")
    #now getting number of datasets in file
    try:
        imageGroup = f.require_group("images")
    except TypeError:
        sys.exit("No 'images' group found, which must exist for the file to be processed correctly. Exiting...")
    numberImages = len(imageGroup)
    numberOfImagesToProcess = 1
    if args.percent != None:
        if args.percent > 0 and args.percent < 100:
            numberOfImagesToProcess = math.ceil((float(args.percent)/100)*float(numberOfImagesToProcess))
        else:
            sys.exit("Invalid percentage given. Exiting...")
    framesToProcess = random.sample(range(numberImages),numberOfImagesToProcess)
    #get maxu
    maxu = 0.4667937556007068 #calculated from only optics data available at the time, serves as default
    if 'op_flen' in imageGroup.attrs:
        imagena = float(imageGroup.attrs['op_na']) / float(imageGroup.attrs['op_mag'])
        if imagena < 1.0:
            ulenslope = 1.0 * float(imageGroup.attrs['op_pitch']) / float(imageGroup.attrs['op_flen'])
            naslope = imagena / (1.0-imagena*imagena)**0.5
            maxu = float(naslope / ulenslope)
            if verboseMode:
                print "Using image-specific maxu of " + str(maxu)
        else:
            print "!!! Ignoring inconsistent optical parameters in the HDF5 file"

    rectification = ([0,0],[0,0],[0,0])
    for currentFrameIndex in framesToProcess:
        currentFrame = imageGroup[str(currentFrameIndex)].value
        currentFrame.shape = (currentFrame.shape[0], currentFrame.shape[1], 1)
        currentFrame = numpy.swapaxes(currentFrame,0,1)
        returnTuple = autorectify(currentFrame,maxu,verboseMode)
        print returnTuple
        for x in range(0,3):
            for y in range(0,2):
                rectification[x][y] += float(returnTuple[x][y])
    #divide by number of frames processed
    for x in range(0,3):
        for y in range(0,2):
            rectification[x][y] /= float(numberOfImagesToProcess)

    #print out here
    x_offset = rectification[0][0]
    y_offset = rectification[0][1]
    right_dx = rectification[1][0]
    right_dy = rectification[1][1]
    down_dx = rectification[2][0]
    down_dy = rectification[2][1]

    if args.mongodb:
        mongo = pymongo.Connection('localhost', 3002)
        db = mongo.meteor
        Images = db.images
        basename = os.path.basename(inputPlace)
        print 'baseName', basename
        Images.update({'baseName': basename}, {'$set': {
            "op_x_offset": x_offset,
            "op_y_offset": y_offset,
            "op_right_dx": right_dx,
            "op_right_dy": right_dy,
            "op_down_dx": down_dx,
            "op_down_dy": down_dy}})
        sys.exit(0)

    #spit out HDF5 file here
    if args.output:
        if os.path.isfile(args.output) or os.path.isfile(args.output):
            sys.exit("Output file or path already exists. Exiting...")
        outroot, outext = os.path.splitext(inputPlace)
        if outext != ".hdf5":
            sys.exit("Invalid output file extension(must be '.hdf5'")
        outputFile = h5py.File(args.output,'w-')
        print "Output file is located at " + args.output
    else:
        outputFile = h5py.File(root + '-autorectify.hdf5', 'w-')
        print "Output file is located at " + root + "-autorectify.hdf5"
    autorectificationGroup = outputFile.require_group("autorectification")
    autorectificationGroup.attrs['x_offset'] = x_offset
    autorectificationGroup.attrs['y_offset'] = y_offset
    autorectificationGroup.attrs['right_dx'] = right_dx
    autorectificationGroup.attrs['right_dy'] = right_dy
    autorectificationGroup.attrs['down_dx'] = down_dx
    autorectificationGroup.attrs['down_dy'] = down_dy

    outputFile.close()
