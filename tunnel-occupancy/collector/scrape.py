"""Read Tunnel occupancy from the public page, refuse to invent uncertain values."""
import asyncio, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright
import requests

URL='https://www.nonstopgym.com/occupancy/'
PAT=re.compile(r'(?<!\w)(?:Tunnel|Lausanne\s+Tunnel)(?!\w)',re.I)
PCT=re.compile(r'(?<!\d)(100|\d{1,2})(?:[.,](\d{1,2}))?\s*%')

def from_text(text):
    """Extract percentage only from a compact nearby label, not a whole page."""
    hits=[]
    for m in PAT.finditer(text):
        s=text[max(0,m.start()-70):m.end()+115]
        values=[float(x.group(1)+(('.'+x.group(2)) if x.group(2) else '')) for x in PCT.finditer(s)]
        if len(values)==1: hits.append(values[0])
    unique=set(hits)
    if len(unique)==1:return unique.pop()
    return None

async def collect():
    captures=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=await browser.new_page(locale='en-GB',timezone_id='Europe/Zurich',viewport={'width':1400,'height':980})
        async def response(r):
            try:
                if 'json' in r.headers.get('content-type','') and r.status==200:
                    t=await r.text()
                    if len(t)<120000:captures.append({'url':r.url,'body':t[:120000]})
            except Exception:pass
        page.on('response',response)
        await page.goto(URL,wait_until='domcontentloaded',timeout=60000)
        await page.wait_for_timeout(7500)
        # Select locality if required. Never select a different club.
        try:
            selects=page.locator('select')
            for i in range(await selects.count()):
                s=selects.nth(i)
                options=await s.locator('option').all_text_contents()
                for opt in options:
                    if re.search(r'Lausanne|Vaud',opt,re.I):
                        await s.select_option(label=opt.strip(),timeout=2000)
                        await page.wait_for_timeout(2800)
                        break
        except Exception:pass
        # Extract text from leaf-level DOM elements containing Tunnel.
        candidates=await page.evaluate('''() => [...document.querySelectorAll('body *')].filter(e=>e.children.length===0 && /\\bTunnel\\b/i.test(e.textContent||'')).slice(0,25).map(e=>({text:e.parentElement?.parentElement?.innerText?.slice(0,500)||'', html:e.parentElement?.parentElement?.outerHTML?.slice(0,1500)||''}))''')
        vals=[from_text(c['text']) for c in candidates]
        vals=[v for v in vals if v is not None]
        unique=set(vals)
        value=next(iter(unique)) if len(unique)==1 else None
        if value is None:
            # Scrape diagnostics provide developer with response format without returning wrong data.
            Path('collector-diagnostic.json').write_text(json.dumps({'page_text':(await page.locator('body').inner_text())[:9000],'candidates':candidates,'json_responses':captures[:25]},indent=2))
            await page.screenshot(path='collector-diagnostic.png',full_page=True)
        await browser.close()
    if value is None: raise RuntimeError('Unable to unambiguously identify Tunnel occupancy. See diagnostic artifacts. No sample stored.')
    return value

def save(value):
    url=os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1/occupancy'
    key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
    observed=datetime.now(timezone.utc).isoformat()
    r=requests.post(url,headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':'return=minimal'},json={'observed_at':observed,'percentage':value},timeout=25)
    r.raise_for_status()
    print('Stored',observed,value,'%')

if __name__=='__main__':
    value=asyncio.run(collect())
    print('Tunnel:',value,'%')
    if '--dry-run' not in sys.argv:save(value)
