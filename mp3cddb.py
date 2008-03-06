# Title: MP3 CDDB renamer
# Author: Michael Dove
# Date: 22/09/02


import MP3Info
import sys
from os import listdir, rename
from os.path import splitext
class mp3cddb:
   
    PRESTART = 150 # frames or 2 seconds
    PRESEC = PRESTART / 75
    
    def __init__(self, directory):
	self.directory = directory
	self.length = self.PRESEC
	self.frames = []
	self.tracks = 0
	self.checksum = 0
	frameoffset = self.PRESTART

	dirs = self.getFiles()
	for i in range(len(dirs)):
	    info = self.getMpegInfo(dirs[i])
	    self.frames.append(info[0])
	    self.length += int(round(info[1]))
    	    self.checksum += self.cddb_sum(frameoffset / 75)
	    self.tracks += 1 		# increment num of tracks
	    frameoffset += info[0]
	

    def getFiles(self):
	"Returns a list of all mp3 filenames"	
	dirlist = listdir(self.directory)
	for file in dirlist:
	    name, extension = splitext(file)
	    if extension != '.mp3':
		dirlist.remove(file)
	dirlist.sort()		
	return dirlist	

    def renameMP3(self, oldname, newname):
	"Rename a MP3"
	rename(self.directory +'/'+ oldname, self.directory +'/'+ newname)

    def updateNames(self, names):
	"updates mp3 titles given info retrieved from cddb"

	dirlist = self.getFiles()
	for i in range(len(dirlist)):
	    number = i + 1 
	    title = names['TTITLE%d' %(number - 1)]
	    artists, disc = names['DTITLE'].split('/', 1)
	    artists = artists.strip()
	    disc = disc.strip()
	    extension = splitext(dirlist[i])[1]

	    newname = '%d - %s - %s - %s%s' %(number, disc, artists, title, extension)
	    print newname
	    #self.renameMP3(dirlist[i], newname)
	    
	

	
    def getMpegInfo(self,filename):
	"Get information about MP3"
	track = MP3Info.MP3Info(open(self.directory +'/'+ filename))
	mpeginfo = track.mpeg
	headerlength = mpeginfo.length
	length = ((mpeginfo.filesize) / mpeginfo.framelength) * (mpeginfo.samplesperframe / mpeginfo.samplerate) 
	frames = int(round(length * 75 -6))

	return (frames, length)

    def getcddbformat(self):
	format = []
	format.append(self.getDiscID())
	format.append(self.tracks)
	offset = self.PRESTART
	format.append(offset)
	for i in range(len(self.frames) -1 ):
	    offset += self.frames[i]
	    format.append(offset)
	format.append(self.length)

	return format

    def getDiscID(self):
	discid = ((self.checksum % 0xff) << 24 | int(self.length - self.PRESEC) << 8 | self.tracks)
	return discid

    def cddb_sum(self, n):
	"Calculate checksum"
        sum = 0
	while n > 0:
	    sum = sum + (n % 10)
	    n = n / 10
    	return sum
					
if __name__ == '__main__':
    renamer = mp3cddb(sys.argv[1])
    disc_id = renamer.getcddbformat()

    import CDDB
    (status, info) = CDDB.query(disc_id)

    status2 = None
    info2 = None
    if status == 200:
    	(status2, info2) = CDDB.read(info['category'], info['disc_id'])
    elif status == 210 or status == 211:
	(status2, info2) = CDDB.read(info[0]['category'], info[0]['disc_id'])

    if status == 202:
	print "No Match Found!"
    if info2:
    	renamer.updateNames(info2)
