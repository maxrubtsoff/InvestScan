"""Домклик adapter: only authorized exports until a permitted discovery API is available."""
from parsers.manual import collect_source
def collect():return collect_source('Домклик')
