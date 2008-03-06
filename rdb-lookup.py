#!/usr/bin/env python

# rdb-lookup.py
# version 0.1  (August 8 2006)
# lookup an mp3's info on rolldabeats.com and stick it back in
# Jamie Wilkinson <jamie@tramchase.com>
#
# tries pretty hard to find you the best match
# prefers LP's over CD's
# looks up label, catalogue #, release date, and "comments"
# TODO: also add it to your RDB "Collection"


# some stuff we want...

import re, sys, urllib, htmllib
from os import listdir, rename
from os.path import splitext
from operator import itemgetter     # requires python 2.4... sorry
from yaml import *                  # requires PyYaml    
from ID3 import *                   # requires id3py
from HTMLParser import HTMLParser   # requires HTMLParser
import traceback


# parses the search page results, grabbing the cool stuff

class rdbPageParser(HTMLParser):
        
    def __init__(self):
        HTMLParser.__init__(self)

        self.matches = []
        self.groupOpen = 0
        self.headerOpen = 0
        self.matchOpen = 0
        self.match = ''
        self.matchType = 'uninitialized'
        self.aOpen = 0  # relatively unused, should delete if all else is working
        self.aAttrs = []

    def handle_starttag(self, tag, attrs):
#        print "Encountered the beginning of a %s tag" % tag
        if(tag == 'h3'):
#            print "@@@@@@@@@@@ start capturing HEADER & GROUP"
            self.groupOpen = 1
            self.headerOpen = 1
            self.commit_match()  # hackish, commit any pending matches...
            
        elif(tag == 'a' and self.groupOpen is 1):
            # this is because the title is captured outside the 
#            print "@@@@@@@@@@@ start capturing A"
            self.aOpen = 1
            self.a = ''
            self.aAttrs.append(attrs[0])
            
#            print "ATTRS:"
#            print attrs[0]

            
    def handle_endtag(self, tag):
        #print "Encountered the end of a %s tag" % tag
        if(tag == 'h3' and self.headerOpen == 1):
#            print "########### stop capturing HEADER"
            self.headerOpen = 0
        elif(tag == 'p' and self.groupOpen == 1):
#            print "########### stop capturing GROUP\n\n"
            self.groupOpen = 0
            self.commit_match();
        elif(tag == 'a' and self.aOpen == 1):
#            print "########### stop capturing A"
            pass
            
    def handle_data(self, text):
        if(self.headerOpen == 1):
#            print "!!!!!!!!!!  header data: '" + text + "'"
            if(re.search('^Releases', text)):
#                print "MATCHING Releases"
                self.matchType = 'release'
            elif(re.search('^Tracks', text)):
#                print "MATCHING Tracks"
                self.matchType = 'track'                
            elif(re.search('^Artists', text)):
#                print "MATCHING Artists"
                self.matchType = 'artist'
            else:
                print "MATCHING ??? (unknown)"
                self.matchType = 'unknown'
                
        elif(self.groupOpen == 1):
            #print "!!!!!!!!!!!  data: '"+text+"'"
            # store said match
            if(re.search('^\n', text)):
                #print "******************* THIS IS A NEWLINE, END MATCH ********************"
                self.commit_match()
            # otherwise append it
            else:
                self.match += text

    def commit_match(self):
        if(self.match == ''):
            return            
        #print "commiting:"
        #print self.matchType
        #print self.match
        self.matches.append( { 'type': self.matchType, 'match': self.match, 'link':self.aAttrs } )
        self.match = ''
        self.aAttrs = []

    def get_matches(self):
        return self.matches


# calculate # of operations to convert string a to string b
def distance(a,b):
    c = {}
    n = len(a); m = len(b)

    for i in range(0,n+1):
        c[i,0] = i
    for j in range(0,m+1):
        c[0,j] = j

    for i in range(1,n+1):
        for j in range(1,m+1):
            x = c[i-1,j]+1
            y = c[i,j-1]+1
            if a[i-1] == b[j-1]:
                z = c[i-1,j-1]
            else:
                z = c[i-1,j-1]+1
            c[i,j] = min(x,y,z)
    return c[n,m]


#
#   main loop
#   RUN TUNE!
#
                    
if __name__ == '__main__':

    try:
        file = sys.argv[1]
    except:
        file = "/Users/jamie/Music/iTunes/iTunes Music/Calyx/Radio Rips #8/Leviathan.mp3"
        
    try:
        id3info = ID3(file)
        #print id3info
        title = id3info['TITLE'].strip()
        artist = id3info['ARTIST'].strip()
    except InvalidTagError, message:
        print "Invalid ID3 tag:", message

    
    print "Title: " + title
    print "Artist: " + artist
      
    useTitle = 1
    if(useTitle):
        meat = title
        meatQuery = 'title'
    else:
        meat = artist
        meatQuery = 'artist'
        
        
    url_data = string.lower(meat).replace(' ', '/')
    data = urllib.urlencode({"find" : "XMLForms", "findtype" : "t"})
    url = "http://www.rolldabeats.com/search/" + meatQuery + "/" + url_data
    #print "Fetching url: " + url
    try:
        f = urllib.urlopen(url, data)
        s = f.read()
    except:
        raise "Can't open URL " + url + ". Are you connected to the internets?"
        sys.quit()
        
    
    # start parsing said object
    htmlparser = rdbPageParser()
    htmlparser.feed(s)
    htmlparser.close()
    

    matches = htmlparser.get_matches()
    #print "[MATCHES]"
    #print yaml.dump(matches)    
    
    # ok split the "match" strings and find one that looks like ours
    goodMatches = []
    for match in matches:
        if match['type'] is 'track':
            # find the 'release' link
            for link in match['link']:
                if re.search( '/release/', link[1] ):
                    
                    # is this our artist & title?
                    try:
                        groups = []
                        try:
                            pattern = re.compile(r'(.*) - (.*) \((.*) - (.*)\).*$')
                            groups = pattern.search(match['match'].strip()).groups()
                        except:
                            print "ERROR: could not get regex groups... "
                            print match['match']
                            print groups
                            print traceback.print_exc()
 
                        
                        gArtist = groups[0].strip()
                        gTitle = groups[1].strip()
                        gLabel = groups[2].strip()
                        gRelease = groups[3].strip()

                        # calculate how close this is to what we want
                        # lower number means chars are closer to identical (good)
                        accuracy = 0.0
                        '''
                        if(gArtist == artist):
                            accuracy += 5
                        if(gTitle == title):
                            accuracy += 5
                        '''
                        
                        try:
                            accuracy += float(len(artist)) / float(distance(artist, gArtist))
                        except ZeroDivisionError:
                            pass

                        try:
                            accuracy += float(len(title)) / float(distance(title, gTitle))
                        except ZeroDivisionError:
                            pass

                        if(gRelease.find("CD") > 0):
                            accuracy += 0.01   # just enough to bump it relative to an LP, but not too much

                        # sure, go ahead and add it
                        goodMatches.append( { 'artist': gArtist, \
                                            'title': gTitle, \
                                            'label': gLabel, \
                                            'release': gRelease, \
                                            'link': link[1], \
                                            'accuracy': accuracy \
                                            } )    
                    except:
#                        print "Matching process threw an exception!"
#                        traceback.print_exc()
                        continue
                        
                        

    # grab the best match based on accuracy score
    result = sorted(goodMatches, key=itemgetter('accuracy'))
    try:
        # grab 1st match since lowest accuracy is the best
        bestMatch = result[0]
    except:  # KeyError, IndexError ?
        print "NO MATCHES!"
        sys.exit()
    
    
    # debug
    #print "good Matches"
    #print goodMatches

    print "\nBest match:"
    print bestMatch
    
    # folllow its link
    url = "http://rolldabeats.com" + bestMatch['link']
    #print "Fetching url: " + url
    try:
        data = urllib.urlencode({"find" : "XMLForms", "findtype" : "t"})
        f = urllib.urlopen(url, data)
    except:
        raise "Can't open website. Are you connected to the internets?"
        sys.quit()

    # find the parts we want
    for line in f:
#        print "line: " + line
        if(line.find('Label:') > 0):
            #print "LABEL: " + line
            parts = line.split('>')
            newLabel = parts[1][:-3]
            
        elif(line.find('Catalogue:') > 0):
            #print "CATALOGUE #: " + line
            parts = line.split(':')
            newCatalogue = parts[1].strip()[:-6]

        elif(line.find('Release Date:') > 0):
            #print "RELEASE DATE: " + line
            parts = line.split(':')
            newReleaseDate = parts[1].strip()[:-5]

        elif(line.find('Comment:') > 0):
            #print "COMMENT: " + line
            parts = line.split(':')
            newComment = parts[1].strip()[:-6]
            if(newComment == "None"):
                newComment = ""
            
        
        # wishlist / collection stuff            
        elif(line.find('release_id') > 0):
            print "release_id: " + line
        elif(line.find('COLLECTION') > 0):
            print "COLLECTION: " + line


    print
    #print "RETRIEVED___"
    print "Label: " + newLabel                        
    print "Catalogue #: " + newCatalogue
    print "Release date: " + newReleaseDate
    newYear = newReleaseDate[-4:]
    print "Year guess: " + newYear
    print "\"Comment\": " + newComment

    if bestMatch['accuracy'] < 0.1:
        print "\n" + "*** writing ***"
#        id3info.label = newLabel
#        id3info.year = newYear
#        if(id3info.album.strip() == ""):   # make album the label + catalogue if blank, put that stuff in the comment otherwise
#            id3info.album = newLabel + " " + newCatalogue
#        else:
#            newComment += "  catalogue: " + newCatalogue + " release date: " + newReleaseDate

        # for now we are ignoring prev comment... careful!
    #    id3info.comment = id3info.comment + "  catalogue: " + newCatalogue + " " + newComment
#        if not id3info.comment.find('catalogue'):
#            id3info.comment = id3info.comment + "catalogue: " + newCatalogue + " " + newComment
#        elif id3info.comment.find('WROTE'):
#            id3info.comment = "Cat#: " + newCatalogue + " " + newComment
        
#        id3info.write()
    
#        print id3info
    else:
        print "Sorry, low accuracy"
        print bestMatch

   
'''
# collection stuff... be cool to post up this info too
<form id="collection_add" title="Add 1 item to collection" method="post" action="/alter_collection.php">
  <input type="hidden" name="action" value="add" />
  <input type="hidden" name="release_id" value="24474" />
  <input class="submit" type="submit" name="add" value="Add" title="Add to collection" />
</form>
'''
    
    
