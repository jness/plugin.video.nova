import xbmc, xbmcgui, xbmcplugin, xbmcaddon
import base64
import sys
import datetime
import urllib2
import simplejson
import re
import coveapi

__plugin__ = "NOVA"
__author__ = 'Jeffrey Ness <jness@flip-edesign.com>'
__date__ = '04-16-2013'
__version__ = '0.1'


class Nova(object):
    """Simple Class for Getting NOVA Episodes from CoveAPI"""

    def __init__(self):
        user = 'eGJtYy01ZGYyNjgwMC0zYTUzLTRlZjQtODQxNy1jODJkYTM2ZTVhYzQ='
        token = 'ZjNlNzM0NzEtZWNkNC00MmI2LWJmNGUtZmJkNGQ4MzFmYjQx'
        self.__cove = coveapi.connect(base64.b64decode(user),
                                      base64.b64decode(token))
        self.__id = self.__cove_nova_id()
        self.__episodes = self.__cove_nova_episodes()

    @property
    def id(self):
        return self.__id

    @property
    def episodes(self):
        return self.__episodes

    def __len__(self):
        return len(self.__episodes)

    def __cove_nova_id(self):
        """Gets the NOVA program ID"""
        data = self.__cove.programs.filter(filter_nola_root='NOVA')
        if data['count'] == 1:
            uri = data['results'][0]['resource_uri']
            match = re.search('/cove/v1/programs/(\d*)/', uri)
            if match:
                return match.group(1)
            xbmcgui.Dialog().ok('Error', 'Unable to determine Nova program id')
            raise Exception()
        xbmcgui.Dialog().ok('Error', 'We should of only found 1 program...')
        raise Exception()

    def __cove_nova_episodes(self):
        """Gets latest NOVA Episodes"""
        pid = self.id
        kwargs = dict(fields='associated_images,mediafiles',
                      filter_producer__name='PBS',
                      filter_program=pid,
                      order_by='-airdate',
                      filter_availability_status='Available',
                      filter_type='Episode')
        filters = dict(**kwargs)
        data = self.__cove.videos.filter(**filters)
        return data['results']


def __get_length(episode):
    """Going to get the first streams length..."""
    mseconds = int(episode['mediafiles'][0]['length_mseconds'])
    return datetime.timedelta(milliseconds=mseconds)


def __get_thumbnail(episode):
    return [i for i in episode['associated_images']
            if i['type']['eeid'] == 'ThumbnailCOVEDefault'][0]['url']


def __select_mp4_stream(episode):
    """Ask the user which mp4 they wish to play and return direct link"""
    videos = []
    for media in episode['mediafiles']:
        if media['video_encoding']['mime_type'] == 'video/mp4':
            videos.append(media)
    dia = xbmcgui.Dialog()
    video_id = dia.select('Pick Quality',
                         [i['video_encoding']['name'] for i in videos])
    video = videos[video_id]['video_download_url']

    # use our download link to get full mp4 path
    res = urllib2.urlopen(video + "?format=json").read()
    data = simplejson.loads(res)
    if data['status'] == "ok":
        return data['url']
    xbmcgui.Dialog().ok('Error', 'Request to %s returned %s' %
                                 (video, data['status']))
    raise Exception()


def showEpisodes(minutes=30):
    """Build a XBMC List of Episodes"""
    nova = Nova()
    for episode in nova.episodes:
        if __get_length(episode) > datetime.timedelta(minutes=minutes):
            title = episode['title'].encode('utf-8')
            desc = episode['long_description'].encode('utf-8')
            thumb = __get_thumbnail(episode)
            length = str(__get_length(episode))
            data = dict(title=title, length=length, desc=desc, episode=episode,
                        thumb=thumb)
            addEpisode(data)


def addEpisode(data):
    """Add a episode to list"""
    url = '%s?data=%s' % (sys.argv[0], simplejson.dumps(data))
    item = xbmcgui.ListItem(data['title'], iconImage=data['thumb'],
                            thumbnailImage=data['thumb'])
    item.setInfo(type="Video",
                 infoLabels={"Title": data['title'], "Plot": data['desc'],
                 "Director": "PBS", "Duration": data['length']})
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url,
                                     listitem=item, isFolder=False)
    return ok


def playEpisode(data):
    """Select Quality and start playing mp4"""
    title = data.get('title')
    desc = data.get('desc')
    length = data.get('length')
    episode = data.get('episode')
    item = xbmcgui.ListItem(label=title, iconImage=data['thumb'],
                            thumbnailImage=data['thumb'])
    item.setInfo(type="Video", infoLabels={"Title": title, "Plot": desc,
                 "Director": "PBS", "Duration": length})
    xbmc.Player().play(__select_mp4_stream(episode), item)

# Check with we have JSON data, and if so
# decode it with simplejson and set data dict.
try:
    jdata = sys.argv[2].split('?data=')[1]
    data = simplejson.loads(jdata)
except IndexError:
    data = None
except simplejson.JSONDecodeError, e:
    xbmcgui.Dialog().ok('JSONDecodeError', '%s' % e)

# If data is set to None we return a episode
# list, else we play the episode contained in
# the data dict.
if not data:
    showEpisodes()
else:
    playEpisode(data)

xbmcplugin.endOfDirectory(int(sys.argv[1]))