"""CPU contracts only; synthetic records never count as GPU performance evidence."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import analyze_recon_c1_session005 as audit
spec=importlib.util.spec_from_file_location('existing004fixtures',ROOT/'tests/test_analyze_sglang_results_004.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class LayersTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.AnalysisTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.native=self.fixture.native;self.row=self.fixture.run['rows'][0]
    def parse(self):return audit.native_layers((json.dumps(self.native)+'\n').encode(),self.row)
    def test_empty_body_is_separate_diagnostic_not_an_added_official_threshold(self):
        self.native.update(generated_texts=['']*8,ttfts=[0]*8,itls=[[] for _ in range(8)])
        result=self.parse();self.assertTrue(result['native_arrays_counts_and_metrics_consistent'])
        self.assertEqual(result['visible_body_additional_check']['empty_or_whitespace_indices'],list(range(8)))
        self.assertFalse(result['visible_body_additional_check']['is_official_performance_threshold'])
        self.assertFalse(result['exact_output_tokens_verified_from_raw_SSE'])
    def test_non_string_body_still_fails_structural_contract(self):
        self.native['generated_texts']=[None]*8;self.assertFalse(self.parse()['native_arrays_counts_and_metrics_consistent'])
    def test_missing_itl_array_is_unknown_and_structurally_invalid(self):
        self.native['itls']=None;r=self.parse();self.assertFalse(r['native_arrays_counts_and_metrics_consistent'])
        self.assertIsNone(r['per_request_itl_sample_counts']);self.assertIsNone(r['native_stream_timing_coverage']['requests_with_itl_samples'])
    def test_request_errors_and_length_mismatch_still_fail(self):
        for key,value in [('errors',['error']*8),('output_lens',[1023]*8),('completed',7)]:
            old=self.native[key];self.native[key]=value
            self.assertFalse(self.parse()['native_arrays_counts_and_metrics_consistent']);self.native[key]=old
    def test_infinity_is_in_memory_only_and_nested_nonfinite_refused(self):
        raw=(json.dumps(self.native)+'\n').encode();before=bytes(raw);r=audit.native_layers(raw,self.row)
        self.assertEqual(raw,before);self.assertEqual(r['normalizations_in_memory'][0]['path'],'$.request_rate')
        self.native['server_info']={'bad':float('nan')}
        with self.assertRaises(ValueError):self.parse()

class MetricsTests(unittest.TestCase):
    model='/model/exact'
    def raw(self,value):
        return ('# TYPE vllm:generation_tokens_total counter\n'
          f'vllm:generation_tokens_total{{engine="0",model_name="{self.model}"}} {value}\n').encode()
    def test_counter_reset_rejected(self):
        with self.assertRaisesRegex(ValueError,'reset'):audit.paired_metrics(self.raw(10),self.raw(9),self.model)
    def test_foreign_model_duplicate_labels_and_nonfinite_rejected(self):
        for raw in [self.raw(1).replace(b'/model/exact',b'/foreign'),self.raw('NaN'),self.raw(1)+self.raw(1),
                    self.raw(1).replace(b'engine="0"',b'engine="0",engine="0"')]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):audit.metric_samples(raw,self.model)
    def test_missing_counter_stays_unknown_not_zero(self):
        r=audit.paired_metrics(self.raw(0),self.raw(32),self.model)
        self.assertIsNone(r['delta']['request_success_total']);self.assertFalse(r['expected_counts_and_token_cap_sum_match'])
    def test_new_series_requires_a_preexisting_family_declaration(self):
        with self.assertRaisesRegex(ValueError,'family'):audit.paired_metrics(b'# HELP irrelevant\n',self.raw(1),self.model)
    def test_matched_36_requests_caps_and_histograms_remain_conditional_not_raw_SSE_proof(self):
        def snapshot(done):
            rows=[]
            values={'generation_tokens_total':32896,'request_generation_tokens_sum':32896,'request_generation_tokens_count':36,
                    'request_params_max_tokens_sum':32896,'request_params_max_tokens_count':36}
            for name,value in values.items():rows.append(f'vllm:{name}{{engine="0",model_name="{self.model}"}} {value if done else 0}')
            rows.append(f'vllm:request_success_total{{engine="0",finished_reason="length",model_name="{self.model}"}} {36 if done else 0}')
            for kind in ['request_generation_tokens','request_params_max_tokens']:
                for le,value in [('50.0',4),('2000.0',36),('+Inf',36)]:
                    rows.append(f'vllm:{kind}_bucket{{engine="0",le="{le}",model_name="{self.model}"}} {value if done else 0}')
            return ('\n'.join(rows)+'\n').encode()
        r=audit.paired_metrics(snapshot(False),snapshot(True),self.model)
        self.assertTrue(r['expected_counts_and_token_cap_sum_match']);self.assertTrue(r['generation_and_requested_cap_bucket_deltas_match'])
        self.assertEqual(r['delta']['request_success_by_reason'],{'length':36})
        self.assertFalse(r['saturation_inference']['raw_SSE_per_request_exact_token_counts_independently_verified'])
        self.assertEqual(len(r['saturation_inference']['semantic_assumptions']),3)

class SchemaTests(unittest.TestCase):
    def test_session005_schema_only_without_relabelling(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);matrix=base/'project/evidence/session005/recon-c1-001/matrix';matrix.mkdir(parents=True)
            remote=audit.PROJECT+'/evidence/session005/recon-c1-001/matrix';run={'output_dir':remote}
            raw=audit.common.encode(run);(matrix/'run.json').write_bytes(raw)
            script={'archive_path':'source.py','source':'/source.py','size':1,'sha256':'a'*64}
            m={'schema':audit.SCHEMA,'project':audit.PROJECT,'script_hashes_unchanged':True,'script_hashes_before':[script],'script_hashes_after':[script],
              'files':[{'archive_path':'project/evidence/session005/recon-c1-001/matrix/run.json','source':remote+'/run.json','size':len(raw),'sha256':audit.common.sha(raw)}]}
            p=base/'export-manifest.json';p.write_bytes(audit.common.encode(m));archive=audit.common.Archive(matrix)
            seal=audit.ExportSeal005(p,audit.common.sha(p.read_bytes()),archive,run);self.assertEqual(seal.summary['schema'],audit.SCHEMA)
            m['schema']='hg-session004-evidence-export-v1';p.write_bytes(audit.common.encode(m))
            with self.assertRaisesRegex(ValueError,'schema'):audit.ExportSeal005(p,audit.common.sha(p.read_bytes()),archive,run)

if __name__=='__main__':unittest.main()
