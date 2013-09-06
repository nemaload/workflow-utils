#!/usr/bin/env python
#
# Extract pose information from a c. elegans lightfield image
# (assuming [0,0] - i.e. frontal - viewpoint).
#
# Usage: pose-extract.py HDF5FILE FRAMENUMBER
#
# Output: A TSV-formatted file with pose control point coordinates
# is printed on stdout: one line per point with the coordinates
# in order "z y x".

# Our algorithm is:
# 1. Convert the original image to a "blob mask" with the body of the
#    worm white and the rest black.
# 2. Sample uniformly random points from the blob as potential backbone
#    control points.
# 3. Create a "rough backbone" by generating a complete graph on top
#    of the control points, generating the minimum spanning tree (weight
#    based on euclidean distances) and then taking the diameter of the
#    MST as the backbone path; drop all points not part of the diameter.
#    The backbone will wiggle around and meander, but it will roughly
#    span the whole (visible) elongated body. This idea comes from
#    Peng et al., Straightening C. elegans Images.
# 4. Annotate each pixel of the blob with the distance and direction
#    of the nearest blob edge.
# 5. Move each point in the _opposite_ direction from the edge so that
#    it maximizes the distance from the edge. This will put all the
#    points within the area of the central axis, but not neccessarily
#    in the right order due to the meandering of the original path.
# 6. Redo the step (3) with the current set and position of control
#    points, generating a good backbone path.
# 7. Perform a filtering step on the path, removing control points
#    which are too close to neighboring control points and inserting
#    additional control points in-between each pair of points (centered
#    to the middle of the worm body, too). This idea also comes from
#    Peng et al.

import math
import random

import numpy
import numpy.ma as ma
import scipy.ndimage as ndimage
import scipy.ndimage.morphology
import hdf5lflib

import networkx as nx

import cv
import cv2
import matplotlib.pyplot as plt
import matplotlib.patches
from matplotlib.path import Path

#various file processing/OS things
import os
import sys
import tables


PROGRESS_FIGURES = False
NUM_SAMPLES = 160
# Minimum distance between path control points; if two control
# points are nearer than this to each other, that is fixed during filtering.
# In a later stage, control points are added at pair mid-points, so
# effective minimum distance at the end of the algorithm may be as
# low as MIN_DISTANCE/2.
MIN_POINT_DISTANCE = 4.


def print_mask(mask):
    """
    A debug print function that prints out a bool array in asciiart.
    """
    for row in mask:
        for item in row:
            sys.stdout.write('#' if item else '.')
        sys.stdout.write('\n')

def edge_dist_if_within(edgedists, coord):
    """
    Return edge distance at a given coord (possibly ma.masked) or
    ma.masked if we are accessing outside of the image.
    """
    if coord[0] < 0 or coord[1] < 0:
        return ma.masked
    try:
        return edgedists[tuple(coord)]
    except IndexError:
        return ma.masked

def display_graph(ax, graph, points):
    verts = []
    codes = []
    for i,j in graph.edges():
        verts.append([points[i][1], points[i][0]])
        codes.append(Path.MOVETO)
        verts.append([points[j][1], points[j][0]])
        codes.append(Path.LINETO)
    path = Path(verts, codes)
    patch = matplotlib.patches.PathPatch(path, facecolor='none', edgecolor='blue', lw=1)
    ax.add_patch(patch)

def display_path(ax, pathlist, points):
    verts = []
    codes = []
    for i in pathlist:
        verts.append([points[i][1], points[i][0]])
        codes.append(Path.LINETO)
    codes[0] = Path.MOVETO
    path = Path(verts, codes)
    patch = matplotlib.patches.PathPatch(path, facecolor='none', edgecolor='green', lw=1)
    ax.add_patch(patch)


def computeEdgeDistances(uvframe):
    """
    Create a 2D matrix @edgedists as a companion to @uvframe,
    containing for each pixel a distance to the nearest edge (more precisely,
    the nearest 0-valued pixel).

    We compute @edgedists in a floodfill fashion spreading from zero-areas
    to the middle of one-areas iteratively, with distances approximated
    on the pixel grid.

    We return a tuple (edgedists, edgedirs), where edgedirs contains information
    about the relative offset of the nearest edge piece.
    """
    # edgedists is a masked array, with only already computed values unmasked;
    # at first, uvframe == 0 already are computed (as zeros)
    edgedists = ma.array(numpy.zeros(uvframe.shape, dtype = numpy.float), mask = (uvframe > 0))
    edgedirs = ma.array(numpy.zeros(uvframe.shape, dtype = (numpy.float, 2)), mask = [[[j,j] for j in i] for i in uvframe > 0])
    #numpy.set_printoptions(threshold=numpy.nan)
    #print edgedists
    #print edgedirs

    flood_spread = scipy.ndimage.morphology.generate_binary_structure(2, 2)
    neighbor_ofs = [[-1,-1],[-1,0],[-1,1], [0,-1],[0,0],[0,1],  [1,-1],[1,0],[1,1]]
    s2 = math.sqrt(2)
    neighbor_dist = [s2,1,s2, 1,0,1, s2,1,s2]

    while ma.getmaskarray(edgedists).any():
        # scan masked area for any elements that have unmasked neighbors
        done_mask = numpy.invert(ma.getmaskarray(edgedists))
        todo_mask = done_mask ^ scipy.ndimage.binary_dilation(done_mask, flood_spread)
        #print_mask(todo_mask)
        for i in numpy.transpose(numpy.nonzero(todo_mask)):
            neighbor_val = ma.array([
                    edge_dist_if_within(edgedists, i + ofs) + dist
                        for ofs, dist in zip(neighbor_ofs, neighbor_dist)
                ])
            nearestnei = ma.argmin(neighbor_val)

            # We assert that this update never affects value other fields
            # visited later in this iteration of floodfill
            edgedists[tuple(i)] = neighbor_val[nearestnei]

            nearestneicoord = i + neighbor_ofs[nearestnei]
            #print "-", nearestneicoord, edgedirs[tuple(nearestneicoord)]
            edgedirs[tuple(i)] = edgedirs[tuple(nearestneicoord)] + tuple(neighbor_ofs[nearestnei])
            #print "+", i, edgedirs[tuple(i)]

    return (edgedists.data, edgedirs.data)

def sampleRandomPoint(uvframe):
    """
    Return a coordinate tuple of a random point with non-zero value in uvframe.
    """
    while True:
        c = (random.randint(0, uvframe.shape[0]-1), random.randint(0, uvframe.shape[1]-1))
        if uvframe[c] > 0:
            return c

def pointsToBackbone(points, uvframe):
    # Generate a complete graph over these points,
    # weighted by Euclidean distances
    g = nx.Graph()
    # Graph vertices are point numbers, except points which are set to None
    nodes = filter(lambda x: points[x] is not None, range(len(points)))
    g.add_nodes_from(nodes)
    for i in range(len(points)):
        if points[i] is None:
            continue
        for j in range(i+1, len(points)):
            # TODO: scipy's cpair? but we will need to construct
            # a graph anyway
            if points[j] is None:
                continue
            g.add_edge(i, j, {'weight': math.pow(points[i][0]-points[j][0], 2) + math.pow(points[i][1]-points[j][1], 2)})

    # Reduce the complete graph to MST
    gmst = nx.minimum_spanning_tree(g)

    # Show the MST
    # f = plt.figure()
    # imgplot = plt.imshow(uvframe, cmap=plt.cm.gray)
    # display_graph(f.add_subplot(111), gmst, points)
    # plt.show()

    # Diameter of the minimum spanning tree will generate
    # a "likely pose walk" through the graph
    tip0 = max(nx.single_source_dijkstra_path_length(gmst, nodes[0]).items(), key=lambda x:x[1])[0] # funky argmax
    (tip1_lengths, tip1_paths) = nx.single_source_dijkstra(gmst, tip0)
    tip1 = max(tip1_lengths.items(), key=lambda x:x[1])[0]
    backbone = tip1_paths[tip1]

    return backbone

def edgedistsInterpolate(edgedists, point):
    """
    2x2 interpolation of distance for non-integer point coordinates.
    """
    beta_y = math.ceil(point[0]) - point[0]
    beta_x = math.ceil(point[1]) - point[1]
    try:
        curdist = (beta_y * beta_x * edgedists[math.floor(point[0]), math.floor(point[1])]
                   + beta_y * (1.-beta_x) * edgedists[math.floor(point[0]), math.ceil(point[1])]
                   + (1.-beta_y) * beta_x * edgedists[math.ceil(point[0]), math.floor(point[1])]
                   + (1.-beta_y) * (1.-beta_x) * edgedists[math.ceil(point[0]), math.ceil(point[1])]) / 4.
    except IndexError:
        return None
    return curdist

def gradientAscent(edgedists, edgedirs, point):
    """
    We want to move the point along the gradient from the edge of the worm
    to the center. However, simple non-guided gradient ascend will obviously
    make all the points converge in some middle point; we do not want to
    move along the A-P axis. Therefore, we instead move _from_ the nearest
    edge.
    Note that points may not have integer coordinates after a gradientAscent.
    """
    bestDist = None
    bestPoint = None
    # From now on, point may be a non-integer; however we always return an int
    max_steps = max(edgedists.shape)
    steps = 0
    while steps < max_steps:
        if point < [0,0] or point >= edgedists.shape:
            # Throw away points that walk out of the picture
            return None
        intpoint = [round(point[0]), round(point[1])]
        curdist = edgedistsInterpolate(edgedists, point)
        if bestDist is not None and curdist < bestDist:
            break
        bestDist = curdist
        bestPoint = point
        if max(abs(edgedirs[tuple(intpoint)])) == 0:
            # We might have been at a ledge, now we are out of the worm; discard
            return None
        walkDir = edgedirs[tuple(intpoint)] / max(abs(edgedirs[tuple(intpoint)]))
        point = [point[0] - walkDir[0], point[1] - walkDir[1]]
        #print ">", bestPoint, bestDist, walkDir, point, curdist
        steps += 1
    return bestPoint

def filterPath(path, points, edgedists, edgedirs, uvframe):
    """
    If two successive points in the path are nearer than MIN_POINT_DISTANCE,
    one of them is removed. Then, an extra point is added inbetween each
    pair of points and gradient-ascended to the middle of the worm.
    """
    # Remove points that are too close
    i = 0
    while i < len(path)-1:
        point0 = points[path[i]]
        point1 = points[path[i+1]]
        distance = (point0[0] - point1[0]) ** 2 + (point0[1] - point1[1]) ** 2
        if distance < MIN_POINT_DISTANCE ** 2:
            # Make sure we never remove the (currently) tip control points
            if i == 0:
                ofs = 1
            elif i == len(path)-1:
                ofs = 0
            else:
                ofs = random.randint(0, 1)
            path.pop(i + ofs)
        else:
            i += 1

    # Insert points in midway
    newpath = []
    for i in range(len(path)-1):
        point0 = points[path[i]]
        point1 = points[path[i+1]]
        point_mid = [round((point0[0] + point1[0]) / 2), round((point0[1] + point1[1]) / 2)]
        point_mid = gradientAscent(edgedists, edgedirs, point_mid)

        points.append(point_mid)
        newpath.append(path[i])
        newpath.append(len(points)-1)
    newpath.append(path[len(path)-1])
    return newpath

def poseExtract(uvframe, edgedists, edgedirs):
    """
    Output a sequence of coordinates of pose curve control points.
    """
    # Pick a random sample of points
    points = [sampleRandomPoint(uvframe) for i in range(NUM_SAMPLES)]

    # Generate a backbone from the points set
    backbone = pointsToBackbone(points, uvframe)
    #print backbone

    # Show the backbone
    if PROGRESS_FIGURES:
        f = plt.figure()
        imgplot = plt.imshow(uvframe, cmap=plt.cm.gray)
        display_path(f.add_subplot(111), backbone, points)
        plt.show()

    # Remove points not used in the backbone path
    for i in list(set(range(len(points))) - set(backbone)):
        points[i] = None

    # Refine points on backbone by fixed-direction gradient ascend
    # over edgedists
    for i in backbone:
        #print "---", i, points[i]
        points[i] = gradientAscent(edgedists, edgedirs, points[i])
        #print "->", points[i]

    # Redo the complete graph - MST - diameter with final graph
    # to get straight tracing
    backbone = pointsToBackbone(points, uvframe)

    # Show the backbone
    if PROGRESS_FIGURES:
        f = plt.figure()
        imgplot = plt.imshow(edgedists)
        display_path(f.add_subplot(111), backbone, points)
        plt.show()

    # Filter the path by removing points too close to each other
    # and inserting points midway (gradient-ascended while at it).
    backbone = filterPath(backbone, points, edgedists, edgedirs, uvframe)

    # Show the backbone
    if PROGRESS_FIGURES:
        f = plt.figure()
        imgplot = plt.imshow(edgedists)
        display_path(f.add_subplot(111), backbone, points)
        plt.show()

    # TODO: Extend tips by slowest-rate gradient descent
    return map(lambda i: points[i], backbone)

def printTSV(backbone):
    for point in backbone:
        print 0, point[0], point[1]

def processFrame(i, node, ar, cw):
    uvframe = hdf5lflib.compute_uvframe(node, ar, cw)

    if PROGRESS_FIGURES:
        plt.figure()
        imgplot = plt.imshow(uvframe, cmap=plt.cm.gray)
        plt.show()

    # Smooth twice
    uvframe = cv2.medianBlur(uvframe, 5)
    uvframe = cv2.medianBlur(uvframe, 5)

    if PROGRESS_FIGURES:
        plt.figure()
        imgplot = plt.imshow(uvframe, cmap=plt.cm.gray)
        plt.show()

    # Threshold
    background_color = uvframe.mean()
    foreground_i = uvframe > background_color
    uvframe[foreground_i] = 255.
    uvframe[numpy.invert(foreground_i)] = 0.

    # Fill holes in "dead" regions of the worm
    uvframe = scipy.ndimage.morphology.binary_fill_holes(uvframe)

    if PROGRESS_FIGURES:
        plt.figure()
        imgplot = plt.imshow(uvframe, cmap=plt.cm.gray)
        plt.show()

    # Annotate with information regarding the nearest edge
    (edgedists, edgedirs) = computeEdgeDistances(uvframe)

    if PROGRESS_FIGURES:
        fig, axes = plt.subplots(ncols = 2)
        axes[0].imshow(uvframe, cmap=plt.cm.gray)
        axes[1].imshow(edgedists)
        plt.show()

    # Determine the backbone
    backbone = poseExtract(uvframe, edgedists, edgedirs)

    # Convert to TSV and output
    printTSV(backbone)

def processFile(filename, frameNo):
    h5file = tables.open_file(filename, mode = "r")
    ar = h5file.get_node('/', '/autorectification')
    cw = h5file.get_node('/', '/cropwindow')
    processFrame(frameNo, h5file.get_node('/', '/images/' + str(frameNo)), ar, cw)
    return True

if __name__ == '__main__':
    filename = sys.argv[1]
    frameNo = int(sys.argv[2])
    if not processFile(filename, frameNo):
        sys.exit(1)
