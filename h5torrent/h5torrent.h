#ifndef _H5TORRENT_H
#define _H5TORRENT_H
//get the HDF5 with data hash 'hash', and cache it in the path cacheDirectory.
//If no cacheDirectory is specified, it will default to $HDF5CACHE
extern int getTorrent(char *hash, char *cacheDirectory);

#endif