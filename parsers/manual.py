"""Owner-supplied exports from legally accessible sources. Never uses private cookies."""
import json
from pathlib import Path
from parsers.exports import imported
ROOT=Path(__file__).resolve().parents[1]
def collect_source(name):
    rows=[]
    for file in sorted((ROOT/'imports').glob('*.json')):
        payload=json.loads(file.read_text())
        if not isinstance(payload,list):raise ValueError('Import must be a JSON array')
        for row in payload:
            if any(s.get('name','').casefold()==name.casefold() for s in row.get('sources',[])):rows.append(imported(row))
    return rows
