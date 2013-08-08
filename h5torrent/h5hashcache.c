//USAGE
// ./h5torrent <hash> [HDF5Cache directory]
/*
cURL COPYRIGHT AND PERMISSION NOTICE
 
Copyright (c) 1996 - 2013, Daniel Stenberg, <daniel@haxx.se>.
 
All rights reserved.
*/
 
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <curl/curl.h>

#include <sys/stat.h>

//declaration of function from C wrapper of libtorrent
int downloadTorrentFile(char*, size_t, char *, bool);

//data structure to hold cURL'd torrent data
struct MemoryStruct {
  char *memory;
  size_t size;
};
 
 //function to write cURL'd data to data structure above
static size_t WriteMemoryCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
  size_t realsize = size * nmemb;
  struct MemoryStruct *mem = (struct MemoryStruct *)userp;
 
  mem->memory = (char *)realloc(mem->memory, mem->size + realsize + 1);
  if(mem->memory == NULL) {
    /* out of memory! */ 
    printf("not enough memory (realloc returned NULL)\n");
    return 0;
  }
 
  memcpy(&(mem->memory[mem->size]), contents, realsize);
  mem->size += realsize;
  mem->memory[mem->size] = 0;
 
  return realsize;
}
//function to fetch torrent data from URL
struct MemoryStruct * getTorrentData(char * url)
{
  CURL *curl_handle;
  CURLcode res;
  struct MemoryStruct* chunk;
  chunk = (struct MemoryStruct *) malloc(sizeof(struct MemoryStruct));
 // struct MemoryStruct chunk;
  chunk->memory = (char *)malloc(1);  /* will be grown as needed by the realloc above */ 
  chunk->size = 0;    /* no data at this point */ 
  curl_global_init(CURL_GLOBAL_ALL);
  curl_handle = curl_easy_init();
  curl_easy_setopt(curl_handle, CURLOPT_URL, url);
  curl_easy_setopt(curl_handle, CURLOPT_WRITEFUNCTION, WriteMemoryCallback);
  curl_easy_setopt(curl_handle, CURLOPT_WRITEDATA, chunk);
  curl_easy_setopt(curl_handle, CURLOPT_USERAGENT, "libcurl-agent/1.0");
  res = curl_easy_perform(curl_handle);
  curl_easy_cleanup(curl_handle);
 
  //curl_global_cleanup(); //this function is NOT thread safe
  return chunk;
}
int main(int argc, char **argv)
{
  if( argc > 3) //check if too many arguments
    return 1;

  char *HDF5Hash = argv[1];
  if (strlen(HDF5Hash) != 40) //length of SHA1 hash
    return 1;
  char *saveDirectory;
  if(argc == 3) //directory supplied
  {
    saveDirectory = argv[2];
    struct stat sb;
    if (!(stat(saveDirectory, &sb) == 0 && S_ISDIR(sb.st_mode)))
      return 1;
  }
  else { //check for environment variable
    char * HDF5CacheDirectory;
    HDF5CacheDirectory = getenv("HDF5CACHE");
    if (!HDF5CacheDirectory)
      return 1;
    else 
      saveDirectory = HDF5CacheDirectory;
  }
  //get the hash prefix and suffix
  char prefix[3];
  memcpy(prefix,HDF5Hash, 2);
  prefix[2] = '\0'; //null terminate the string
  char suffix[39];
  memcpy(suffix,&HDF5Hash[2],39);
  suffix[38] = '\0';

  //now check for file existence
  
  char * baseURL = "https://s3.amazonaws.com/nemaload.data/cache/";
  char torrentURL[120];
  //construct the URL
  strcat(torrentURL, baseURL);
  strcat(torrentURL, "/");
  strcat(torrentURL, prefix);
  strcat(torrentURL, "/");
  strcat(torrentURL, suffix);
  strcat(torrentURL, "?torrent");

  struct MemoryStruct *returnChunk =  getTorrentData(torrentURL);
  if (downloadTorrentFile(returnChunk->memory, returnChunk->size, "", true))
    return 0;
  return 1;
  return 0;
}