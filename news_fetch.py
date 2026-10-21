#!/usr/bin/env python3
"""MyLuiseApp: holt Kinder- und Familien-Nachrichten und schreibt sie nach news.json.
Läuft automatisch in GitHub Actions. Die App liest news.json vom eigenen Server, daher laden die News sofort."""
import json, re, sys, time, html, urllib.request, urllib.parse, email.utils
import xml.etree.ElementTree as ET

CONFIG = {"stages": [{"id": "neu", "q": {"gesundheit": ["Neugeborenes Gesundheit Stillen Pflege Kinderarzt"], "entwicklung": ["Neugeborenes Entwicklung Schlaf Bindung"], "natur": ["(Homöopathie OR Naturheilkunde OR Hausmittel) Baby"], "recht": ["Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen Gesetz", "Junior-Depot OR Kinderdepot OR Frühstart-Rente OR Kindersparen"], "sicherheit": ["Babyprodukt Rückruf Warnung"]}}, {"id": "baby1", "q": {"gesundheit": ["Baby Gesundheit Säugling Pflege Kinderarzt"], "entwicklung": ["Baby Entwicklung Schlaf Beikost"], "natur": ["(Homöopathie OR Naturheilkunde OR Hausmittel) Baby"], "recht": ["Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen Gesetz", "Junior-Depot OR Kinderdepot OR Frühstart-Rente OR Kindersparen"], "sicherheit": ["Babyprodukt Rückruf Warnung"]}}, {"id": "baby2", "q": {"gesundheit": ["Baby Gesundheit Zahnen Kinderarzt Ernährung"], "entwicklung": ["Baby Entwicklung Beikost krabbeln"], "natur": ["(Homöopathie OR Naturheilkunde OR Hausmittel) Baby Zahnen"], "recht": ["Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen Gesetz", "Junior-Depot OR Kinderdepot OR Frühstart-Rente OR Kindersparen"], "sicherheit": ["Babyprodukt Rückruf Warnung"]}}, {"id": "klein", "q": {"gesundheit": ["Kleinkind Gesundheit Kinderarzt Ernährung"], "entwicklung": ["Kleinkind Entwicklung Sprache Trotzphase"], "natur": ["(Homöopathie OR Naturheilkunde OR Heilpflanzen) Kleinkind Kinder"], "recht": ["Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen Gesetz", "Junior-Depot OR Kinderdepot OR Frühstart-Rente OR Kindersparen"], "sicherheit": ["Kinderprodukt Spielzeug Rückruf Warnung"]}}, {"id": "kita", "q": {"gesundheit": ["Kindergartenkind Gesundheit Kinderarzt"], "entwicklung": ["Vorschulkind Entwicklung Schulreife"], "natur": ["(Naturkunde OR Naturheilkunde OR Homöopathie) Kinder Natur entdecken"], "recht": ["Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen Gesetz", "Junior-Depot OR Kinderdepot OR Frühstart-Rente OR Kindersparen"], "sicherheit": ["Spielzeug Rückruf Kinder Warnung"]}}, {"id": "schule", "q": {"gesundheit": ["Schulkinder Gesundheit Kinderarzt"], "entwicklung": ["Grundschule Kinder Lernen Medien"], "natur": ["(Naturkunde OR Naturheilkunde OR Homöopathie) Schulkinder"], "recht": ["Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen Gesetz", "Junior-Depot OR Kinderdepot OR Frühstart-Rente OR Kindersparen"], "sicherheit": ["Kinder Sicherheit Schulweg Rückruf"]}}, {"id": "teen", "q": {"gesundheit": ["Jugendliche Gesundheit Kinderarzt"], "entwicklung": ["Jugendliche Pubertät Schule Medien"], "natur": ["(Naturheilkunde OR Homöopathie) Jugendliche"], "recht": ["Kindergeld Ausbildung Jugendliche Gesetz", "Taschengeld Jugendkonto Junior-Depot"], "sicherheit": ["Jugendliche Sicherheit Internet Rückruf"]}}], "topics": ["gesundheit", "entwicklung", "natur", "recht", "sicherheit"]}
TOPICS = CONFIG['topics']
BLOCK = re.compile(r'impf|stiko', re.I)
UA = 'Mozilla/5.0 (compatible; MyLuiseApp/1.0; +https://github.com)'
GELD_QUERIES = ['Junior-Depot OR Kinderdepot OR Kinderkonto OR Frühstart-Rente', 'Kindergeld OR Kinderfreibetrag Erhöhung Gesetz']
GDELT = {
    'gesundheit': '(Baby OR Säugling OR Kleinkind OR Kinderarzt OR Stillen OR Kindergesundheit) sourcelang:german',
    'entwicklung': '(Kleinkind OR Baby OR Kita OR Kindesentwicklung OR Beikost OR Schlaf) (Entwicklung OR Erziehung OR Eltern) sourcelang:german',
    'recht': '(Kindergeld OR Elterngeld OR Kinderfreibetrag OR Familienleistungen) sourcelang:german',
    'sicherheit': '(Babyprodukt OR Kinderprodukt OR Spielzeug OR Kindersitz) (Rückruf OR Warnung) sourcelang:german',
    'natur': '(Homöopathie OR Naturheilkunde OR Hausmittel) (Kinder OR Baby) sourcelang:german',
}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def local(tag):
    return tag.split('}')[-1]


def split_title(title, source):
    title = html.unescape(title or '').strip()
    source = html.unescape(source or '').strip()
    m = re.match(r'^(.*)\s[-–|]\s([^-–|]{2,40})$', title)
    if m and (not source or m.group(2).strip().lower() == source.lower() or not source):
        return m.group(1).strip(), (source or m.group(2)).strip()
    return title, source


def unwrap(link):
    try:
        u = urllib.parse.urlparse(link)
        if u.hostname and u.hostname.endswith('bing.com'):
            t = urllib.parse.parse_qs(u.query).get('url')
            if t:
                return t[0]
    except Exception:
        pass
    return link


def parse_rss(data):
    root = ET.fromstring(data)
    out = []
    for it in root.iter('item'):
        f = {}
        for ch in it:
            k = local(ch.tag)
            if k not in f:
                f[k] = ch
        def tx(k):
            e = f.get(k)
            return (e.text or '').strip() if e is not None else ''
        img = ''
        for k in ('Image', 'thumbnail', 'content', 'enclosure'):
            e = f.get(k)
            if e is not None:
                img = (e.text or '').strip() or e.attrib.get('url', '')
                if img:
                    break
        if not img:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', html.unescape(tx('description')))
            img = m.group(1) if m else ''
        if img.startswith('http://'):
            img = 'https://' + img[7:]
        t, s = split_title(tx('title'), tx('source') or tx('Source'))
        try:
            d = int(email.utils.parsedate_to_datetime(tx('pubDate')).timestamp() * 1000)
        except Exception:
            d = 0
        link = unwrap(tx('link'))
        if t and link.startswith('http'):
            out.append({'t': t, 's': s, 'u': link, 'd': d, 'i': img if img.startswith('https://') else ''})
    return out


def bing(q):
    return parse_rss(get('https://www.bing.com/news/search?q=' + urllib.parse.quote(q) + '&format=rss&setlang=de&cc=DE&mkt=de-DE'))


def google(q):
    return parse_rss(get('https://news.google.com/rss/search?q=' + urllib.parse.quote(q + ' when:30d') + '&hl=de&gl=DE&ceid=DE:de'))


def gdelt(q):
    url = 'https://api.gdeltproject.org/api/v2/doc/doc?mode=artlist&format=json&maxrecords=60&sort=datedesc&timespan=21d&query=' + urllib.parse.quote(q)
    j = json.loads(get(url, 40).decode('utf-8', 'replace'))
    out = []
    for a in j.get('articles', []):
        try:
            d = int(time.mktime(time.strptime(a['seendate'], '%Y%m%dT%H%M%SZ')) * 1000)
        except Exception:
            d = 0
        img = a.get('socialimage') or ''
        if img.startswith('http://'):
            img = 'https://' + img[7:]
        out.append({'t': html.unescape(a.get('title', '')).strip(), 's': re.sub(r'^www\.', '', a.get('domain', '')), 'u': a.get('url', ''), 'd': d, 'i': img if img.startswith('https://') else ''})
    return out


def key(t):
    return re.sub(r'[^a-zäöüß0-9]', '', t.lower())[:60]


def clean(items, mx):
    now = time.time() * 1000
    seen, out = set(), []
    for x in sorted(items, key=lambda x: -x['d']):
        if not x['t'] or not x['u'] or BLOCK.search(x['t']) or len(x['t']) < 15:
            continue
        if x['d'] and now - x['d'] > 45 * 864e5:
            continue
        k = key(x['t'])
        if k in seen or len(out) >= mx:
            continue
        seen.add(k)
        out.append(x)
    return out


def fetch_query(q, cache):
    if q in cache:
        return cache[q]
    items = []
    for fn in (bing, google):
        try:
            items += fn(q)
        except Exception as e:
            print('  Fehler', fn.__name__, q[:40], e, file=sys.stderr)
        if len(items) >= 4:
            break
        time.sleep(0.4)
    cache[q] = items
    return items


# ---------- Reels: YouTube Shorts je Thema ----------
VID_TOPICS = {
    'schlaf': ['Baby Schlaf sicher Tipps Eltern', 'Baby einschlafen Hebamme Tipps'],
    'essen': ['Stillen Anleitung Hebamme', 'Beikost Start Baby Anleitung'],
    'pflege': ['Baby baden Anleitung Neugeborenes', 'Baby wickeln Anleitung'],
    'entwicklung': ['Baby Entwicklung Meilensteine Kinderarzt', 'Baby fördern spielen Anleitung'],
    'hilfe': ['Erste Hilfe Baby Säugling Anleitung', 'Baby verschluckt Erste Hilfe'],
    'tragen': ['Baby tragen Tragetuch Anleitung', 'Babymassage Anleitung'],
}
VID_MAX_SECS = 95
CHROME = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'


def secs(txt):
    try:
        p = [int(x) for x in str(txt).split(':')]
    except ValueError:
        return 0
    n = 0
    for x in p:
        n = n * 60 + x
    return n


def parse_yt(page):
    """Liest Videos aus der YouTube-Suchseite (videoRenderer, reelItemRenderer, shortsLockupViewModel)."""
    out, seen = [], set()
    i = page.find('ytInitialData')
    if i < 0:
        return out
    j = page.find('{', i)
    try:
        data, _ = json.JSONDecoder().raw_decode(page[j:])
    except ValueError:
        return out

    def txt(o):
        if not isinstance(o, dict):
            return ''
        return o.get('simpleText') or ''.join(r.get('text', '') for r in o.get('runs', [])) or o.get('content', '')

    def add(vid, t, ch, ln):
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid or '') or vid in seen:
            return
        seen.add(vid)
        out.append({'vid': vid, 't': t.strip(), 'ch': ch, 'len': ln})

    def walk(o):
        if isinstance(o, dict):
            v = o.get('videoRenderer')
            if isinstance(v, dict) and v.get('videoId'):
                add(v['videoId'], txt(v.get('title')), txt(v.get('ownerText')), txt(v.get('lengthText')))
                return
            v = o.get('reelItemRenderer')
            if isinstance(v, dict) and v.get('videoId'):
                add(v['videoId'], txt(v.get('headline')), '', '')
                return
            v = o.get('shortsLockupViewModel')
            if isinstance(v, dict):
                ep = ((v.get('onTap') or {}).get('innertubeCommand') or {}).get('reelWatchEndpoint') or {}
                vid = ep.get('videoId') or str(v.get('entityId', '')).replace('shorts-shelf-item-', '')
                add(vid, txt((v.get('overlayMetadata') or {}).get('primaryText')) or v.get('accessibilityText', ''), '', '')
                return
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    return out


def yt_search(q):
    url = 'https://www.youtube.com/results?hl=de&gl=DE&sp=EgIYAQ%253D%253D&search_query=' + urllib.parse.quote(q + ' #shorts')
    req = urllib.request.Request(url, headers={'User-Agent': CHROME, 'Accept-Language': 'de-DE,de;q=0.9', 'Cookie': 'CONSENT=YES+cb; SOCS=CAI'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return parse_yt(r.read().decode('utf-8', 'ignore'))


def fetch_videos():
    topics = {}
    for tid, qs in VID_TOPICS.items():
        seen, lst = set(), []
        for q in qs:
            try:
                for x in yt_search(q):
                    ln = secs(x['len']) if x['len'] else 0
                    if x['vid'] in seen or not x['t'] or BLOCK.search(x['t']) or (x['len'] and (ln <= 0 or ln > VID_MAX_SECS)):
                        continue
                    seen.add(x['vid'])
                    lst.append(x)
            except Exception as e:
                print('  Fehler YouTube', q, e, file=sys.stderr)
            time.sleep(1.5)
        if lst:
            topics[tid] = lst[:12]
    return topics


def main(out_path='news.json', fast=False):
    cache, stages = {}, {}
    gd = {}
    for st in CONFIG['stages']:
        by = {}
        for tp in TOPICS:
            items = []
            for q in st['q'].get(tp, []):
                items += fetch_query(q, cache)
            by[tp] = clean(items, 10)
        stages[st['id']] = by
    # Lücken mit GDELT füllen (nur wenn Bing und Google zu wenig liefern)
    for tp in TOPICS:
        need = any(len(stages[s['id']][tp]) < 3 for s in CONFIG['stages'])
        if need and not fast:
            try:
                gd[tp] = clean(gdelt(GDELT[tp]), 12)
            except Exception as e:
                print('  Fehler gdelt', tp, e, file=sys.stderr)
            time.sleep(6)
    result = {}
    for sid, by in stages.items():
        seen, flat = set(), []
        for tp in TOPICS:
            pool = by[tp] + (gd.get(tp, []) if len(by[tp]) < 3 else [])
            for x in clean(pool, 10):
                k = key(x['t'])
                if k in seen:
                    continue
                seen.add(k)
                flat.append(dict(x, topic=tp))
        result[sid] = sorted(flat, key=lambda x: -x['d'])
    geld = []
    for q in GELD_QUERIES:
        geld += fetch_query(q, cache)
    geld = clean(geld, 12)
    total = sum(len(v) for v in result.values())
    if total == 0 and not geld:
        print('Keine Meldungen erhalten, news.json bleibt unverändert.', file=sys.stderr)
        return 1
    out = {'ts': int(time.time() * 1000), 'stages': result, 'geld': geld}
    try:
        vids = fetch_videos() if not fast else {}
    except Exception as e:
        print('  Fehler Videos', e, file=sys.stderr)
        vids = {}
    if vids:
        out['videos'] = {'ts': out['ts'], 'topics': vids}
    else:
        try:  # alte Videos behalten, wenn YouTube gerade nichts liefert
            with open(out_path, encoding='utf-8') as f:
                old = json.load(f).get('videos')
            if old:
                out['videos'] = old
        except Exception:
            pass
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('Fertig:', {k: len(v) for k, v in result.items()}, 'geld', len(geld), 'videos', {k: len(v) for k, v in out.get('videos', {}).get('topics', {}).items()})
    return 0


if __name__ == '__main__':
    sys.exit(main())
