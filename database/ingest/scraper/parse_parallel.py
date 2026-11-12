#!/usr/bin/env python3
"""Parse paralel (multiprocessing) untuk ribuan file HTML.

Usage: python parse_parallel.py <adapter> <html_dir> [--dry] [--procs N]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import adapters


def main():
    adapter_name = sys.argv[1]
    html_dir = sys.argv[2]
    dry = '--dry' in sys.argv
    procs = 6
    if '--procs' in sys.argv:
        procs = int(sys.argv[sys.argv.index('--procs') + 1])

    adapter = adapters.ADAPTERS[adapter_name]
    files = sorted(f for f in os.listdir(html_dir) if f.endswith('.html'))
    paths = [os.path.join(html_dir, f) for f in files]
    print(f'parsing {len(paths)} file dengan {procs} proses ...', flush=True)

    # cache: hasil parse disimpan ke JSONL supaya insert bisa diulang
    # tanpa mem-parse ulang puluhan ribu file
    import json
    cache = os.path.join(html_dir, '_parsed_rows.jsonl')
    if os.path.exists(cache):
        with open(cache, encoding='utf-8') as f:
            rows = [json.loads(l) for l in f if l.strip()]
        bad = len(paths) - len(rows)
        print(f'cache hit: {len(rows)} baris dari {cache}', flush=True)
    else:
        rows, bad = [], 0
        with ProcessPoolExecutor(procs) as ex:
            for i, r in enumerate(ex.map(adapter.parse_song, paths, chunksize=64)):
                if r:
                    rows.append(r)
                else:
                    bad += 1
                if (i + 1) % 10000 == 0:
                    print(f'  {i+1}/{len(paths)} ...', flush=True)
        with open(cache, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(f'parsed: {len(rows)} | skip/gagal: {bad}', flush=True)
    adapters.insert_songs(rows, dry=dry)


if __name__ == '__main__':
    main()
