import hashlib
import numpy
import tables


class H5HashFile:
	#class to process hash
	def __init__(self, filepath):
		self.filepath = filepath
		self.h5file = tables.open_file(filepath, mode="r")
		self.giantArray = numpy.array([]) #creates an emtpy 1D array to hold all data in a file

	def __getData(self):
		for group in self.h5file.walk_groups("/"):
			for array in self.h5file.list_nodes(group,classname='Array'):
				self.giantArray = numpy.append(self.giantArray, array.read().flatten())
		self.h5file.close()

	def __hash(self):
		return hashlib.sha1(self.giantArray.view(numpy.uint8)).hexdigest() #done this way for speed

	def process(self):
		self.__getData()
		return self.__hash()


