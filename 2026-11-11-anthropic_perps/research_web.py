import concurrent.futures as cf
from html.parser import HTMLParser
import json
from pathlib import Path
import requests

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0; self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag=='a': self.links += [v for k,v in attrs if k=='href']
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip(): self.parts.append(data.strip())

def get(url,name=None):
    try:
        r=requests.get(url,timeout=45,headers={'User-Agent':'Mozilla/5.0'})
        p=Text(); p.feed(r.text)
        text='\n'.join(p.parts)
        if name:
            Path('research').mkdir(exist_ok=True)
            Path('research/'+name+'.txt').write_text(url+'\n'+str(r.status_code)+'\n'+text+'\nLINKS\n'+'\n'.join(p.links),encoding='utf-8')
        return url,r.status_code,text,p.links
    except Exception as e: return url,str(e),'',[]

if __name__=='__main__':
    queries=['TradeXYZ ANT Anthropic valuation contract specifications','Ventuals ANTHROPIC price valuation multiplier','Paragon ANTH Anthropic valuation perpetual','Entropy io ANTH Anthropic valuation price']
    for i,q in enumerate(queries):
        url='https://www.google.com/search?gbv=1&hl=en&q='+requests.utils.quote(q)
        result=get(url,'search_'+str(i))
        print(result[0],result[1],result[2][:18000])
