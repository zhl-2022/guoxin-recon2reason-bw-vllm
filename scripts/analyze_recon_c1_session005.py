#!/usr/bin/env python3
"""Read-only session005 c1 audit. Preserve Infinity raw bytes; separate every evidence layer."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from decimal import Decimal
import io
import json
import math
from pathlib import Path
import re
import zipfile

import analyze_sglang_results_004 as common
import collect_vllm_metrics_004 as prom

PROJECT='/root/private_data/guoxin-hackathon-20261023-session005-recon-c1'
RUN_ID='c78f8f7f9b24488a9d0d529a5ad28f0f'
SCHEMA='hg-session005-evidence-export-v1'
FROZEN_BUNDLE_SHA='4b05728f2f5e3858f59ecb59ad34ddbb7f4636630a1946595a7f42cfef78fc4b'
FROZEN_MANIFEST_SHA='8debc32a394545939e20f93c7bc8d2f0d702191bbdb1ae0666e71d62ad18100c'
METRICS={'vllm:generation_tokens_total','vllm:request_success_total',
    *['vllm:'+kind+suffix for kind in ['request_generation_tokens','request_params_max_tokens'] for suffix in ['_sum','_count','_bucket']]}

class ExportSeal005:
    """Explicit session005 schema; never rewrite it to impersonate a session004 export."""
    def __init__(self,path,expected_sha256,archive,run):
        path=Path(path).absolute();common.no_links(path);self.archive=common.Archive(path.parent)
        raw=self.archive.read(path.name)
        if not re.fullmatch('[0-9a-f]{64}',expected_sha256 or '') or common.sha(raw)!=expected_sha256:raise ValueError('Independent manifest SHA missing/differs')
        manifest,_=common.parse_json(raw)
        if manifest.get('schema')!=SCHEMA or manifest.get('project')!=PROJECT or manifest.get('script_hashes_unchanged') is not True:raise ValueError('Session005 schema/project/source stability differs')
        keys=('archive_path','source','size','sha256');before=manifest.get('script_hashes_before');after=manifest.get('script_hashes_after')
        if not isinstance(before,list) or not before or not isinstance(after,list) or [{k:x[k] for k in keys} for x in before]!=[{k:x[k] for k in keys} for x in after]:raise ValueError('Source seal differs before/after')
        self.scripts={common.relative(x['archive_path']):x for x in before};self.files={common.relative(x['archive_path']):x for x in manifest['files']}
        if len(self.scripts)!=len(before) or len(self.files)!=len(manifest['files']):raise ValueError('Duplicate source/payload seal')
        for item in before:
            if type(item['size']) is not int or item['size']<0 or not re.fullmatch('[0-9a-f]{64}',item['sha256']):raise ValueError('Invalid source seal')
        self.prefix=archive.root.relative_to(path.parent.resolve()).as_posix()
        if not self.prefix.startswith('project/'):raise ValueError('Run is not inside exported project')
        self.remote_root=PROJECT+'/'+self.prefix[len('project/'):]
        if run.get('output_dir')!=self.remote_root:raise ValueError('Run output path differs from export source path')
        self.summary={'manifest_path':str(path),'manifest_sha256':common.sha(raw),'schema':SCHEMA,
            'before_after_script_hashes_identical':True,'source_payloads_not_reconstructed':True,
            'capture_semantics':manifest.get('capture_semantics'),'source_hash_count':len(before)}
        self.verify_payload('run.json',archive.read('run.json'))
    def bound(self,key):
        key=common.relative(key);raw=self.archive.read(key);item=self.files.get(key)
        expected_source=PROJECT+'/'+key[len('project/'):] if key.startswith('project/') else None
        if not item or item.get('sha256')!=common.sha(raw) or item.get('size')!=len(raw) or (expected_source and item.get('source')!=expected_source):raise ValueError('Payload source/size/SHA differs: '+key)
        return raw
    def verify_payload(self,name,raw):
        key=self.prefix+'/'+common.relative(name);bound=self.bound(key)
        if bound!=raw:raise ValueError('Run payload snapshot differs')
    def script(self,name):
        key=self.prefix+'/'+common.relative(name);item=self.scripts.get(key)
        if not item or item.get('source')!=self.remote_root+'/'+name:raise ValueError('Missing/different actual source seal: '+name)
        return {'path':name,'sha256':item['sha256'],'bytes':item['size'],'source_payload_archived':False,
            'proof_type':'session005_export_before_after_source_hash_only','remote_source':item['source'],'export_manifest_sha256':self.summary['manifest_sha256']}

def native_layers(raw,row):
    parsed=common.native_result(raw,row);data=parsed['native_record'];issues=list(parsed['issues'])
    texts=data.get('generated_texts');typed_texts=isinstance(texts,list) and len(texts)==row['expected_requests'] and all(isinstance(x,str) for x in texts)
    if typed_texts and 'empty or non-string generated text' in issues:issues.remove('empty or non-string generated text')
    # The original body screen is retained explicitly, without turning it into
    # an additional contest threshold or silently dropping it.
    empty=[i for i,x in enumerate(texts) if not x.strip()] if typed_texts else None
    ttfts=data.get('ttfts');itls=data.get('itls')
    coverage={'positive_ttft_requests':sum(type(x) in (int,float) and x>0 for x in ttfts) if isinstance(ttfts,list) else None,
        'zero_ttft_requests':sum(type(x) in (int,float) and x==0 for x in ttfts) if isinstance(ttfts,list) else None,
        'requests_with_itl_samples':sum(isinstance(x,list) and bool(x) for x in itls) if isinstance(itls,list) else None,
        'all_client_stream_timing_fields_are_not_independent_raw_SSE_capture':True}
    return {'native_contract_issues':issues,'native_arrays_counts_and_metrics_consistent':not issues,
        'normalizations_in_memory':parsed['normalizations'],'client_reported_metrics':parsed['metrics'],
        'client_reported_input_lens':data.get('input_lens'),'client_reported_output_lens':data.get('output_lens'),
        'request_errors':data.get('errors'),'per_request_ttfts_seconds':data.get('ttfts'),
        'per_request_itl_sample_counts':[len(x) if isinstance(x,list) else None for x in itls] if isinstance(itls,list) else None,
        'native_stream_timing_coverage':coverage,
        'visible_body_additional_check':{'all_entries_are_strings':typed_texts,'empty_or_whitespace_indices':empty,
            'nonempty_text_count':len(texts)-len(empty) if typed_texts else None,'passed':typed_texts and not empty,
            'is_official_performance_threshold':False,'is_semantic_accuracy_evaluation':False},
        'output_lens_can_use_requested_length_fallback':True,'per_request_output_lens_usage_vs_fallback_origin_recorded':False,
        'server_actual_prompt_tokens_per_request_verified':False,'exact_output_tokens_verified_from_raw_SSE':False,
        'stream_terminal_framing_verified':False,'raw_SSE_usage_captured':False,'boundary':common.BOUNDARY}

def metric_samples(raw,model):
    result={};families=set()
    for line in raw.decode('utf-8',errors='strict').splitlines():
        if line.startswith('# TYPE '):families.add(line.split()[2]);continue
        if not line or line.startswith('#'):continue
        name=re.split(r'[\s{]',line,1)[0]
        if name not in METRICS:continue
        match=prom.LINE.fullmatch(line)
        if not match:raise ValueError('Malformed/nonfinite selected metric')
        labels={};block=match.group('labels')
        if block:
            value=block[1:-1];offset=0
            while offset<len(value):
                label=prom.LABEL.match(value,offset)
                if not label or label.group(1) in labels:raise ValueError('Malformed/duplicate metric label')
                labels[label.group(1)]=json.loads('"'+label.group(2)+'"');offset=label.end()
                if offset<len(value):
                    if value[offset]!=',':raise ValueError('Malformed label delimiter')
                    offset+=1
                    if offset==len(value):raise ValueError('Trailing label delimiter')
        if labels.get('model_name')!=model or labels.get('engine')!='0':raise ValueError('Metric model/engine differs from owned runtime')
        number=Decimal(match.group('value'))
        if not number.is_finite() or number<0 or number!=number.to_integral_value():raise ValueError('Expected integral finite nonnegative token/request metric')
        key=(name,tuple(sorted(labels.items())))
        if key in result:raise ValueError('Duplicate metric series')
        result[key]=int(number)
    return result,families

def paired_metrics(before_raw,after_raw,model):
    before,families=metric_samples(before_raw,model);after,_=metric_samples(after_raw,model)
    delta={};absent=[]
    for key in set(before)|set(after):
        if key not in after:raise ValueError('Selected metric series disappeared')
        previous=before.get(key)
        if previous is None:
            family=key[0][:-6] if key[0].endswith('_total') else key[0]
            if family not in families and key[0] not in families:raise ValueError('New counter series lacks pre-existing declared family')
            previous=0;absent.append({'name':key[0],'labels':dict(key[1])})
        if after[key]<previous:raise ValueError('Counter reset/decrease inside paired snapshots')
        delta[key]=after[key]-previous
    def total(name):
        values=[v for (n,_),v in delta.items() if n==name]
        return sum(values) if values else None
    success={}
    for (name,labels),value in delta.items():
        if name=='vllm:request_success_total':
            reason=dict(labels).get('finished_reason',dict(labels).get('finish_reason','unknown'));success[reason]=success.get(reason,0)+value
    summary={name.removeprefix('vllm:'):total(name) for name in METRICS if not name.endswith('_bucket')}
    summary['request_success_by_reason']=success
    buckets={kind:{dict(labels)['le']:value for (name,labels),value in delta.items() if name=='vllm:'+kind+'_bucket'} for kind in ['request_generation_tokens','request_params_max_tokens']}
    condition=(summary['request_generation_tokens_count']==summary['request_params_max_tokens_count']==summary['request_success_total']==36
        and summary['request_generation_tokens_sum']==summary['request_params_max_tokens_sum']==summary['generation_tokens_total']==32896)
    return {'paired_snapshots_available':True,'before_sha256':common.sha(before_raw),'after_sha256':common.sha(after_raw),
        'delta':summary,'histogram_bucket_deltas':buckets,'series_absent_before_treated_as_zero':absent,
        'absent_series_policy':'Only after a matching counter family TYPE declaration exists in the before snapshot',
        'expected_POSTs':36,'expected_measured_requests':32,'expected_warmups':4,'expected_cap_sum':32896,
        'expected_counts_and_token_cap_sum_match':condition,
        'generation_and_requested_cap_bucket_deltas_match':(buckets['request_generation_tokens']==buckets['request_params_max_tokens']) if all(buckets.values()) else None,
        'saturation_inference':{'paired_finished_counts_and_sums_match_expected':condition,
            'conditional_math':'For the same 36 finished requests, if each actual output t_i <= requested cap m_i, equal sums imply every t_i=m_i.',
            'semantic_assumptions':['Native DAS fork uses the audited vLLM finished-request generation/max-token histogram semantics',
                'The same observations populate both histograms and actual output cannot exceed each corresponding requested cap',
                'All model POSTs in this owned run are the 32 measured requests and four 32-token warmups'],
            'raw_SSE_per_request_exact_token_counts_independently_verified':False},
        'official_performance_accepted':False}

def source_bundle_proof(seal,parent):
    root=Path(__file__).resolve().parents[1];raw=(root/'dist/session005-recon-c1.zip').read_bytes()
    if common.sha(raw)!=FROZEN_BUNDLE_SHA:raise ValueError('Local frozen c1 source ZIP differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        frozen=z.read('recon-c1-source-manifest.json');captured=seal.bound(parent+'/source-manifest.json')
        manifest,_=common.parse_json(frozen);snapshot,_=common.parse_json(captured)
        if common.sha(frozen)!=FROZEN_MANIFEST_SHA or snapshot!=manifest:raise ValueError('Actual c1 source manifest differs from fixed bundle')
        observed=[];missing=[]
        records=list(seal.scripts.values())+list(seal.files.values())
        for item in manifest['files']:
            expected_source=PROJECT+'/'+item['path'];matches=[r for r in records if r.get('source')==expected_source]
            if not matches:missing.append(expected_source);continue
            if any(r['sha256']!=item['sha256'] or r['size']!=item['size'] for r in matches):raise ValueError('Actual source differs from frozen bundle: '+item['path'])
            observed.append({'source':expected_source,'sha256':item['sha256'],'size':item['size']})
    return {'frozen_bundle_sha256':FROZEN_BUNDLE_SHA,'source_manifest_sha256':FROZEN_MANIFEST_SHA,
        'captured_source_manifest_sha256':common.sha(captured),'manifest_objects_equal':True,
        'source_manifest_format_boundary':'Controller reserializes the source manifest with LF; frozen Windows-generated source JSON may use CRLF. Both original byte hashes remain recorded.',
        'observed_actual_source_seals_match':observed,'sources_without_direct_export_seal':missing,
        'all_seven_files_directly_sealed':len(observed)==7,'source_manifest_is_not_alone_proof_of_execution':True}

def runtime_binding(archive,seal,run):
    snapshots={};config_raws=[]
    for phase in ['before','after']:
        claim=run.get('runtime_'+phase,{})
        if claim.get('run_id')!=RUN_ID or claim.get('server_framework_verified') is not True:raise ValueError('Runtime snapshot identity/framework differs')
        files=claim.get('files',[])
        if {x['name'] for x in files}!={'state.json',f'config-{RUN_ID}.json','server.log','supervisor.log'} or len(files)!=4:raise ValueError('Runtime snapshot exact file set differs')
        data={}
        for item in files:
            name='runtime/'+phase+'/'+common.relative(item['name']);raw=archive.read(name);seal.verify_payload(name,raw)
            if len(raw)!=item['bytes'] or common.sha(raw)!=item['sha256']:raise ValueError('Producer runtime snapshot SHA differs')
            data[item['name']]=raw
        state,_=common.parse_json(data['state.json']);config,_=common.parse_json(data[f'config-{RUN_ID}.json']);config_raws.append(data[f'config-{RUN_ID}.json'])
        if state.get('run_id')!=RUN_ID or config.get('run_id')!=RUN_ID or state.get('status')!='ready':raise ValueError('Before/after runtime is not same ready run')
        expected={'model_path':run['model_path'],'served_name':run['served_model_name'],'framework':'vllm','precision':'bf16','port':30000,'tp':1,'max_len':32768,'mem_frac':.85}
        if any(config.get(k)!=v for k,v in expected.items()):raise ValueError('Runtime configuration differs from session004 A parameters')
        command=config['command']
        for key,value in {'--max-num-seqs':'16','--max-model-len':'32768','--gpu-memory-utilization':'0.85','--dtype':'bfloat16'}.items():
            if command.count(key)!=1 or command[command.index(key)+1]!=value:raise ValueError('Runtime command parameter differs: '+key)
        if '--enforce-eager' not in command or json.loads(command[command.index('--limit-mm-per-prompt')+1])!={'image':2,'video':0}:raise ValueError('Runtime eager/image limits differ')
        snapshots[phase]={'state':state,'config_sha256':common.sha(data[f'config-{RUN_ID}.json'])}
    if config_raws[0]!=config_raws[1]:raise ValueError('Runtime config changed during workload')
    for key in ['supervisor_pid','supervisor_token','server_pid','server_token','command']:
        if snapshots['before']['state'].get(key)!=snapshots['after']['state'].get(key):raise ValueError('Runtime process/command identity changed during workload')
    return {'before_after_same_owned_ready_processes_and_config':True,'snapshots':snapshots}

def analyze(run_path,analysis_dir,manifest_path,manifest_sha):
    run_path=Path(run_path).absolute();analysis_dir=Path(analysis_dir).absolute();common.no_links(run_path);common.no_links(analysis_dir)
    if run_path.name!='run.json' or analysis_dir.exists():raise ValueError('Use run.json and a fresh analysis directory')
    archive=common.Archive(run_path.parent);raw_run=archive.read('run.json');run,_=common.parse_json(raw_run)
    if analysis_dir.resolve().is_relative_to(archive.root) or archive.root.is_relative_to(analysis_dir.resolve()):raise ValueError('Output must be independent of input archive')
    if run.get('expected_run_id')!=RUN_ID or not isinstance(run.get('rows'),list) or not 1<=len(run['rows'])<=4:raise ValueError('Different c1 run identity/row count')
    seal=ExportSeal005(manifest_path,manifest_sha,archive,run);provenance=common.source_provenance(archive,run,seal)
    inventory=archive.inventory_native();rows=[];seen=set()
    for producer in run['rows']:
        name,issues=common.row_contract(run,producer)
        if producer.get('warmup_requests')!=1:issues.append('Session005 c1 requires exactly one original warmup per row')
        if name in seen or producer['concurrency']!=1:raise ValueError('Duplicate or non-c1 selected row')
        seen.add(name);item={'name':name,'round':producer['round'],'scored_round':producer['scored_round'],'text_target_tokens':producer['text_target_tokens'],
            'concurrency':1,'expected_requests':producer['expected_requests'],'original_producer_status':producer.get('status'),
            'prompt_length_boundary':run.get('input_length_boundary'),
            'original_result_error':producer.get('result_error'),'process_status':producer.get('process_status'),'exit_code':producer.get('exit_code'),
            'child_reaped':producer.get('child_reaped'),'client_wall_seconds':producer.get('client_wall_seconds'),'native_client_execution_and_contract_passed':False}
        try:
            raw=archive.read('native/'+name+'.jsonl');seal.verify_payload('native/'+name+'.jsonl',raw)
            if producer.get('native_result_sha256')!=common.sha(raw):issues.append('Producer native SHA differs')
            layer=native_layers(raw,producer);item.update(layer);issues.extend(layer['native_contract_issues'])
            item['native_file_sha256']=common.sha(raw);item['native_file_bytes']=len(raw)
            log=archive.read(name+'.log');seal.verify_payload(name+'.log',log)
            if producer.get('log_sha256')!=common.sha(log) or producer.get('log')!=run['output_dir']+'/'+name+'.log':issues.append('Producer execution log source/SHA differs')
            item['client_log_sha256']=common.sha(log)
        except (ValueError,OSError,UnicodeError) as exc:issues.append('Native parse/read failed: '+str(exc))
        exited=(producer.get('process_status')=='exited' and type(producer.get('exit_code')) is int and producer['exit_code']==0 and producer.get('child_reaped') is True)
        item['native_process_exited_zero_and_reaped']=exited
        if not exited:issues.append('Client process did not exit zero and reap')
        if not common.finite_nonnegative(producer.get('client_wall_seconds')) or producer.get('client_wall_seconds',0)<=0:issues.append('Client wall duration is not positive finite')
        if producer.get('status') not in ['complete_client_report','invalid_native_result'] or (producer.get('status')=='invalid_native_result' and producer.get('result_error')!='Infinity'):issues.append('Producer status differs from completed/specific Infinity parse failure')
        if not provenance['verified_for_reanalysis']:issues.append('Producer/upstream provenance not closed')
        item['native_client_execution_and_contract_passed']=not issues;item['issues']=issues;rows.append(item)
    expected={(n,r) for n in [4096,16384] for r in [1,2]};selected={(r['text_target_tokens'],r['round']) for r in rows}
    parent=seal.prefix.rsplit('/',1)[0];controller={};metrics={'paired_snapshots_available':False};cleanup=None
    bundle_proof=source_bundle_proof(seal,parent)
    runtime_proof=runtime_binding(archive,seal,run)
    try:
        start,_=common.parse_json(seal.bound(parent+'/run-start.json'));final,_=common.parse_json(seal.bound(parent+'/run-final.json'))
        if start.get('run_id')!=RUN_ID or final.get('plan',{}).get('run_id')!=RUN_ID:raise ValueError('Outer controller identity differs')
        cleanup,_=common.parse_json(seal.bound(parent+'/independent-cleanup.json'))
        controller={'start':start,'final':final,'cleanup':cleanup}
        model=run['model_path'];b=seal.bound(parent+'/metrics-before-client.txt');a=seal.bound(parent+'/metrics-after-client.txt')
        for filename,raw in [('metrics-before-client.txt',b),('metrics-after-client.txt',a)]:
            identity,_=common.parse_json(seal.bound(parent+'/'+filename+'.identity.json'))
            if identity.get('owned_run_id')!=RUN_ID or identity.get('sha256')!=common.sha(raw) or identity.get('status')!=200 or identity.get('model_request_sent') is not False:raise ValueError('Metrics snapshot binding differs')
        metrics=paired_metrics(b,a,model)
        server_log=seal.bound(parent+'/runtime-after-stop/server.log').decode('utf-8')
        posts=re.findall(r'"POST ([^ ]+) HTTP/1\.1" ([0-9]{3})',server_log)
        metrics['owned_server_POST_log']={'observed_POSTs':len(posts),'POST_path_status_pairs':[list(x) for x in posts],
            'exactly_expected_chat_POSTs_all_200':len(posts)==36 and all(x==('/v1/chat/completions','200') for x in posts)}
        stopped_state,_=common.parse_json(seal.bound(parent+'/runtime-after-stop/state.json'))
        cleanup_evidence=(cleanup.get('run_id')==RUN_ID and cleanup.get('cleanup_verified') is True and cleanup.get('stop_called') is True
            and cleanup.get('stop_step',{}).get('exit_code')==0 and cleanup.get('port_30000_open') is False
            and cleanup.get('owned_processes_alive')=={'server':False,'supervisor':False}
            and stopped_state.get('run_id')==RUN_ID and stopped_state.get('status')=='stopped' and stopped_state.get('reason')=='stop requested')
        controller.update(copied_state_after_stop=stopped_state,independent_cleanup_record_consistent=cleanup_evidence,
            frozen_source_self_check_after_run_passed=final.get('frozen_sources_unchanged') is True)
    except (OSError,ValueError,KeyError) as exc:metrics['audit_issue']=str(exc)
    archive.verify_unchanged();seal.archive.verify_unchanged()
    passing=[r for r in rows if r['native_client_execution_and_contract_passed']]
    empty_body_lists=[r.get('visible_body_additional_check',{}).get('empty_or_whitespace_indices') for r in rows]
    result={'schema':'session005-recon-c1-audit-v1','utc':datetime.now(timezone.utc).isoformat(),
        'analyzer_sha256':common.sha(Path(__file__).read_bytes()),'shared_parser_sha256':common.sha(Path(common.__file__).read_bytes()),
        'shared_prometheus_grammar_sha256':common.sha(Path(prom.__file__).read_bytes()),
        'source_run_sha256':common.sha(raw_run),'source_run_path':str(run_path),'source_provenance':provenance,
        'export_seal':seal.summary,'frozen_source_bundle_proof':bundle_proof,'runtime_binding':runtime_proof,'native_inventory':inventory,'rows':rows,'controller':controller,'server_paired_metrics':metrics,
        'summary':{'selected_c1_four_rows_planned':selected==expected,'selected_c1_rows':len(rows),'native_client_contract_pass_rows':len(passing),
            'native_client_reported_requests':sum(r['expected_requests'] for r in passing),
            'visible_body_additional_check_pass_rows':sum(r.get('visible_body_additional_check',{}).get('passed') is True for r in rows),
            'empty_body_total':sum(map(len,empty_body_lists)) if all(isinstance(x,list) for x in empty_body_lists) else None,
            'rows_without_a_typed_text_array':sum(x is None for x in empty_body_lists),
            'this_is_a_separate_session005_c1_run':True,'full_twelve_row_same_run_matrix_complete':False,
            'official_accuracy_verified':False,'official_performance_accepted':False,'submission_ready':False},
        'boundaries':['Only top-level request_rate Infinity is normalized in memory; original native bytes are never changed or republished as normalized raw',
            common.BOUNDARY,'Nonempty client text is an additional diagnostic, not a published contest performance threshold',
            'Reported native throughput may use requested-length fallback; TTFT/TPOT need visible stream samples and are not independent raw-SSE proof',
            'Paired server metrics are a separate aggregate/conditional inference layer; do not silently relabel client output_lens as raw server usage',
            'Kimi checkpoint download co-run was declared; this is not an isolated official performance measurement'],
        'source_files_modified':False,'GPU_or_model_execution_performed_by_analyzer':False,'normalized_native_artifacts_written':False}
    analysis_dir.mkdir(parents=True,exist_ok=False);raw=common.encode(result)
    with (analysis_dir/'analysis.json').open('xb') as f:f.write(raw)
    manifest={'schema':'session005-recon-c1-analysis-files-v1','files':[{'path':'analysis.json','size':len(raw),'sha256':common.sha(raw)}],
        'source_snapshot_sha256':[{'path':name,'size':len(data),'sha256':common.sha(data)} for name,data in sorted({**archive.raw,**{'export/'+k:v for k,v in seal.archive.raw.items()}}.items())]}
    with (analysis_dir/'analysis-manifest.json').open('xb') as f:f.write(common.encode(manifest))
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--analysis-dir',type=Path,required=True)
    p.add_argument('--export-manifest',type=Path,required=True);p.add_argument('--expected-export-manifest-sha256',required=True);a=p.parse_args(argv)
    try:
        r=analyze(a.run,a.analysis_dir,a.export_manifest,a.expected_export_manifest_sha256)
        print(json.dumps(r['summary'],indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:print(json.dumps({'audit_failed':True,'error':str(exc)}));return 2

if __name__=='__main__':raise SystemExit(main())
