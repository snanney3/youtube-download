#!/usr/bin/env python
'''
Download YouTube videos.

Author:  Stephen Nanney.
Version: 2015-08-16

import urllib
import subprocess # Used for calling external commands.
import os # Used for testing if a certain file name is taken.
import argparse # Handles arguments.
import mechanize # Allows for easy downloading of files. See https://views.scraperwiki.com/run/python_mechanize_cheat_sheet/
import re # Regex
import codecs
import mimetypes # For getting the file extension of the file.
import sys # For printing to standard error.

def main():

    getArguments()

    if args.files:
        getVideosFromFiles()
    else:
        getVideosFromURLs()

'''
Interpret the list of arguments as URLs of the videos to download.
'''
def getVideosFromURLs():
    # No URLs were given on the command line. Get them from user input.
    if len(args.URLs) == 0:
        userInput = raw_input('Please enter one or more YouTube URLs or video IDs:\n')
        args.URLs = userInput.split() # Split by runs of consecutive whitespace.

    # Download every video.
    for i in xrange(len(args.URLs)):

        url = args.URLs[i]

        # If we have just the video ID, create the full URL.
        if (not url.startswith(r'http://')) and (not url.startswith(r'https://')):
            url = r'http://www.youtube.com/watch?v=' + url
            download(url)

        # The argument is a video with a full URL.
        elif re.search(r'watch\?v=', url) or \
             re.search(r'watch\?.*&v=', url) or \
             re.search(r'youtu.be/', url):
            download(url)

        # The argument is a playlist.
        elif re.search('playlist\?list=', url):
            # Get the ID for each video in the playlist.
            playlistURLs = getPlaylistURLs(url)
            # Download each video.
            for j in xrange(len(playlistURLs)):
                download(r'http://www.youtube.com/watch?v=' + playlistURLs[j])

        # We don't know what this is.
        else:
            if not args.quiet:
                print '\nERROR: Confusing argument: ' + url + '\n'

'''
Interpret the list of arguments as local HTML files of the videos to download.
'''
def getVideosFromFiles():
    # No files were given on the command line. Get them from user input.
    if len(args.URLs) == 0:
        userInput = raw_input('Please enter one or more HTML files:\n')
        args.URLs = userInput.split() # Split by runs of consecutive whitespace.

    # Download every video.
    for i in xrange(len(args.URLs)):

        url = 'file://' + os.path.abspath(args.URLs[i])

        download(url)

'''
Download the video at url.
    url - The URL or video ID of the video to download.
'''
def download(url):

    if args.debug or args.superDebug:
        print "URL: " + url

    browser = mechanize.Browser()
    #browser.set_all_readonly(False) # allow everything to be written to
    browser.set_handle_robots(False) # no robots
    browser.set_handle_refresh(False) # can sometimes hang without this
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    try:
        htmlHandle = browser.open(url)
    except mechanize.HTTPError, e:
        if not args.quiet:
            print '\nERROR: HTTP error for ' + url
            print 'Maybe there\'s a 404 error?\n'
        return
    except mechanize.URLError, e:
        if not args.quiet:
            print '\nERROR: mechanize.URLError for ' + url
            print 'Maybe there\'s a network connectivity problem?\n'
        return
        URLError
    videoTitle = browser.title() # Get the title of the video.
    videoTitle = re.sub(' - YouTube$', '', videoTitle) # Get rid of the "- YouTube" bit at the end.
    videoTitle = re.sub(r'\/', r'_', videoTitle) # Replace forward slashes with underscores (because Linux).

    if args.appendId:
        match = re.search(r'[\?&]v=([^&]+)', url)
        if match:
            videoTitle += ' - YouTube ' + match.group(1)

    urlLine = 'no data' # Value kept if no video data is found.

    for currentLine in htmlHandle:
        # Find the line with video urls. They have "url_encoded_fmt_stream_map" in them.
        if '\"url_encoded_fmt_stream_map\"' in currentLine:
            urlLine = currentLine
            break # The same urls are repeated in about 3 lines. We only need one.
                  # We can collect all lines with urls later if they're needed.

    htmlHandle.close()

    # If urlLine is None then we haven't found good data.
    if urlLine == 'no data':
        if not args.quiet:
            print '\nERROR 113: No video data found for ' + url + '\n'
        return

    match = re.search(r'"fmt_list":"([^"]+)"', urlLine)
    if not match: # fmt_list data not found
        fmtListFound = False
        if not args.quiet:
            print '\nERROR NUMBER 112: No fmt_list data found for ' + url + '\n'
    else: # fmt_list data found
        fmtListFound = True
        fmtList = match.group(1)
        # The formats are separated by commas.
        fmtList = fmtList.split(r',')
        fmtListDict = {}
        # The comma-separated items are each separated by back and forward slashes (\/).
        for i in xrange(len(fmtList)):
            fmtList[i] = fmtList[i].split(r'\/')
            fmtListDict[str(fmtList[i][0])] = fmtList[i][1] # Add this data to a dict.

    # Get the adaptive_fmts data. This has the video and audio split up.
    # Remove the beginning of the line. Keep the urls.
    adaptiveFmtLine = re.sub(r'.*"adaptive_fmts":"', '', urlLine)
    # Remove the end of the line. Keep the urls.
    adaptiveFmtLine = re.sub(r'",.*', '', adaptiveFmtLine)

    # Get the normal video formats. Remove the beginning of the line. Keep the urls.
    urlLine = re.sub(r'.*"url_encoded_fmt_stream_map":"', '', urlLine)
    # Remove the end of the line. Keep the urls.
    urlLine = re.sub(r'",.*', '', urlLine)

    # Split the line up into separate video types. These are separated by commas.
    # Each element of this new list will be for a different video size and format.
    videos = urlLine.split(r',')
    adaptiveVideos = adaptiveFmtLine.split(r',')

    # Operate on each video string. # TODO make these two loops one separate function
    for i in xrange(len(videos)):

        # Convert "\u0026" to "&".
        videos[i] = str(videos[i]).decode('unicode-escape')
        #print str(i) + " " + videos[i]

        # The previous decode() step converted '\n' to new lines.
        # Put this all on one line to make future regex operations easier.
        videos[i] = re.sub(r'\n', '', videos[i])

        # The data in each video type string is separated by ampersands.
        # Split by ampersands to make a new list for each element in videos.
        videos[i] = videos[i].split(r'&')

        # Make a dict with the information found from the previous split().
        # This data is name/value pairs separated by equals signs.
        videoDataDict = {}
        for j in xrange(len(videos[i])):
            nameValue = videos[i][j].split(r'=')
            # Add the data to the dict. The first item is the name (key), the second is the value.
            videoDataDict[nameValue[0]] = nameValue[1]

        # Replace our list in videos[i] with the new dict.
        videos[i] = videoDataDict

    # Operate on each video string.
    for i in xrange(len(adaptiveVideos)):

        # Convert "\u0026" to "&".
        adaptiveVideos[i] = str(adaptiveVideos[i]).decode('unicode-escape')

        # The previous decode() step converted '\n' to new lines.
        # Put this all on one line to make future regex operations easier.
        adaptiveVideos[i] = re.sub(r'\n', '', adaptiveVideos[i])

        # The data in each video type string is separated by ampersands.
        # Split by ampersands to make a new list for each element in videos.
        adaptiveVideos[i] = adaptiveVideos[i].split(r'&')

        # Make a dict with the information found from the previous split().
        # This data is name/value pairs separated by equals signs.
        adaptiveVideoDataDict = {}
        for j in xrange(len(adaptiveVideos[i])):
            nameValue = adaptiveVideos[i][j].split(r'=')
            # Add the data to the dict. The first item is the name (key), the second is the value.
            adaptiveVideoDataDict[nameValue[0]] = nameValue[1]

        # Replace our list in adaptiveVideos[i] with the new dict.
        adaptiveVideos[i] = adaptiveVideoDataDict


    # Clean up the values in the dict.
    for i in xrange(len(videos)):

        # Unencode the URL.
        videos[i]['url'] = urllib.unquote(videos[i]['url'])

        # Unencode the fallback_host. This might not be needed.
        #videos[i]['fallback_host'] = urllib.unquote(videos[i]['fallback_host'])

        # Unencode the type data.
        videos[i]['type'] = urllib.unquote(videos[i]['type'])

        # There may be extra stuff in the type data after a semicolon (and maybe an ampersand). Example:
        # video/webm;+codecs="vp8.0,+vorbis"
        # Get rid of this extra data. (Leave video/webm or whatever).
        videos[i]['type'] = re.sub(r'[;&].*', '', videos[i]['type'])

    # Clean up the values in the dict.
    for i in xrange(len(adaptiveVideos)):

        # Unencode the URL.
        adaptiveVideos[i]['url'] = urllib.unquote(adaptiveVideos[i]['url'])

        # Unencode the type data.
        adaptiveVideos[i]['type'] = urllib.unquote(adaptiveVideos[i]['type'])

        # There may be extra stuff in the type data after a semicolon (and maybe an ampersand). Example:
        # video/webm;+codecs="vp8.0,+vorbis"
        # Get rid of this extra data. (Leave video/webm or whatever).
        adaptiveVideos[i]['type'] = re.sub(r'[;&].*', '', adaptiveVideos[i]['type'])

    # Print every element.
    if args.superDebug:
        for i in xrange(len(videos)):
            print videos[i]
        for i in xrange(len(adaptiveVideos)):
            print adaptiveVideos[i]

    numNormalVideos = len(videos)

    # If any of these arguments are set, then we skip user input.
    skipInput = args.maxQuality or args.minQuality or args.maxMP4 or args.minMP4

    if (not skipInput) or args.debug or args.superDebug:
        # Print out the options.
        print '----------------------------------------------'
        print ' # :  ID :        TYPE  : QUALITY : DIMENSIONS'
        print '----------------------------------------------'
        for i in xrange(len(videos)):
            print '%2d : %3s : %12s : %7s : %s' % (1 + i, videos[i]['itag'], \
                videos[i]['type'], videos[i]['quality'], \
                
                fmtListDict[str(videos[i]['itag'])] if fmtListFound else '???')
        print '' # Print a newline.

    if (not skipInput) or args.debug or args.superDebug:
        # Print out the options.
        # I use the get() function for when a certain key might not exist. It offers a default value.
        print '-------------------------------------------------------------------------'
        print ' # :  ID :        TYPE  :      SIZE : FPS :  BITRATE :     INDEX :   INIT'
        print '-------------------------------------------------------------------------'
        for i in xrange(len(adaptiveVideos)):
            print '%2d : %3s : %12s : %9s : %3s : %8s : %9s : %6s' \
                % (1 + i + numNormalVideos, adaptiveVideos[i]['itag'], \
                adaptiveVideos[i]['type'], \
                adaptiveVideos[i].get('size', '-'), \
                adaptiveVideos[i].get('fps', '-'), \
                adaptiveVideos[i]['bitrate'], \
                adaptiveVideos[i]['index'], \
                adaptiveVideos[i]['init'])
        print '' # Print a newline.

    # Concatenate both lists.
    allFormats = videos + adaptiveVideos

    if not skipInput:
        videoNum = getVideoNumInput(len(allFormats))
    else:
        videoNum = getAutoVideoNum(videos) # TODO make the "highest quality" option check the adaptive formats

    if videoNum > len(videos) and args.combine: # The video is from the adaptive formats list.
        # Find audio to dowload.
        if allFormats[videoNum - 1]['type'].startswith('audio/'):
            sys.stderr.write('ERROR: Select a video file first and an audio file will be selected for it.\n')
            return
        matchinAudioFormat = 'audio/mp4' # Default format.
        if allFormats[videoNum - 1]['type'] == 'video/webm': matchinAudioFormat = 'audio/webm' # Match webm video with webm audio
        for i in xrange(len(allFormats)):
            if allFormats[i]['type'] == matchinAudioFormat:
                audioNum = i + 1 # The first matching audio. TODO: We should search by highest bitrate. It's not in descending bitrate order for the webm audio for video fhdIYS2gOBU
        fullAudioUrl = allFormats[audioNum - 1]['url']

    # Find a good file extension for the file.
    extension = mimetypes.guess_extension(allFormats[videoNum - 1]['type'], strict=False)

    if extension is None:
        extension = ".VIDEO"

    fileName = videoTitle + extension

    # Check to see if we're about to overwrite something.
    suffixNum = 1
    while os.path.exists(fileName) and not args.overwrite:
        if args.promptName: # Ask the user for a file name.
            print '\nFile name collision: ' + fileName
            fileName = raw_input('Enter a new file name (without the extension): ') + extension
        else: # not args.promptName
            # Use the same way to deal with file name collisions as wget.
            fileName = videoTitle + '.' +  str(suffixNum) + extension
            suffixNum += 1

    # Add the fallback_host to the url to download.
    fullUrlDict = allFormats[videoNum - 1]
    
    # Download the video with the browser from above (unless we're doing a simulation).
    if not args.simulate:
        if videoNum <= len(videos) or not args.combine: # The video is not from the adaptive formats or we don't want to combine video and audio.
            if args.debug or args.superDebug:
                print 'Downloading video number: ' + str(videoNum)
                print 'Downloading video url: ' + fullUrl
            if not args.quiet:
                print 'Saving file: ' + fileName
            browser.retrieve(fullUrl, fileName)

        else: # The video is from the adaptive formats list. We have to get the audio and add it to the video.
            # Make /tmp files to save the video and audio to. Make sure to strip
            # the newline from the output of mktemp.
            tempVideo = subprocess.check_output(["mktemp", '-t', \
                'youtube-get.py_video_XXXXXX'], \
                stdin=None, stderr=None, shell=False).rstrip('\n')
            tempAudio = subprocess.check_output(["mktemp", '-t', \
                'youtube-get.py_audio_XXXXXX'], \
                stdin=None, stderr=None, shell=False).rstrip('\n')

            if args.debug or args.superDebug:
                print 'Downloading video number: ' + str(videoNum)
                print 'Downloading video url: ' + fullUrl
            if not args.quiet:
                print 'Saving temporary video: ' + tempVideo
            browser.retrieve(fullUrl, tempVideo)

            if not args.quiet: # Show the audio number even without --debug since it's automatically selected and the user won't know what it is otherwise.
                print 'Downloading audio number: ' + str(audioNum)
            if args.debug or args.superDebug:
                print 'Downloading audio url: ' + fullAudioUrl
            if not args.quiet:
                print 'Saving temporary audio: ' + tempAudio
            browser.retrieve(fullAudioUrl, tempAudio)

            if not args.quiet:
                print 'Combining files with ffmpeg: ' + fileName
            ffmpegReturn = subprocess.check_call(["ffmpeg", \
                '-i', tempVideo, '-i', tempAudio, '-vcodec', 'copy', \
                '-acodec', 'copy', fileName, '-loglevel', 'warning'], \
                stdin=None, stdout=None, stderr=None, shell=False)
            
            if not args.quiet:
                print 'Removing temporary files.'
                os.remove(tempVideo)
                os.remove(tempAudio)


'''
Get a list of every video ID in a playlist.
    playlistURL - The URL of the playlist.
    returns the list of every video ID in the playlist.
'''
def getPlaylistURLs(playlistURL):

    videos = []

    browser = mechanize.Browser()
    #browser.set_all_readonly(False) # allow everything to be written to
    browser.set_handle_robots(False) # no robots
    browser.set_handle_refresh(False) # can sometimes hang without this
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
    htmlHandle = browser.open(playlistURL)

    for currentLine in htmlHandle:
        # Find a line with a video ID. They have "data-video-ids=" in them.
        match = re.search(r'data-video-ids="([^"]+)"', currentLine)
        if match:
            videos.append(match.group(1)) # This group is the video ID.

    htmlHandle.close()

    # No videos were found.
    if len(videos) == 0 and not args.quiet:
        print 'WARNING: No videos found in playlist at:\n' + playlistURL

    return videos

'''
Get user input for the video to download.
    numOptions - The number of video options available.
    returns the number of the video to download.
'''
def getVideoNumInput(numOptions):

    print 'Enter the number (1 through ' + str(numOptions) + ') of the video you want to download:'

    needInput = True
    while needInput: # Keep trying until the user enters a valid number.

        # Get input.
        # raw_input always returns strings.
        userInput = raw_input()

        # isdigit() returns true if it's composed of only digits (i.e. it's a nonnegative integer).
        if userInput.isdigit():
            videoNum = int(userInput) # Convert the string to an int.

            # Keep trying if it's out of range.
            if videoNum < 1 or videoNum > numOptions:
                print 'Please enter an integer between 1 and ' + str(numOptions) + '.'
            else:
                # Quit the while loop if it's in range.
                needInput = False # Quit the while loop if it's in range.

        else: # The number is either negative or not an integer.
            try:
                int(userInput) # If this works then it's a valid negative integer.
            except ValueError: # Non-integer.
                print 'Please enter an integer.'
            else: # Valid negative integer.
                print 'Please enter an integer between 1 and ' + str(numOptions) + '.'

    return videoNum

'''
Automatically choose a video to download based on the command line options.
    videos - A list of video data. Each element is a dict that represents
             one type of video.
             The keys of the dict are:
             itag, url, quality, fallback_host, and type

    returns the number of the video to download.
'''
def getAutoVideoNum(videos):

    validVideos = []
    # Get the highest quality video.
    if args.maxQuality:
        return 0 + 1 # The videos are numbered starting with 1.

    # Get the lowest quality video.
    elif args.minQuality:
        return len(videos)

    # Get the highest quality MP4 video.
    elif args.maxMP4:
        for i in xrange(len(videos)):
            # The video is an MP4.
            if videos[i]['type'] == 'video/mp4':
                return i + 1 # Return the first (highest quality) MP4 video.

    # Get the lowest quality MP4 video.
    elif args.minMP4:
        for i in xrange(len(videos)):
            # The video is an MP4.
            if videos[i]['type'] == 'video/mp4':
                validVideos.append(i)
        # Return the last (lowest quality) MP4 video. 
        return validVideos[len(validVideos) - 1] + 1

    else:
        print 'ERROR NUMBER 111: NO CORRECT OPTION SELECTED.'
        videoNum = 1

    return videoNum

'''
Set up argparse and get the arguments.
'''
def getArguments():

    # Use argparse to deal with arguments.
    parser = argparse.ArgumentParser(description='Download YouTube videos.', \
        epilog='Note that you should put two hyphens (--) before the list of URLs so that URLs that start with a hyphen aren\'t interpreted as command-line options.')
    # Have zero or more urls.
    parser.add_argument('URLs', metavar='URL', nargs='*', \
                       help='A YouTube video URL or ID string.')

    # Optional arguments.

    # Simulate download.
    parser.add_argument('-s', '--simulate', dest='simulate', \
        action='store_true', help='Simulate download, but don\'t actually download anything.')

    # Download videos from local HTML files.
    parser.add_argument('-f', '--files', dest='files', \
    action='store_true', help='Download the videos found in local HTML files. With this option each argument should be the name of an HTML file from YouTube instead of a URL.')

    # Append the video ID to the saved file.
    parser.add_argument('-i', '--append-id', dest='appendId', \
    action='store_true', help='Append the video ID to the saved file. It is in the format " - YouTube xxxxxxxxxxx".')

    # Automatically download and combine videos that are split up into separate audio and video files.
    parser.add_argument('-c', '--combine', dest='combine', \
        action='store_true', help='Automatically download combine videos that are split up into separate audio and video files.\nNOTE: The bitrate seems to be better for a single video with audio built in than for a split-up video of the same resolution. Download complete videos if possible.')


    # Name collision options.
    nameGroup = parser.add_mutually_exclusive_group()
    nameGroup.add_argument('-O', '--overwrite', dest='overwrite', \
        action='store_true', help='Overwrite existing files.')
    nameGroup.add_argument('-n', '--prompt-name', dest='promptName', \
        action='store_true', help='Prompt for file names in the event of collision. The default behavior is to add a number to the end of the name.')

    # Quality options.
    qualityGroup = parser.add_mutually_exclusive_group()
    qualityGroup.add_argument('-M', '--max-quality', dest='maxQuality', \
        action='store_true', help='Download the highest quality video without user input. This is usually or always a webm video.')
    qualityGroup.add_argument('-m', '--min-quality', dest='minQuality', \
        action='store_true', help='Download the lowest quality video without user input. This is usually or always a 3gpp video.')
    qualityGroup.add_argument('-P', '--max-mp4', dest='maxMP4', \
        action='store_true', help='Download the highest quality mp4 video without user input.')
    qualityGroup.add_argument('-p', '--min-mp4', dest='minMP4', \
        action='store_true', help='Download the lowest quality mp4 video without user input.')

    # Output options.
    outputGroup = parser.add_mutually_exclusive_group()
    outputGroup.add_argument('-q', '--quiet', dest='quiet', \
        action='store_true', help='Don\'t print anything unless input is needed.')
    outputGroup.add_argument('-d', '--debug', dest='debug', \
        action='store_true', help='Print out a bunch of data.')
    outputGroup.add_argument('-D', '--super-debug', dest='superDebug', \
        action='store_true', help='Print out way too much data.')

    # Make the arguments global so we can later see the options set.
    global args
    # Read the arguments.
    args = parser.parse_args()

if __name__ == '__main__':
    main()
