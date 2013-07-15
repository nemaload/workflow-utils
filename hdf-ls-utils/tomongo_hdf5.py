#!/usr/bin/python
#
# Usage: tomongo_hdf5.py FILENAME
#
# Example: ./tomongo_hdf5.py 16_4-15_27.hdf5

import os
import sys

import tables
import pymongo
import bson


filename = sys.argv[1]
basename = os.path.basename(filename)

h5file = tables.open_file(filename, mode = "r")

mongo = pymongo.Connection('localhost', 3002)
db = mongo.meteor
Images = db.images

if Images.find({'relPath': basename + '/0/0'}).count() > 0:
    print 'Duplicate: ' + basename
    sys.exit(1)

imageObject = {
    # We go to extra lengths to make sure _id is not of type ObjectId
    # which would be painful for Meteor.
    '_id': str(bson.objectid.ObjectId()),

    'type': 'ls',
    'originalPath': os.path.abspath(filename),
    'baseName': basename,
    'size': os.stat(filename).st_size,
    'folderId': db.folders.find({'name':'Unsorted'})[0]['_id'],
    'numFrames': 0,
    'channels': [],
    'relPath': []
}

channel_list = [i for (i, node) in h5file.get_node('/', '/images')._v_children.items()]
channel_list.sort()
for ch in channel_list:
    group_list = [i for (i, node) in h5file.get_node('/', '/images/' + ch)._v_children.items()]
    group_list = map(int, group_list)
    group_list.sort()

    chno = ch[len(".ch"):]
    imageObject['channels'].append(chno)

    imageObject['numFrames'] += len(group_list)
    imageObject['relPath'].extend([basename + '/' + chno + '/' + str(g) for g in group_list])

print imageObject['relPath'][0] + ' ...'
print Images.insert(imageObject)
