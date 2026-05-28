# -*- coding: utf-8 -*-
import re

def parse_m3u(m3u_content):
    movies = {}
    series = {}
    current_item = {}

    for line in m3u_content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            current_item = {}
            # Extract group-title
            group_title_match = re.search(r'group-title="([^"]+)"', line)
            if group_title_match:
                current_item["group_title"] = group_title_match.group(1)
            # Extract tvg-name
            tvg_name_match = re.search(r'tvg-name="([^"]+)"', line)
            if tvg_name_match:
                current_item["title"] = tvg_name_match.group(1)
            else:
                # Fallback for title if tvg-name is not present
                title_match = re.search(r',([^,]+)$', line)
                if title_match:
                    current_item["title"] = title_match.group(1).strip()
            # Extract tvg-logo
            tvg_logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            if tvg_logo_match:
                current_item["thumbnail"] = tvg_logo_match.group(1)

        elif line and not line.startswith("#"):
            current_item["path"] = line
            if "group_title" in current_item and "title" in current_item and "path" in current_item:
                if "/movie/" in current_item["path"]:
                    if current_item["group_title"] not in movies:
                        movies[current_item["group_title"]] = []
                    movies[current_item["group_title"]].append(current_item)
                elif "/series/" in current_item["path"]:
                    if current_item["group_title"] not in series:
                        series[current_item["group_title"]] = []
                    series[current_item["group_title"]].append(current_item)
            current_item = {}

    return movies, series
