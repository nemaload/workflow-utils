#!/usr/bin/python

import os
import subprocess
import sys
import fnmatch
from xml.dom import minidom
import json

# USAGE
# ./generateRawAndJSON.py [inputFileName] [outputDirectory]

# convenience function to convert string to bool
def parseStringToBool(inputString):
    return ("a" not in inputString)

def processFile(file, outputDirectoryPath):
    # dump XML version of HDF5 file attributes
    child = subprocess.Popen(
        ["h5dump", "-uA", file], stdout=subprocess.PIPE)

    unprocessedXML = child.communicate()[0]  # get the stdout as a string
    returnCode = child.returncode
    if returnCode is not 0:
        print file + " was not successfully processed"
        return False
    xmldoc = minidom.parseString(
        unprocessedXML)  # parse the XML output string

    itemList = xmldoc.getElementsByTagName(
        'Dataset')  # get all datasets in file

    print "Found " + str(len(itemList)) + (" dataset" if (len(itemList) ==1)  else " datasets") + " in file " + file
    for dataset in itemList:
        datasetPath = dataset.attributes[
            "H5Path"].nodeValue  # used in binary image dump
        outputDict = {}
        outputDict["Name"] = dataset.attributes[
            "Name"].nodeValue  # get the name of the dataset
        outputDict[
            "SimpleDataspace"] = {}  # used to hold information about the dataset dimensions
        for childNode in dataset.childNodes:
            if childNode.localName and "Dataspace" in childNode.localName:
                    outputDict["SimpleDataspace"]["Ndims"] = int(
                        childNode.getElementsByTagName("SimpleDataspace")[0].attributes["Ndims"].nodeValue)
                    dimensions = childNode.getElementsByTagName(
                        "Dimension")
                    outputDict["SimpleDataspace"]["Dimension"] = [
                        {"DimSize": int(dimensions[0].attributes["DimSize"].nodeValue)}, {"DimSize": int(dimensions[1].attributes["DimSize"].nodeValue)}]
        dataTypeChildNodes = dataset.getElementsByTagName(
            "DataType")[0].childNodes
        for childNode in dataTypeChildNodes:
            if childNode.localName and "AtomicType" in childNode.localName: #usually IntegerType
                typeChildNodes = childNode.childNodes
                for typeChild in typeChildNodes:
                    if typeChild and typeChild.localName:
                        outputDict["DataType"] = {"Type": typeChild.localName, "ByteOrder": typeChild.attributes["ByteOrder"].nodeValue, "Sign": parseStringToBool(
                                                  typeChild.attributes["Sign"].nodeValue), "Size": int(typeChild.attributes["Size"].nodeValue)}
        outputFilePath = outputDirectoryPath + os.path.basename(file) + "-" + \
            outputDict["Name"] + ".json"  # file to save JSON in
        jsonFile = open(outputFilePath, "w")
        # write the dictionary in JSON form
        jsonFile.write(json.dumps(outputDict))
        jsonFile.close()
        print "Wrote file " + outputFilePath + ". Converting file to binary format..."
        rawFilePath = outputDirectoryPath + os.path.basename(file) + "-" + \
            outputDict[
                "Name"] + ".raw"  # file to save binary image in
        child = subprocess.Popen(["sudo", "h5dump", "-d", datasetPath, "-b", outputDict[
                                 "DataType"]["ByteOrder"], "-o", rawFilePath, file], stdout=subprocess.PIPE)
        out, err = child.communicate()  # [0] is stdout, [1] is stderr
        returnCode = child.returncode
        if returnCode is not 0:
            print rawFilePath + " was not successfully generated."
            print err
            return False
        else:
            print rawFilePath + " was successfully generated."
    return True

if __name__ == '__main__':
    file = sys.argv[1]
    outputDirectoryPath = os.path.normpath(sys.argv[2]) + os.sep
    if not processFile(file, outputDirectoryPath):
        sys.exit(1)
