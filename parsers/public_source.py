"""Ordinary public HTTPS requests. No proxy rotation, fingerprint spoofing or challenge solving."""
import time
from urllib.parse import urljoin,urlsplit
import httpx
from parsers.base import USER_AGENT
class SourceUnavailable(RuntimeError):pass
class PublicSource:
 def __init__(self,domain,delay=10):self.domain=domain;self.delay=delay;self.last=0;self.client=httpx.Client(timeout=30,headers={'User-Agent':USER_AGENT},follow_redirects=False)
 def get(self,url,redirects=0):
  p=urlsplit(url)
  if p.scheme!='https' or not(p.hostname==self.domain or (p.hostname or '').endswith('.'+self.domain)):raise ValueError('Source URL outside allowed domain')
  if redirects>5:raise SourceUnavailable('Too many redirects')
  time.sleep(max(0,self.delay-(time.monotonic()-self.last)))
  try:r=self.client.get(url)
  finally:self.last=time.monotonic()
  if r.status_code in (401,403,429):raise SourceUnavailable(f'HTTP {r.status_code}: доступ ограничен; запросы источника остановлены')
  if r.is_redirect:return self.get(urljoin(url,r.headers['location']),redirects+1)
  r.raise_for_status();lower=r.text.lower()
  if any(t in lower for t in ['<title>site unavailable','<title>captcha','verify you are human','подтвердите, что вы не робот','/__qrator/qauth','checking your browser']):raise SourceUnavailable('Страница недоступности или защитной проверки; без обхода и повторов')
  return r.text
