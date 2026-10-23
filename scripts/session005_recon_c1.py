#!/usr/bin/env python3
"""Small session005 c1 controller around the byte-identical session004 runtime/client."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

import recon2reason_runtime as supervisor
import t02_sglang_bench as driver

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_ROOT=Path('/root/private_data/guoxin-hackathon-20261023-session005-recon-c1')
TASK=ROOT/'tasks/recon2reason-bw-vllm'
RUN_ID='c78f8f7f9b24488a9d0d529a5ad28f0f' # uuid.uuid4().hex, fixed once and real checked_run_id tested
MODEL='/root/private_data/SothisAI/model/Aihub/Recon2Reason-Reasoning-4B/main/Recon2Reason-Reasoning-4B'
CLIENT='/root/private_data/sglang-client-004c/bin/python'
SERVER='/usr/bin/python'
FLAGS={'official_accuracy_verified':False,'official_performance_verified':False,'submission_ready':False}
NATIVE_SHA='0edc33da22c07a804c93047f918a4a39a58af90997390c49695d8b39a891d85b'
DRIVER_SHA='ff8eef852e19f336e99884cc031353627ca304c6a7534c22375116758a850000'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def dump(p,v):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')


def source_check():
    supervisor.checked_run_id(RUN_ID)
    m=read(ROOT/'recon-c1-source-manifest.json')
    if m['target_project']!=EXPECTED_ROOT.as_posix() or m['run_id']!=RUN_ID:raise ValueError('Source manifest root/run identity differs')
    for item in m['files']:
        p=ROOT/item['path'];raw=p.read_bytes()
        if p.is_symlink() or len(raw)!=item['size'] or sha(raw)!=item['sha256']:raise ValueError('Frozen source differs: '+item['path'])
    if sha((ROOT/'scripts/recon2reason_runtime.py').read_bytes())!=NATIVE_SHA:raise ValueError('Actual004 runtime identity differs')
    if sha((ROOT/'scripts/t02_sglang_bench.py').read_bytes())!=DRIVER_SHA:raise ValueError('Actual004g client identity differs')
    return m


def environment():
    env=os.environ.copy();env.update({'RECON2REASON_MODEL_PATH':MODEL,'RECON2REASON_SERVED_NAME':MODEL,
        'RECON2REASON_PORT':'30000','RECON2REASON_TP':'1','RECON2REASON_MAX_LEN':'32768',
        'RECON2REASON_MEM_FRAC':'0.85','RECON2REASON_LOAD_TIMEOUT':'600','RECON2REASON_MAX_RUNTIME_SECONDS':'2400',
        'RECON2REASON_STOP_GRACE_SECONDS':'30','RECON2REASON_PYTHON_BIN':SERVER,
        'RECON2REASON_EXTRA_ARGS_JSON':'["--enforce-eager","--max-num-seqs","16","--limit-mm-per-prompt","{\\"image\\":2,\\"video\\":0}"]',
        'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_DATASETS_OFFLINE':'1'})
    return env


def bench_argv(output,total_seconds):
    return [SERVER,str(ROOT/'scripts/t02_sglang_bench.py'),'--run','--client-python',CLIENT,
        '--model-path',MODEL,'--served-model-name',MODEL,'--port','30000','--output-dir',str(output),
        '--timeout-seconds','600','--total-timeout-seconds',str(total_seconds),
        '--load','4096:1','--load','16384:1','--round','1','--round','2',
        '--runtime-dir',str(TASK/'runtime'),'--expected-run-id',RUN_ID,'--allow-client-device-discovery']


def step(argv,log,seconds,env):
    began=time.monotonic();timed_out=False
    with Path(log).open('xb') as f:
        p=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=p.wait(timeout=seconds)
        except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
            timed_out=isinstance(exc,subprocess.TimeoutExpired)
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                p.wait()
            if not timed_out:raise
            code=124
    return {'argv':argv,'exit_code':code,'timed_out':timed_out,'child_reaped':True,'wall_seconds':time.monotonic()-began,'log_sha256':sha(Path(log).read_bytes())}


def owned_state():
    p=TASK/'runtime/state.json';v=read(p) if p.exists() else None
    return v if v and v.get('run_id')==RUN_ID else None


def metrics(out,name):
    if owned_state() is None:raise ValueError('No matching owned service for metrics GET')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:30000/metrics',timeout=5) as r:
        raw=r.read(2*1024*1024+1);status=r.status
    if status!=200 or len(raw)>2*1024*1024:raise ValueError('Metrics status/byte cap')
    p=out/name
    with p.open('xb') as f:f.write(raw)
    dump(out/(name+'.identity.json'),{'utc':utc(),'owned_run_id':RUN_ID,'status':status,'bytes':len(raw),'sha256':sha(raw),'method':'GET','model_request_sent':False})


def cleanup(out,env):
    state=owned_state();record={'utc':utc(),'run_id':RUN_ID,'state_exists_with_matching_identity':state is not None,'stop_called':False}
    if state is None:
        p=TASK/'runtime/state.json';config=TASK/f'runtime/config-{RUN_ID}.json'
        record.update(cleanup_verified=not p.exists() and not config.exists(),scope='No matching state; no stop/signals attempted')
    else:
        record['stop_called']=True;record['stop_step']=step(['bash',str(TASK/'stop.sh'),'--run-id',RUN_ID],out/'stop.log',45,env)
        after=owned_state();record['state_after']=after
        # Always independently check the originally owned PID/start-time tokens,
        # including when a stopped state file was removed or replaced.
        record['owned_processes_alive']={k:supervisor.matches(state.get(k+'_pid',0),state.get(k+'_token')) for k in ['server','supervisor']}
        record['cleanup_verified']=record['stop_step']['exit_code']==0 and not any(record['owned_processes_alive'].values())
    with socket.socket() as s:s.settimeout(2);record['port_30000_open']=s.connect_ex(('127.0.0.1',30000))==0
    record['cleanup_verified']=record['cleanup_verified'] and not record['port_30000_open']
    runtime=TASK/'runtime'
    if runtime.exists():
        saved=out/'runtime-after-stop';saved.mkdir()
        for p in runtime.iterdir():
            if p.is_file() and p.name.endswith(('.json','.log')):
                if p.is_symlink() or p.stat().st_size>50*1024*1024:raise ValueError('Unsafe/oversized runtime evidence')
                shutil.copyfile(p,saved/p.name)
    dump(out/'independent-cleanup.json',record);return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dry-run',action='store_true');a=p.parse_args(argv)
    manifest=source_check();env=environment();supervisor.checked_run_id(RUN_ID)
    plan={'run_id':RUN_ID,'expected_project':EXPECTED_ROOT.as_posix(),'controller_total_seconds':2200,'service_seconds':2400,
        'per_load_seconds':600,'loads':['4096:1','16384:1'],'rounds':[1,2],'measured_requests':32,'warmups':4,
        'expected_POSTs':36,'output_cap_sum_if_all_caps_hit':32896,'co_run_declared_by_root':'Kimi checkpoint download; not an isolated official performance run',
        'historical_task_json_is_not_session005_platform_evidence':True,**FLAGS}
    if a.dry_run:print(json.dumps(plan,indent=2));return 0
    if sys.platform!='linux' or ROOT!=EXPECTED_ROOT:raise ValueError('Run only in the new dedicated Recon c1 project')
    for port in [30119,30000]:
        with socket.socket() as s:
            s.settimeout(2)
            if s.connect_ex(('127.0.0.1',port))==0:raise ValueError('Required port not closed before new service: '+str(port))
    out=ROOT/'evidence/session005/recon-c1-001';out.mkdir(parents=True,exist_ok=False)
    dump(out/'run-start.json',{'utc':utc(),**plan});dump(out/'source-manifest.json',manifest)
    began=time.monotonic();result={'started_utc':utc(),'plan':plan,'steps':[],**FLAGS};code=2;cleaning=False;ready=False
    def interrupted(*_):
        if not cleaning:raise KeyboardInterrupt
    previous=signal.signal(signal.SIGTERM,interrupted)
    try:
        item=step(['bash',str(TASK/'run.sh'),'--run-id',RUN_ID],out/'launch.log',650,env);result['steps'].append(item)
        if item['exit_code']!=0:raise ValueError('Service startup failed')
        ready=True;metrics(out,'metrics-before-client.txt')
        budget=max(1,2200-(time.monotonic()-began)-60)
        item=step(bench_argv(out/'matrix',budget),out/'bench-controller.log',budget,env);result['steps'].append(item)
        result['bench_exit_status']=item['exit_code'];code=item['exit_code']
        result['bench_status_is_not_official_judgment']=True
    except (Exception,KeyboardInterrupt) as exc:
        result['error']={'type':type(exc).__name__,'message':str(exc)};code=130 if isinstance(exc,KeyboardInterrupt) else 2
    finally:
        cleaning=True
        if ready:
            try:metrics(out,'metrics-after-client.txt');result['post_bench_metrics_saved']=True
            except Exception as exc:result['metrics_after_error']=str(exc)
        try:
            record=cleanup(out,env);result['cleanup_verified']=record['cleanup_verified']
            if not record['cleanup_verified']:code=2
        except Exception as exc:result['cleanup_error']=str(exc);code=2
        try:source_check();result['frozen_sources_unchanged']=True
        except Exception as exc:result['source_after_error']=str(exc);code=2
        result.update(ended_utc=utc(),wall_seconds=time.monotonic()-began,controller_exit_code=code)
        dump(out/'run-final.json',result);signal.signal(signal.SIGTERM,previous)
    print(json.dumps({'output':str(out),'controller_exit_code':code,'bench_exit_status':result.get('bench_exit_status'),
        'post_bench_metrics_saved':result.get('post_bench_metrics_saved',False),'cleanup_verified':result.get('cleanup_verified',False),**FLAGS},indent=2));return code


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:print(json.dumps({'error':str(exc),**FLAGS}));raise SystemExit(2)
