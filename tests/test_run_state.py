import json
from pathlib import Path
import pytest
from storage.run_state import same_collection_day,scheduled_already_attempted,source_times,write_marker,write_summary

def test_daily_guard_uses_moscow_calendar_not_utc():
    marker={'mode':'full','attempted_at':'2026-11-16T22:00:00Z'}
    assert same_collection_day(marker,'2026-11-17T09:17:00Z')
    assert not same_collection_day(marker,'2026-11-17T22:00:00Z')
    assert not same_collection_day(marker,'2026-11-16T21:59:00Z')

@pytest.mark.parametrize('stamp',['unknown','2026-11-17T03:17:00',None])
def test_bad_marker_cannot_suppress_collection(stamp):
    assert not same_collection_day({'mode':'full','attempted_at':stamp},'2026-11-17T09:17:00Z')

def test_guard_does_not_block_manual_targeted_or_import_runs(tmp_path,monkeypatch):
    (tmp_path/'data').mkdir();(tmp_path/'data/collection-run.json').write_text(json.dumps({'mode':'full','attempted_at':'2026-11-17T03:17:00Z'}))
    monkeypatch.setenv('GITHUB_EVENT_NAME','schedule')
    assert scheduled_already_attempted(tmp_path,'2026-11-17T09:17:00Z',True,False)
    assert not scheduled_already_attempted(tmp_path,'2026-11-17T09:17:00Z',False,False)
    assert not scheduled_already_attempted(tmp_path,'2026-11-17T09:17:00Z',True,True)
    monkeypatch.setenv('GITHUB_EVENT_NAME','workflow_dispatch')
    assert not scheduled_already_attempted(tmp_path,'2026-11-17T09:17:00Z',True,False)
    monkeypatch.setenv('INVESTSCAN_DUE_ONLY','1')
    assert scheduled_already_attempted(tmp_path,'2026-11-17T09:17:00Z',True,False)
    assert not scheduled_already_attempted(tmp_path,'2026-11-17T09:17:00Z',True,True)

def test_backup_skip_has_no_collector_or_geocoder_calls(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    (tmp_path/'data').mkdir();path=tmp_path/'data/listings.json';path.write_text('{"listings":[]}')
    (tmp_path/'data/collection-run.json').write_text(json.dumps({'mode':'full','attempted_at':'2026-11-17T03:17:00Z'}))
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner,'now',lambda:'2026-11-17T09:17:00Z')
    monkeypatch.setenv('GITHUB_EVENT_NAME','schedule');monkeypatch.setenv('INVESTSCAN_SOURCES','all');monkeypatch.setenv('INVESTSCAN_IMPORTS_ONLY','0')
    def forbidden(*a,**k):raise AssertionError('No source or database access should occur')
    monkeypatch.setattr(runner,'Database',forbidden);monkeypatch.setattr(runner,'collect',forbidden)
    runner.run();assert path.read_text()=='{"listings":[]}'

def test_failed_attempt_does_not_erase_last_success_or_claim_import_was_checked():
    previous={'checked_at':'2026-11-16T03:20:00Z','last_success_at':'2026-11-15T03:20:00Z'}
    failed=source_times({'status':'blocked','live_count':0},previous,'2026-11-17T03:20:00Z',False)
    assert failed['checked_at']=='2026-11-17T03:20:00Z' and failed['last_success_at']==previous['last_success_at']
    imported=source_times({'status':'blocked','imported_count':37},failed,'2026-11-17T12:00:00Z',True)
    assert imported['checked_at']==failed['checked_at'] and imported['last_success_at']==failed['last_success_at']
    assert imported['checked_this_run'] is False

def test_full_attempt_with_blocked_sources_is_recorded_without_claiming_success(tmp_path):
    (tmp_path/'data').mkdir()
    marker=write_marker(tmp_path,'2026-11-17T03:17:00Z','2026-11-17T03:25:00Z',[{'name':'ЦИАН','status':'blocked','live_count':0},{'name':'АРР','status':'ok','live_count':472}])
    assert marker['unavailable_sources']==['ЦИАН'] and marker['live_sources']==['АРР']
    assert same_collection_day(marker,'2026-11-17T09:17:00Z')

def test_job_summary_does_not_count_cached_data_as_this_runs_collection(tmp_path,monkeypatch):
    output=tmp_path/'summary.md';monkeypatch.setenv('GITHUB_STEP_SUMMARY',str(output))
    write_summary([{'name':'АРР','status':'ok','live_count':472,'checked_this_run':False,'processed_this_run':False},{'name':'ЦИАН','status':'blocked','live_count':0,'imported_count':37,'checked_this_run':False,'processed_this_run':True}])
    text=output.read_text()
    assert '| АРР | 0 | 0 | Не запрашивался |' in text
    assert '| ЦИАН | 0 | 37 | Не запрашивался |' in text

def test_import_does_not_create_or_refresh_full_attempt_marker(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    (tmp_path/'data').mkdir();marker=tmp_path/'data/collection-run.json'
    before=json.dumps({'mode':'full','attempted_at':'2026-11-16T03:17:00Z'});marker.write_text(before)
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setenv('INVESTSCAN_SOURCES','all');monkeypatch.setenv('INVESTSCAN_IMPORTS_ONLY','1');monkeypatch.setenv('INVESTSCAN_DUE_ONLY','1')
    monkeypatch.setattr(runner,'imports_for',lambda name:[])
    runner.run();assert marker.read_text()==before
