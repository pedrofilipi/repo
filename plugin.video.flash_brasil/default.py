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
import re

# Adicionar pasta lib ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'resources', 'lib'))
import m3u_parser

# Configurações do Addon
__addon__ = xbmcaddon.Addon()
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
_url = sys.argv[0]
__handle__ = int(sys.argv[1])

if not os.path.exists(__profile__):
    os.makedirs(__profile__)

# A URL base que contém as URLs das listas M3U
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

def to_unicode(text):
    if isinstance(text, str):
        try:
            return text.decode('utf-8')
        except:
            return text.decode('iso-8859-1', 'ignore')
    return text

def to_utf8(text):
    if isinstance(text, unicode):
        return text.encode('utf-8')
    return text

def get_url(**kwargs):
    query = {}
    for k, v in kwargs.items():
        query[k] = to_utf8(v)
    return '{0}?{1}'.format(_url, urllib.urlencode(query))

def get_m3u_content():
    if os.path.exists(CACHE_FILE):
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age < CACHE_TIME:
            try:
                with open(CACHE_FILE, 'r') as f:
                    return to_unicode(f.read())
            except:
                pass
    try:
        req = urllib2.Request(BASE_SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib2.urlopen(req, timeout=10)
        source_content = to_unicode(response.read())
        
        m3u_data = None
        if "#EXTM3U" in source_content:
            m3u_data = source_content
        else:
            urls = [line.strip() for line in source_content.splitlines() if line.strip().startswith('http')]
            for m3u_url in urls:
                try:
                    req_m3u = urllib2.Request(m3u_url, headers={'User-Agent': 'Mozilla/5.0'})
                    resp_m3u = urllib2.urlopen(req_m3u, timeout=10)
                    temp_data = to_unicode(resp_m3u.read())
                    if "#EXTM3U" in temp_data:
                        m3u_data = temp_data
                        break
                except:
                    continue
        
        if m3u_data:
            with open(CACHE_FILE, 'w') as f:
                f.write(to_utf8(m3u_data))
            return m3u_data
        return None
    except Exception as e:
        log("Erro ao obter conteúdo: " + str(e))
        return None

def list_categories():
    xbmcplugin.setContent(__handle__, 'files')
    xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_movies'), xbmcgui.ListItem('[COLOR white]Filmes[/COLOR]'), True)
    xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_series'), xbmcgui.ListItem('[COLOR white]Séries[/COLOR]'), True)
    xbmcplugin.addDirectoryItem(__handle__, get_url(action='search'), xbmcgui.ListItem('[COLOR yellow]Buscar...[/COLOR]'), True)
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
        label = to_utf8(group_title)
        display_label = "[COLOR white]{0}[/COLOR]".format(label)
        list_item = xbmcgui.ListItem(display_label)
        xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_items_by_group', group_title=group_title, content_type=content_type), list_item, True)
    
    xbmcplugin.endOfDirectory(__handle__)

def list_items_by_group(group_title, content_type):
    group_title = to_unicode(group_title)
    m3u_content = get_m3u_content()
    if not m3u_content:
        xbmcplugin.endOfDirectory(__handle__)
        return
    
    movies, series = m3u_parser.parse_m3u(m3u_content)
    content_data = movies if content_type == 'movie' else series
    
    if group_title not in content_data:
        xbmcplugin.endOfDirectory(__handle__)
        return

    items = content_data[group_title]
    
    if content_type == 'movie':
        xbmcplugin.setContent(__handle__, 'movies')
        for item in items:
            add_video_item(item)
    else:
        xbmcplugin.setContent(__handle__, 'tvshows')
        display_shows_as_folders(items, group_title)
            
    xbmcplugin.endOfDirectory(__handle__)

def display_shows_as_folders(items, group_title):
    shows = {}
    for item in items:
        show_name = get_clean_show_name(to_unicode(item['title']))
        if show_name not in shows:
            shows[show_name] = {
                'title': show_name,
                'thumbnail': item.get('thumbnail', ''),
                'count': 0
            }
        shows[show_name]['count'] += 1
        
    sorted_shows = sorted(shows.keys())
    for show_key in sorted_shows:
        show = shows[show_key]
        label = to_utf8(show['title'])
        display_label = "[COLOR white]{0}[/COLOR] [COLOR lightgray]({1})[/COLOR]".format(label, show['count'])
        list_item = xbmcgui.ListItem(display_label)
        list_item.setArt({'thumb': show['thumbnail']})
        xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_episodes', show_name=show['title'], group_title=group_title), list_item, True)

def get_clean_show_name(full_title):
    # Limpar padrões de temporada e episódio
    show_name = re.sub(r'[\s\-]+S\d+E\d+.*$', '', full_title, flags=re.IGNORECASE)
    show_name = re.sub(r'[\s\-]+\d+x\d+.*$', '', show_name, flags=re.IGNORECASE)
    show_name = re.sub(r'[\s\-]+Episódio\s+\d+.*$', '', show_name, flags=re.IGNORECASE)
    return show_name.strip()

def add_video_item(item):
    title = to_utf8(item['title'])
    display_title = "[COLOR white]{0}[/COLOR]".format(title)
    list_item = xbmcgui.ListItem(display_title)
    list_item.setArt({'thumb': item.get('thumbnail', '')})
    list_item.setInfo('video', {'title': title})
    list_item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(__handle__, get_url(action='play', path=item['path']), list_item, False)

def list_episodes(show_name, group_title):
    xbmcplugin.setContent(__handle__, 'episodes')
    show_name = to_unicode(show_name)
    group_title = to_unicode(group_title)
        
    m3u_content = get_m3u_content()
    movies, series = m3u_parser.parse_m3u(m3u_content)
    
    if group_title in series:
        for item in series[group_title]:
            if show_name in to_unicode(item['title']):
                add_video_item(item)
                
    xbmcplugin.endOfDirectory(__handle__)

def search():
    keyboard = xbmc.Keyboard('', 'Buscar Filmes ou Séries')
    keyboard.doModal()
    if keyboard.isConfirmed():
        query = keyboard.getText()
        if query:
            do_search(query)

def do_search(query):
    xbmcplugin.setContent(__handle__, 'files')
    m3u_content = get_m3u_content()
    if not m3u_content:
        xbmcplugin.endOfDirectory(__handle__)
        return

    movies, series = m3u_parser.parse_m3u(m3u_content)
    query = to_unicode(query).lower()
    
    # Busca em Filmes
    found_movies = []
    for group in movies.values():
        for item in group:
            if query in to_unicode(item['title']).lower():
                found_movies.append(item)
    
    # Busca em Séries
    found_series_items = []
    for group in series.values():
        for item in group:
            if query in to_unicode(item['title']).lower():
                found_series_items.append(item)

    if not found_movies and not found_series_items:
        xbmcgui.Dialog().ok('Busca', 'Nenhum resultado encontrado para: ' + to_utf8(query))
        xbmcplugin.endOfDirectory(__handle__)
        return

    # Exibir Filmes encontrados
    if found_movies:
        for item in found_movies:
            add_video_item(item)

    # Exibir Séries encontradas (agrupadas por nome)
    if found_series_items:
        shows = {}
        for item in found_series_items:
            show_name = get_clean_show_name(to_unicode(item['title']))
            if show_name not in shows:
                shows[show_name] = {
                    'title': show_name,
                    'thumbnail': item.get('thumbnail', ''),
                    'group_title': item.get('group_title', ''),
                    'count': 0
                }
            shows[show_name]['count'] += 1
            
        for show_key in sorted(shows.keys()):
            show = shows[show_key]
            label = to_utf8(show['title'])
            display_label = "[COLOR cyan][SÉRIE][/COLOR] [COLOR white]{0}[/COLOR] [COLOR lightgray]({1})[/COLOR]".format(label, show['count'])
            list_item = xbmcgui.ListItem(display_label)
            list_item.setArt({'thumb': show['thumbnail']})
            xbmcplugin.addDirectoryItem(__handle__, get_url(action='list_episodes', show_name=show['title'], group_title=show['group_title']), list_item, True)

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
        elif action == 'list_episodes':
            list_episodes(params.get('show_name'), params.get('group_title'))
        elif action == 'search':
            search()
        elif action == 'play':
            play_video(params.get('path'))
    else:
        list_categories()

if __name__ == '__main__':
    router(sys.argv[2][1:])
