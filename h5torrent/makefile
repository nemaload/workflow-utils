all: h5torrent

h5torrent: get_torrent.o h5hashcache.o 
	g++ -o h5torrent get_torrent.o h5hashcache.o -lcurl -ltorrent-rasterbar  -lssl -lcrypto -DBOOST_ASIO_DYN_LINK -DBOOST_FILESYSTEM_VERSION=2 -lboost_system -L /lib64 -lpthread

get_torrent.o: get_torrent.cpp
	g++ -c get_torrent.cpp -ltorrent-rasterbar -lssl -lcrypto -DBOOST_ASIO_DYN_LINK -DBOOST_FILESYSTEM_VERSION=2 -lboost_system -L /lib64 -lpthread

h5hashcache.o: h5hashcache.c
	gcc -c h5hashcache.c -lcurl

clean:
	rm -rf *o torrent_test