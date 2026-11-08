"""Local filesystem validation only. Does not start a server or make requests."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import json
import xml.etree.ElementTree as ET
import tomllib
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
P=ROOT/'public'
M=json.loads((ROOT/'draft-manifest.json').read_text())
BASE=M['configured_base']
VOID={'meta','link','br','hr','img','input','area','base','col','embed','param','source','track','wbr'}
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.stack=[];self.ids=set();self.links=[];self.titles=[];self.h1s=[];self.metas=[];self.canon=[];self.ld=[];self.text=[];self.capture=None;self.buffer=''
    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        assert not any(k.startswith('on') for k in a), 'Inline handler'
        assert t not in {'form','input','textarea','select','iframe','audio','video'},t
        if t=='script':assert a=={'type':'application/ld+json'}
        if t=='button':assert 'disabled' in a
        if 'id' in a:assert a['id'] not in self.ids;self.ids.add(a['id'])
        if t=='meta':self.metas.append(a)
        if t=='link' and a.get('rel')=='canonical':self.canon.append(a['href'])
        elif 'href' in a:self.links.append(a['href'])
        if 'src' in a:
            assert t=='img' and a.get('alt')=='Delmarva Home Comfort Guide'
            assert a.get('width')=='512' and a.get('height')=='150'
            self.links.append(a['src'])
        if 'srcset' in a:
            assert t=='source' and a.get('type')=='image/svg+xml'
            self.links.append(a['srcset'])
        if t in {'h1','title','script'}:self.capture=t;self.buffer=''
        if t not in VOID:self.stack.append(t)
    def handle_data(self,s):
        if self.capture:self.buffer+=s
        if self.capture!='script':self.text.append(s)
    def handle_endtag(self,t):
        assert self.stack and self.stack.pop()==t, f'Unbalanced {t}'
        if t==self.capture:
            {'title':self.titles,'h1':self.h1s,'script':self.ld}[t].append(self.buffer.strip());self.capture=None

def resolve(source,href):
    u=urlsplit(href);assert not u.scheme and not u.netloc,href
    target=(P/unquote(u.path.lstrip('/'))) if u.path.startswith('/') else source.parent/unquote(u.path)
    target=target.resolve()
    assert target.is_relative_to(P),href
    if target.is_dir():target=target/'index.html'
    assert target.is_file(),f'Missing local target {href} from {source}'
    return target,u.fragment

def run():
    assert BASE=='https://delmarvahomecomfortguide.com'
    # Checkout metadata may exist only at the repository root. Nested .git still fails.
    git_meta={x for x in ROOT.rglob('*') if x.name=='.git'}
    assert git_meta<={ROOT/'.git'},git_meta
    for runtime in [*P.rglob('*.html'),P/'sitemap.xml',P/'robots.txt',ROOT/'draft-manifest.json']:
        assert 'example.invalid' not in runtime.read_text()
    assert 'Disallow: /' in (P/'robots.txt').read_text()
    assert len(M['routes'])==9
    expected={P/r['file'] for r in M['routes']}|{P/'404.html'}
    assert set(P.rglob('*.html'))==expected
    allowed=expected|{P/'styles.css',P/'robots.txt',P/'sitemap.xml'}|{P/a for a in M['brand_assets']}
    assert {x for x in P.rglob('*') if x.is_file()}==allowed, 'Unexpected public file'
    assert not any(x.is_symlink() for x in P.rglob('*'))
    assert not list(ROOT.glob('*.html')), 'Stale runtime at prototype root'
    for item in P.rglob('*'):
        if item.is_file():assert item.suffix not in {'.md','.py','.json','.toml'}, item
    parsed={};route_results=[];titles=[];descriptions=[];h1s=[]
    for file in sorted(expected):
        text=file.read_text()
        assert 'North Star Heating and Air Conditioning Inc. (Dagsboro, DE)' in text
        assert 'Planned launch disclosure — forwarding is not active in this draft' in text
        assert 'Tracking number pending — calls are not active' in text
        assert 'No referral provider is confirmed' not in text
        for blocked in ['tel:', 'sms:', 'HVACBusiness', 'LocalBusiness', 'AggregateRating', 'openingHours', 'telephone', 'same-day', '24/7']:
            assert blocked not in text, blocked
        a=Page();a.feed(text);assert not a.stack
        assert len(a.titles)==len(a.h1s)==1
        assert len([x for x in a.metas if x.get('name')=='description'])==1
        assert [x['content'] for x in a.metas if x.get('name')=='robots']==['noindex,nofollow']
        visible=' '.join(a.text)
        assert 'cursor.com' not in text and 'README.md' not in visible
        for phrase in ['Replace the existing safety-placeholder', 'Do not paste', 'Implementation instructions']:
            assert phrase not in visible
        if file==P/'index.html' or file==P/'about/index.html':
            assert 'do not recommend equipment, diagnose a system or provide safety instructions' not in visible
            assert 'current pages are nontechnical questions' not in visible
        for label in ['UNPUBLISHED LOCAL DRAFT','UNREVIEWED','NO REFERRALS AVAILABLE']:assert label in visible
        parsed[file]=a
    for row in M['routes']:
        file=P/row['file'];a=parsed[file]
        assert a.titles==[row['title']] and a.h1s==[row['h1']]
        ds=[x['content'] for x in a.metas if x.get('name')=='description'];assert ds==[row['description']]
        assert a.canon==[BASE+row['route']]
        assert len(a.ld)==1
        data=json.loads(a.ld[0]);assert data['@context']=='https://schema.org'
        page,crumbs,organization=data['@graph']
        assert organization=={'@type':'Organization','@id':BASE+'/#local-loop','name':'Local Loop'}
        assert page['@type']=='WebPage' and page['url']==BASE+row['route'] and page['name']==row['h1']
        assert page['description']==row['description'] and page['@id']==BASE+row['route']+'#page'
        assert crumbs['@type']=='BreadcrumbList'
        assert crumbs['itemListElement'][-1]['item']==BASE+row['route']
        assert [c['position'] for c in crumbs['itemListElement']]==list(range(1,len(crumbs['itemListElement'])+1))
        assert set(page)=={'@type','@id','url','name','description'}
        assert len(' '.join(a.text).split())>(150 if row['route']=='/' else 200)
        titles+=a.titles;descriptions+=ds;h1s+=a.h1s
        route_results.append({'route':row['route'],'static_checks':'PASS','canonical':'Configured local self-canonical — NOT HOSTED/PRODUCTION PASS'})
    assert len(set(titles))==len(set(descriptions))==len(set(h1s))==9
    for file,a in parsed.items():
        for href in a.links:
            if href in set(M.get('supplied_primary_citations',[])):
                u=urlsplit(href);assert u.scheme=='https' and u.netloc and not u.username and not u.password and not u.fragment
                continue
            target,frag=resolve(file,href)
            if frag:assert target in parsed and frag in parsed[target].ids
    # Every supplied primary citation is still present on its intended route.
    for integration in M.get('content_integrations',[]):
        actual=parsed[P/integration['file']]
        for citation in integration['unique_citations']:assert citation in actual.links
        assert not any('cursor.com' in h for h in actual.links)
    # Required internal-link coverage.
    byroute={r['route']:P/r['file'] for r in M['routes']}
    guides=['/ac/repair/','/heating/no-heat/','/heat-pumps/repair-or-replace/','/maintenance/']
    for route,file in byroute.items():
        targets={resolve(file,h)[0] for h in parsed[file].links if h not in set(M.get('supplied_primary_citations',[]))}
        required=['/about/','/how-referrals-work/','/privacy/']
        if route in ['/', '/areas/seaford-de/']:required+=guides+['/areas/seaford-de/']
        if route in guides:required+=['/areas/seaford-de/']+[g for g in guides if g!=route]
        for r in required:
            if r!=route:assert byroute[r] in targets,(route,r)
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs=[e.text for e in ET.parse(P/'sitemap.xml').findall('s:url/s:loc',ns)]
    assert set(locs)=={BASE+r['route'] for r in M['routes']} and len(locs)==9
    robots=(P/'robots.txt').read_text();assert 'Disallow: /' in robots and BASE+'/sitemap.xml' in robots
    config=tomllib.loads((ROOT/'netlify.toml').read_text())
    assert (ROOT/config['build']['publish']).resolve()==P and config['build']['publish']=='public'
    assert config['build']['ignore']=='exit 0'
    header=config['headers'][0];assert header['for']=='/*'
    assert header['values']['X-Robots-Tag']=='noindex, nofollow'
    for rule in config.get('redirects',[]):assert rule['status']==404 and rule['to']=='/404.html'
    assert not parsed[P/'404.html'].canon
    assert len(parsed[P/'404.html'].ld)==1
    assert json.loads(parsed[P/'404.html'].ld[0])=={'@context':'https://schema.org','@type':'Organization','@id':BASE+'/#local-loop','name':'Local Loop'}
    assert set((P/'assets/brand').iterdir())=={P/a for a in M['brand_assets']}
    for asset in M['brand_assets']:
        assert (P/asset).is_file()
        if asset.endswith('.svg'):
            root=ET.parse(P/asset).getroot()
            assert not any(e.tag.split('}')[-1] in {'script','text','image','foreignObject'} for e in root.iter())
            assert not any('href' in k for e in root.iter() for k in e.attrib)
    for file,a in parsed.items():
        assert any('dhcg-favicon.svg' in h for h in a.links)
        assert any('dhcg-logo-horizontal.svg' in h for h in a.links)
        assert any('dhcg-logo-horizontal@2x.png' in h for h in a.links)
    css=(P/'styles.css').read_text();assert '@import' not in css and 'url(' not in css
    return {'checked_at':datetime.now(ZoneInfo('America/New_York')).isoformat(),'zone':'America/New_York (EST)','overall':'PASS — static filesystem assertions only','routes':route_results,'other_checks':['10 HTML files incl 404; balanced tags and unique IDs; exact public runtime-only inventory, no Cursor links or visible implementation instructions','All local links/fragments resolve; expected internal-link graph covered; supplied primary citation presence/syntax checked; no Cursor citations','Unique route title/description/H1; configured-domain route self-canonicals','JSON-LD parses and matches visible page/breadcrumb labels','9-route configured-domain draft sitemap; staging robots and noindex meta/header','Netlify TOML parses; correct publish root; auto-build skip; no SPA catchall','No repository metadata or active scripts/forms/calls/external assets; proposed-recipient disclosure qualified inactive; minimal Local Loop Organization only'], 'not_tested':['Browser rendering/accessibility audit','Lighthouse or field CWV','HTTP status, redirects, headers or Netlify behavior','Production SEO/SSR/canonical validity','Primary-source technical review, legal/privacy clearance']}
if __name__=='__main__':
    result=run();(ROOT/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
