# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urllib2
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import time

# Adicionar o caminho da biblioteca ao sys.path
__addon__ = xbmcaddon.Addon()
__path__ = __addon__.getAddonInfo('path')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
sys.path.append(os.path.join(__path__, 'resources', 'lib'))

if not os.path.exists(__profile__):
    os.makedirs(__profile__)

try:
    import m3u_parser
except ImportError:
    from resources.lib import m3u_parser

# Plugin constants
__addon_id__ = 'plugin.video.flash_brasil'
__handle__ = int(sys.argv[1])
_url = sys.argv[0]

# URL base que contém as URLs das listas M3U
BASE_SOURCE_URL = "http://htmlescola.x10.mx/htmlsre/brafilm"
CACHE_FILE = os.path.join(__profile__, 'playlist_cache.m3u')
CACHE_TIME = 3600 # 1 hora em segundos

def log(msg):
    try:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        xbmc.log("[FlashBrasil] " + str(msg), xbmc.LOGNOTICE)
    except:
        pass

def get_url(**kwargs):
    query = {}
    for k, v in kwargs.items():
        if isinstance(v, unicode):
            query[k] = v.encode('utf-8')
        else:
            query[k] = v
    return '{0}?{1}'.format(_url, urllib.urlencode(query))

def get_m3u_content():
    if os.path.exists(CACHE_FILE):
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age < CACHE_TIME:
            try:
                with open(CACHE_FILE, 'r') as f:
                    return f.read().decode('utf-8', 'ignore')
            except:
                pass

    try:
        req = urllib2.Request(BASE_SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib2.urlopen(req, timeout=10)
        source_content = response.read().decode('utf-8', 'ignore')
        
        m3u_data = None
        if "#EXTM3U" in source_content:
            m3u_data = source_content
        else:
            urls = [line.strip() for line in source_content.splitlines() if line.strip().startswith('http')]
            for m3u_url in urls:
                try:
                    req_m3u = urllib2.Request(m3u_url, headers={'User-Agent': 'Mozilla/5.0'})
                    resp_m3u = urllib2.urlopen(req_m3u, timeout=10)
                    temp_data = resp_m3u.read().decode('utf-8', 'ignore')
                    if "#EXTM3U" in temp_data:
                        m3u_data = temp_data
                        break
                except:
                    continue
        
        if m3u_data:
            with open(CACHE_FILE, 'w') as f:
                f.write(m3u_data.encode('utf-8'))
            return m3u_data
        return None
    except Exception as e:
        log("Erro ao obter conteúdo: " + str(e))
        return None

def list_categories():
    xbmcplugin.setContent(__handle__, 'files')
    xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_movies'), xbmcgui.ListItem('Filmes'), True)
    xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_series'), xbmcgui.ListItem('Séries'), True)
    xbmcplugin.endOfDirectory(__handle__)

def list_content(content_type):
    xbmcplugin.setContent(__handle__, 'movies' if content_type == 'movie' else 'tvshows')
    m3u_content = get_m3u_content()
    if not m3u_content:
        xbmcplugin.endOfDirectory(__handle__)
        return

    movies, series = m3u_parser.parse_m3u(m3u_content)
    content_data = movies if content_type == 'movie' else series

    sorted_groups = sorted(content_data.keys())
    for group_title in sorted_groups:
        label = group_title.encode('utf-8') if isinstance(group_title, unicode) else group_title
        list_item = xbmcgui.ListItem(label)
        xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_items_by_group', group_title=group_title, content_type=content_type), list_item, True)
    xbmcplugin.endOfDirectory(__handle__)

def list_items_by_group(group_title, content_type):
    xbmcplugin.setContent(__handle__, 'movies' if content_type == 'movie' else 'episodes')
    if isinstance(group_title, str):
        group_title = group_title.decode('utf-8', 'ignore')

    m3u_content = get_m3u_content()
    if not m3u_content:
        xbmcplugin.endOfDirectory(__handle__)
        return

    movies, series = m3u_parser.parse_m3u(m3u_content)
    content_data = movies if content_type == 'movie' else series

    if group_title in content_data:
        for item in content_data[group_title]:
            title = item['title'].encode('utf-8') if isinstance(item['title'], unicode) else item['title']
            list_item = xbmcgui.ListItem(title)
            list_item.setArt({'thumb': item.get('thumbnail', '')})
            list_item.setInfo('video', {'title': title})
            list_item.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(__handle__, get_url(action='play', path=item['path']), list_item, False)
    xbmcplugin.endOfDirectory(__handle__)

def play_video(path):
    play_item = xbmcgui.ListItem(path=path)
    xbmcplugin.setResolvedUrl(__handle__, True, play_item)

def router(paramstring):
    params = dict(urlparse.parse_qsl(paramstring))
    if params:
        action = params.get('action')
        if action == 'list_movies':
            list_content('movie')
        elif action == 'list_series':
            list_content('series')
        elif action == 'list_items_by_group':
            list_items_by_group(params.get('group_title'), params.get('content_type'))
        elif action == 'play':
            play_video(params.get('path'))
    else:
        list_categories()

if __name__ == '__main__':
    router(sys.argv[2][1:])
