#include <iostream>
#include <fstream>
#include <iterator>
#include <exception>

#include <boost/format.hpp>
#include <boost/date_time/posix_time/posix_time.hpp>

#include "libtorrent/entry.hpp"
#include "libtorrent/bencode.hpp"
#include "libtorrent/session.hpp"


#include <cstring>
#include <pthread.h>

extern "C" {
        int downloadTorrentFile(char *torrentData, char *outputPath, bool verbose)
        {
                using namespace libtorrent;
                try {

                        session s;
                        s.listen_on(std::make_pair(6881, 6889));
                        //may need to add 1 to strlen to account for null character

                        entry e = bdecode(torrentData, torrentData + strlen(torrentData)); 
                        //s.add_torrent(torrent_info(e), "");
                        torrent_handle currentHandle = s.add_torrent(torrent_info(e), outputPath);
                        //repeat occasional status in verbose mode
                        if (verbose)
                        {
                                while (! currentHandle.is_seed() ) {
                                        torrent_status currentStatus = currentHandle.status();
                                        std::cout << "Download Rate " << currentStatus.download_rate << std::endl;
                                        //may cause issues if it suspends the session
                                        sleep(3);
                                }
                        }
                        return 0;
                }
                catch (std::exception& e)
                {
                        std::cout << e.what() << "\n";
                        return 1;
                }
        }
}

