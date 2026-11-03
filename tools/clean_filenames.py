import os
import re

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

txt_dir = os.path.join(BASE_DIR, "database")
if not os.path.isdir(txt_dir):
    txt_dir = os.path.join(BASE_DIR, "TXT")
for f in os.listdir(txt_dir):
    clean_name = f.replace('â€™', "'").replace('â€˜', "'").replace('’', "'").replace('‘', "'")
    clean_name = clean_name.replace('â€œ', "'").replace('â€', "'").replace('“', "'").replace('”', "'").replace('"', "'")
    clean_name = re.sub(r'[<>:"/\\|?*]', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    if clean_name != f:
        old_path = os.path.join(txt_dir, f)
        new_path = os.path.join(txt_dir, clean_name)
        if not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"Renamed: {f} -> {clean_name}")
        else:
            os.remove(old_path)
            print(f"Removed duplicate: {f}")
