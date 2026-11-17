"""Record complete attempts, without calling an import or deployment a collection."""
import json,os
from datetime import datetime
from zoneinfo import ZoneInfo

MOSCOW=ZoneInfo('Europe/Moscow')

def same_collection_day(marker,at):
    try:
        stamp=datetime.fromisoformat(marker['attempted_at'].replace('Z','+00:00'))
        current=datetime.fromisoformat(at.replace('Z','+00:00'))
        if stamp.tzinfo is None or current.tzinfo is None or stamp>current:return False
        return marker.get('mode')=='full' and stamp.astimezone(MOSCOW).date()==current.astimezone(MOSCOW).date()
    except (ValueError,TypeError,KeyError,AttributeError):return False

def read_marker(root):
    try:return json.loads((root/'data/collection-run.json').read_text())
    except (FileNotFoundError,ValueError):return {}

def scheduled_already_attempted(root,at,full,imports_only):
    due_only=os.environ.get('GITHUB_EVENT_NAME')=='schedule' or os.environ.get('INVESTSCAN_DUE_ONLY')=='1'
    return due_only and full and not imports_only and same_collection_day(read_marker(root),at)

def source_times(report,previous,started_at,imports_only):
    report.update(processed_this_run=True,checked_this_run=not imports_only,checked_at=previous.get('checked_at') if imports_only else started_at,last_success_at=previous.get('last_success_at'))
    if not imports_only and report.get('status')=='ok' and report.get('live_count',0)>0:
        report['last_success_at']=started_at
    return report

def write_marker(root,started_at,completed_at,reports):
    marker=dict(mode='full',attempted_at=started_at,completed_at=completed_at,run_id=os.environ.get('GITHUB_RUN_ID'),live_sources=[s['name'] for s in reports if s.get('live_count',0)>0],unavailable_sources=[s['name'] for s in reports if s.get('status') in ('blocked','error')])
    path=root/'data/collection-run.json';tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(marker,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
    return marker

def write_summary(reports=None,skipped=False):
    path=os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:return
    if skipped:
        text='Полный проход за этот московский день уже выполнен. Резервный запуск не запрашивал источники.\n'
    else:
        labels={'ok':'Данные получены','partial':'Неполные данные','blocked':'Доступ ограничен','error':'Ошибка','imported':'Импорт','empty':'Нет новых данных','cached':'Не запрашивался'}
        text='| Источник | Прямой сбор, записей | Импорт, записей | Результат |\n|---|---:|---:|---|\n'
        for s in reports or []:
            label='Не запрашивался' if s.get('checked_this_run') is False else labels.get(s.get('status'),'Неизвестно')
            name=str(s.get('name','')).replace('|',' ').replace('\n',' ')
            live=s.get('live_count',0) if s.get('processed_this_run') else 0
            imported=s.get('imported_count',0) if s.get('processed_this_run') else 0
            text+=f'| {name} | {live} | {imported} | {label} |\n'
        text+='\nУспех публикации не подтверждает доступность всех источников. Импорт не является прямым сбором.\n'
    with open(path,'a',encoding='utf-8') as f:f.write(text)
