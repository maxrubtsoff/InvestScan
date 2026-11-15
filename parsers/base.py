import time,re
from urllib.parse import urlparse,urljoin
from urllib.robotparser import RobotFileParser
import httpx
USER_AGENT='InvestScan/1.0 (+https://github.com/maxrubtsoff/InvestScan)'
class PublicClient:
    def __init__(self):self.client=httpx.Client(timeout=30,headers={'User-Agent':USER_AGENT},follow_redirects=False);self.robots={};self.last={};self.patterns={}
    def get(self,url,redirects=0):
        if redirects>5:raise RuntimeError("Too many redirects")
        p=urlparse(url);origin=f'{p.scheme}://{p.netloc}'
        if p.scheme!='https' or p.hostname not in ['broker.arrpro.ru','arrpro.ru']:raise ValueError('Host not allowed')
        if origin not in self.robots:
            r=self.client.get(origin+'/robots.txt');r.raise_for_status();rp=RobotFileParser();rp.parse(r.text.splitlines());self.robots[origin]=rp
            patterns=[];active=False
            for line in r.text.splitlines():
                key,sep,value=line.partition(':');key=key.strip().lower();value=value.split('#')[0].strip()
                if key=='user-agent':active=value=='*'
                elif active and key=='disallow' and value:patterns.append('^'+re.escape(value).replace(r'\*','.*').replace(r'\$','$'))
            self.patterns[origin]=patterns
        rp=self.robots[origin]
        # RobotFileParser lacks wildcard support: apply all '*' disallows conservatively too.
        rpath=p.path+('?' + p.query if p.query else '')
        if not rp.can_fetch(USER_AGENT,url):raise ValueError('robots.txt disallows request')
        if any(re.search(pattern,rpath) for pattern in self.patterns[origin]):raise ValueError('robots.txt wildcard disallows request')
        delay=max(10,rp.crawl_delay('*') or 0);time.sleep(max(0,delay-(time.monotonic()-self.last.get(origin,0))))
        r=self.client.get(url);self.last[origin]=time.monotonic()
        if r.status_code in (401,403,429):raise RuntimeError(f'Source blocked HTTP {r.status_code}; no retries')
        r.raise_for_status()
        if any(x in r.text.lower() for x in ['verify you are human','checking your browser','captcha-container']):raise RuntimeError('Human verification; collection stopped')
        if r.is_redirect:
            target=urljoin(url,r.headers['location']);return self.get(target,redirects+1)
        return r.text
