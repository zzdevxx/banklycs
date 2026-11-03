import os
import re
import sys
import ssl
import time
import urllib.request
import urllib.parse
from html import unescape

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

TXT_DIR = os.path.join(BASE_DIR, "TXT")

def sanitize_filename(name):
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_song_title_and_artist(raw_headline):
    """
    Parses 'Lirik & Chord Lagu Yehova Rafa - Umbu Kaborang, Andre Hermanto'
    into ('Yehova Rafa', 'Umbu Kaborang, Andre Hermanto')
    """
    text = unescape(raw_headline).strip()
    text = text.replace('’', "'").replace('‘', "'").replace('â€™', "'").replace('â€˜', "'")
    text = text.replace('“', '"').replace('”', '"').replace('â€œ', '"').replace('â€', '"')
    text = re.sub(r'^(Lirik\s+(&|dan)?\s+Chord\s+Lagu|Chord\s+(&|dan)?\s+Lirik\s+Lagu|Lirik\s+Lagu|Chord\s+Lagu)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(Chords\s+and\s+Lyrics|Lyrics\s+and\s+Chords|Chords\s+Lyrics)$', '', text, flags=re.IGNORECASE)
    
    # Check for separator ' - ' or ' – ' or ' — '
    parts = re.split(r'\s+[\-–—]\s+', text, maxsplit=1)
    if len(parts) == 2:
        title = parts[0].strip()
        artist = parts[1].strip()
        # Clean artist trailing
        artist = re.sub(r'\s*\|\s*Kidung\.com.*$', '', artist, flags=re.IGNORECASE)
        artist = re.sub(r'\s+Chords.*$', '', artist, flags=re.IGNORECASE)
        return title, artist
    return None, None

def format_lines_into_slides(lines):
    clean = [l.strip().replace('’', "'").replace('‘', "'").replace('â€™', "'").replace('â€˜', "'").replace('“', '"').replace('”', '"') for l in lines if l.strip()]
    slides = []
    for i in range(0, len(clean), 2):
        chunk = clean[i:i+2]
        slides.append("\n".join(chunk))
    return slides

def parse_kidung_content(entry_html):
    """
    Extracts pure lyric lines from entry-content, filtering chords and metadata.
    """
    # Cut off before comments / shares / metadata
    for cut in ['<div class="sharedaddy', '<p class="post-meta', 'Words &amp; Music', 'Words &#038; Music', 'Words & Music']:
        if cut in entry_html:
            entry_html = entry_html.split(cut)[0]

    # Split into paragraphs
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', entry_html, re.DOTALL)
    
    header_regex = re.compile(r'^(BLANK|INTRO|VERSE(\s+\d+)?|PRE[\s\-]*CHORUS(\s+\d+)?|CHORUS(\s+\d+)?|BRIDGE(\s+\d+)?|TAG|INTERLUDE|ENDING|OUTRO)$', re.IGNORECASE)
    
    sections = []
    curr_section_name = "VERSE 1"
    curr_lines = []
    verse_counter = 1
    
    for p in paragraphs:
        # Check if paragraph contains chord table or download image or iframe
        if any(bad in p for bad in ['<iframe', '<img', 'download-chord', 'wp-image', 'Guitar Chord', 'Piano Chord']):
            continue
            
        clean_p = unescape(p)
        raw_lines = re.split(r'<br\s*/?>|\n', clean_p)
        
        for l in raw_lines:
            l = re.sub(r'<[^>]+>', '', l).strip()
            # Ignore chord-only lines: e.g. "C   G/B   Am   F" or "Intro : C G Am"
            if not l:
                continue
            if re.match(r'^(Intro|Outro|Interlude|Ending|Bait|Chorus|Reff|Bait\s+\d+|Verse\s+\d+|Bridge)\s*:', l, re.IGNORECASE):
                # Header line
                hdr_match = re.match(r'^(Intro|Outro|Interlude|Ending|Bait|Chorus|Reff|Bridge)(\s+\d+)?', l, re.IGNORECASE)
                hdr_raw = hdr_match.group(0).upper() if hdr_match else l.upper()
                if "REFF" in hdr_raw or "CHORUS" in hdr_raw:
                    sec_tag = "CHORUS"
                elif "BAIT" in hdr_raw or "VERSE" in hdr_raw:
                    num_m = re.search(r'\d+', hdr_raw)
                    sec_tag = f"VERSE {num_m.group(0)}" if num_m else f"VERSE {verse_counter}"
                    verse_counter += 1
                elif "BRIDGE" in hdr_raw:
                    sec_tag = "BRIDGE"
                elif "INTRO" in hdr_raw:
                    sec_tag = "INTRO"
                else:
                    sec_tag = hdr_raw

                if curr_lines:
                    slides = format_lines_into_slides(curr_lines)
                    if slides:
                        sections.append((curr_section_name, slides))
                    curr_lines = []
                curr_section_name = sec_tag
                continue
                
            # If line looks like pure chords: only A-G, m, maj, sus, dim, numbers, slashes, spaces
            chord_ratio = len(re.findall(r'\b[A-G](?:#|b)?(?:m|maj|min|sus|dim|add)?\d*(?:/[A-G](?:#|b)?)?\b', l))
            tokens = l.split()
            if tokens and chord_ratio >= len(tokens) * 0.7:
                # Likely chord line, ignore
                continue
                
            curr_lines.append(l)

        # After paragraph, if we have lines and no explicit section tag switch
        if curr_lines:
            slides = format_lines_into_slides(curr_lines)
            if slides:
                sections.append((curr_section_name, slides))
            curr_lines = []
            verse_counter += 1
            curr_section_name = f"VERSE {verse_counter}"

    # Merge consecutive sections with same name or fix empty
    final_sections = []
    for sname, sslides in sections:
        if sslides:
            final_sections.append((sname, sslides))
            
    return final_sections
