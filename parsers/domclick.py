"""Public website only. airatb1508's private mobile API and request signing are not used."""
from parsers.manual import collect_source
from parsers.public_source import PublicSource
SEED='https://kazan.domclick.ru/pokupka/kommercheskaya-nedvizhimost'
def collect():
 yield from collect_source('Домклик')
 PublicSource('domclick.ru').get(SEED)
 raise RuntimeError('Домклик: публичная структура коммерческой выдачи пока не подтверждена')
