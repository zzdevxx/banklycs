#!/usr/bin/env python3
"""Banklycs Scraper — tools pengayaan katalog lagu yang proper.

Subcommands:
  discover   Kumpulkan URL halaman lagu dari sebuah sumber (adapter).
  fetch      Unduh halaman-halaman lagu (resume, keep-alive, proxy opsional).
  check-proxy Validasi daftar proxy, tulis daftar yang hidup saja.
  parse      Konversi HTML tersimpan -> BL format + insert ke banklycs.db.
  dedupe     Hapus duplikat (judul sama + isi mirip), simpan versi terbaik.

Contoh:
  python scraper.py check-proxy floppy.txt --out alive.txt
  python scraper.py discover sifalyrics --out urls.txt
  python scraper.py fetch --urls urls.txt --out sifa_songs --workers 8
  python scraper.py fetch --urls urls.txt --out sifa_songs --proxy alive.txt --workers 24
  python scraper.py parse sifalyrics --dir sifa_songs --dry
  python scraper.py dedupe
"""
import argparse
import os
import sys
import time
import threading
import itertools
import concurrent.futures as cf

import requests

from adapters import ADAPTERS, DB_PATH

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) BanklycsCatalog/1.0'


# ---------------------------------------------------------------- check-proxy
def cmd_check_proxy(args):
    """Uji tiap proxy terhadap domain target; tulis yang hidup ke --out."""
    proxies = [l.strip() for l in open(args.file, encoding='utf-8')
               if l.strip().startswith(('http://', 'https://', 'socks'))]
    print(f'{len(proxies)} proxy dimuat dari {args.file}')
    test_url = args.test_url
    alive, dead = [], []
    lock = threading.Lock()

    def test(px):
        try:
            r = requests.get(test_url, proxies={'http': px, 'https': px},
                             timeout=args.timeout, headers={'User-Agent': UA})
            ok = r.status_code == 200 and len(r.content) > 1000
        except Exception:
            ok = False
        with lock:
            (alive if ok else dead).append(px)

    t0 = time.time()
    with cf.ThreadPoolExecutor(args.concurrency) as ex:
        list(ex.map(test, proxies))
    print(f'hasil: {len(alive)} hidup, {len(dead)} mati ({time.time()-t0:.0f}s)')
    if alive and args.out:
        open(args.out, 'w', encoding='utf-8').write('\n'.join(alive))
        print(f'ditulis: {args.out}')
    return 0 if alive else 1


# --------------------------------------------------------------------- fetch
def cmd_fetch(args):
    urls = [l.strip() for l in open(args.urls, encoding='utf-8') if l.strip()]
    os.makedirs(args.out, exist_ok=True)

    proxies = []
    if args.proxy:
        proxies = [l.strip() for l in open(args.proxy, encoding='utf-8')
                   if l.strip().startswith(('http://', 'https://', 'socks'))]
        print(f'{len(proxies)} proxy dimuat')

    count, errs, throttle_until = [0], [0], [0.0]
    lock = threading.Lock()
    proxy_cycle = itertools.cycle(proxies) if proxies else None
    tlocal = threading.local()

    def get_session():
        if not hasattr(tlocal, 's'):
            s = requests.Session()
            s.headers.update({'User-Agent': UA})
            if proxy_cycle is not None:
                with lock:
                    px = next(proxy_cycle)
                s.proxies = {'http': px, 'https': px}
            tlocal.s = s
        return tlocal.s

    def fetch_one(url):
        if time.time() < throttle_until[0]:
            time.sleep(throttle_until[0] - time.time())
        name = url.rstrip('/').rsplit('/', 1)[-1] + '.html'
        out = os.path.join(args.out, name)
        if os.path.exists(out) and os.path.getsize(out) > args.min_size:
            with lock:
                count[0] += 1
            return
        s = get_session()
        for attempt in range(args.retries):
            try:
                r = s.get(url, timeout=args.timeout)
                if r.status_code in (429, 503):
                    # throttle global: semua worker jeda
                    with lock:
                        throttle_until[0] = max(throttle_until[0], time.time() + args.backoff)
                    return
                if r.status_code == 200 and len(r.content) > args.min_size:
                    open(out, 'wb').write(r.content)
                    with lock:
                        count[0] += 1
                        n = count[0]
                    if n % 500 == 0:
                        print(f'  {n}/{len(urls)} ...', file=sys.stderr)
                    return
                errs[0] += 1
                return
            except Exception:
                errs[0] += 1
                time.sleep(args.delay * (attempt + 1))

    t0 = time.time()
    with cf.ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(fetch_one, urls))
    print(f'fetch selesai: {count[0]}/{len(urls)} ok, {errs[0]} error, '
          f'{time.time()-t0:.0f}s')
    return 0


# --------------------------------------------------------------------- parse
def cmd_parse(args):
    adapter = ADAPTERS.get(args.source)
    if not adapter:
        print(f'sumber tidak dikenal: {args.source}. '
              f'Pilihan: {", ".join(ADAPTERS)}')
        return 1
    adapter.run(args.dir, dry=args.dry, source_name=args.source)
    return 0


# -------------------------------------------------------------------- dedupe
def cmd_dedupe(args):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import dedupe_songs
    sys.argv = ['dedupe_songs.py'] + (['--dry'] if args.dry else [])
    dedupe_songs.main()
    return 0


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(prog='banklycs-scraper',
                                 description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('check-proxy', help='validasi daftar proxy')
    p.add_argument('file', help='file daftar proxy (satu per baris)')
    p.add_argument('--out', help='tulis proxy yang hidup ke file ini')
    p.add_argument('--test-url', default='https://sifalyrics.com/sitemap.xml')
    p.add_argument('--timeout', type=float, default=10.0)
    p.add_argument('--concurrency', type=int, default=20)
    p.set_defaults(fn=cmd_check_proxy)

    p = sub.add_parser('discover', help='kumpulkan URL halaman lagu')
    p.add_argument('source', choices=sorted(ADAPTERS))
    p.add_argument('--out', required=True, help='file output daftar URL')
    p.add_argument('--feed-url', help='(blogger) URL feed Atom awal')
    p.set_defaults(fn=lambda a: ADAPTERS[a.source].discover(a.out) or 0)

    p = sub.add_parser('fetch', help='unduh halaman lagu')
    p.add_argument('--urls', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--proxy', help='file proxy opsional (rotasi per worker)')
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--timeout', type=float, default=25.0)
    p.add_argument('--retries', type=int, default=3)
    p.add_argument('--delay', type=float, default=0.5)
    p.add_argument('--backoff', type=float, default=30.0,
                   help='jeda global saat kena 429/503 (detik)')
    p.add_argument('--min-size', type=int, default=5000)
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser('parse', help='HTML -> BL format -> banklycs.db')
    p.add_argument('source', choices=sorted(ADAPTERS))
    p.add_argument('--dir', required=True, help='folder HTML hasil fetch')
    p.add_argument('--dry', action='store_true', help='laporan saja, tanpa insert')
    p.set_defaults(fn=cmd_parse)

    p = sub.add_parser('dedupe', help='hapus duplikat dari DB')
    p.add_argument('--dry', action='store_true')
    p.set_defaults(fn=cmd_dedupe)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == '__main__':
    main()
