/*
COPYRIGHT AND PERMISSION NOTICE
 
Copyright (c) 1996 - 2013, Daniel Stenberg, <daniel@haxx.se>.
 
All rights reserved.
*/
 
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <curl/curl.h>

//int downloadTorrentFile(char *torrentData, char *outputPath, bool verbose);

struct MemoryStruct {
  char *memory;
  size_t size;
};
 
 
static size_t
WriteMemoryCallback(void *contents, size_t size, size_t nmemb, void *userp)
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
 
  curl_global_cleanup();
  return chunk;
}
int main(void)
{
  
  struct MemoryStruct *returnChunk =  getTorrentData("https://s3.amazonaws.com/nemaload.data/cache/00/5190f535521cf675c73551b34d74a986b0b50f?torrent");
  if (downloadTorrentFile(returnChunk->memory, "", true))
    return 0;
  return 1;
  return 0;
}