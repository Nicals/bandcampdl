#!/usr/bin/python
#
##################################################################
#
# THE BEER-WARE LICENSE" (Revision 42):
# nicolas.appriou@gmail.com wrote this file. As long as you retain
# this notice you can do whatever you want with this stuff. If we
# meet some day, and you think this stuff is worth it, you can buy
# me a beer in return.
#
##################################################################
#
# Quick and dirty script to automatically download album on bandcamp
# Should work when the album is fully downloadable, dunno what happens
# in other case.
# The url to put on the command line argument is the link to listen
# the the album.
# Using this script should be perfectly legal since it only download
# files that are used for streaming preview.
#
# Still lot of things to do:
#    + handle the case when an album is not fully listenable
#    + handle the case when an audio file can be freely downloadable
#      (not the streaming case)
#    + select file format when available (for now, only mp3 is downloaded
#      and bandcampdl tries to get the better quality.
#    + download an album from a random page
#    + audio file metadata
#
# Let me know if you find any problem on this.
#

import argparse
import json
import re
import time
import datetime
import urllib2
import os
import sys

def get_url_response(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0')

    return urllib2.urlopen(req)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bandcamp album downloader')
    parser.add_argument('-u', '--url', type=str, required=True, help='Url to bandcamp album')
    parser.add_argument('-o', '--output', type=str, required=False, default=os.getcwd(), help='Output directory')
    parser.add_argument('-a', '--artist', type=str, required=False, default='%(artist)s', help='Artist directory format string')
    parser.add_argument('-b', '--album', type=str, required=False, default='%(release_year)4d - %(album)s', help='Album directory format string')
    parser.add_argument('-t', '--track', type=str, required=False, default='%(track_num)02d - %(track_title)s', help='Track filename format strint')

    args = parser.parse_args()

    url = args.url

    result = get_url_response(url).read()

    # recover artist and album information
    album_data_regex = re.compile(r'current\s*:\s*(\{.*\}),\s*is_preorder')
    m = album_data_regex.findall(result)
    album_definition = json.loads(m[0])

    album_format_args = {
        'artist':album_definition['artist'],
        'type':album_definition['type'],
        'release_year':datetime.datetime.strptime(album_definition['release_date'], '%d %b %Y %H:%M:%S %Z').year,
        'album':album_definition['title'],
    }

    # prepare directory to download tracks
    album_dirpath = os.path.join(os.path.abspath(args.output), args.artist % album_format_args, args.album % album_format_args)
    try:
        os.makedirs(album_dirpath, 0755)
    # if the directory already exists
    except OSError, e:
        # errno = 17 if the directory already exists
        if e.errno != 17:
            raise
    print ('downloading %(artist)s album (%(album)s) in ' + album_dirpath) % album_format_args

    # get tracks
    trackinfo_regex = re.compile(r'trackinfo\s*:\s*(\[.+\]),\s*playing_from')
    m = trackinfo_regex.findall(result)

    block_size = 512

    for track_definition in json.loads(m[0]):
        # track_definition contains the following keys:
        #   unreleased_track: dunno
        #   lyrics: no need
        #   free_album_download: need example
        #   is_downloadable: need to find one
        #   private: dunno
        #   has_info: dunno
        #   track_num: obvious
        #   file: url of file in a dict <format>:<url>
        #   duration: no need
        #   encoding_id: no need
        #   id: no need
        #   encoding_error: dunno, may be needed
        #   title: obvious
        #   has_lyrics: no need
        #   encoding_pending: dunno
        #   sizeof_lyrics: no need
        #   album_preorder: no need
        #   is_draft: dunno, may be needed
        #   streaming: dunno, think it is used as a boolean
        #   download_tooltop: dunno
        #   title_link: dunno, may be usefull
        #   license_type: may be usefull
        #   has_free_download: dunno
        #
        album_format_args['track_num'] = track_definition['track_num']
        album_format_args['track_title'] = track_definition['title']

        # get highest mp3 quality
        urls = track_definition['file']
        file_url = sorted([urls[a] for a in urls.keys() if 'mp3' in a])[0]

        response = get_url_response(file_url)
        total_size = int(response.info().getheader('Content-Length').strip())
        current_size = 0

        start_time = int(round(time.time() * 1000))

        filename = args.track % album_format_args
        f = open(os.path.join(album_dirpath, filename), 'wb')

        while True:
            chunk = response.read(block_size)

            if not chunk:
                break

            current_size += len(chunk)
            f.write(chunk)

            diff_time = int(round(time.time() * 1000)) - start_time
            dl_speed = (1000. * (float(current_size) / 1024.) / diff_time) if diff_time else 0.

            sys.stdout.write('\r%s - %02.2f%% [%06.2fkio/s]' % (filename, (100 * float(current_size) / total_size), dl_speed))
            sys.stdout.flush()

        sys.stdout.write('\n')

        f.close()

