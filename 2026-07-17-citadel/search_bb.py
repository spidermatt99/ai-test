import urllib.request, urllib.parse, json, re

def ddg(q):
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        links = set(re.findall(r'href=[\'"](.*?)[\'"]', html))
        bb_links = []
        for l in links:
            if 'uddg=' in l:
                actual = urllib.parse.unquote(l.split('uddg=')[1].split('&')[0])
                if 'bloomberg.com' in actual:
                    bb_links.append(actual)
            elif 'bloomberg.com' in l:
                bb_links.append(l)
        return bb_links
    except Exception as e:
        return str(e)

print('General:', ddg('site:bloomberg.com crypto citadel'))
print('General2:', ddg('site:bloomberg.com EDX Markets Citadel'))
