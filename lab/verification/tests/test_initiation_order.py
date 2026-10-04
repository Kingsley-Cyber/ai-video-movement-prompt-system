import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lab.compiler.provenance import sha256_value, canonical_json_bytes
from lab.verification.tests.test_verify import _measurement_batch
from lab.verification.verify import compare_initiation_order


def request(paths=None):
    # Explicit synthetic calibration; production has no configured defaults.
    batch = _measurement_batch(source_id='synthetic_onsets', source_sha256='a'*64,
        paths=paths or {'left_hip': [(0,0),(1,0),(1,0),(1,0)],
                       'left_knee': [(0,0),(0,0),(0,0),(1,0)]})
    declaration = {'actor':'actor_A', 'beat_id':'beat_1',
        'interval': {'start_s':0.0,'end_s':6.0},
        'initiation_chain': {'kind':'sequential','root':'left_hip',
                             'path':['left_hip','left_knee'], 'pattern':'upper-lower'}}
    return {'schema':'cpcs.initiation_order_request/1.0',
        'declaration':declaration, 'declaration_sha256':sha256_value(declaration),
        'measurement_batch':batch, 'measurement_sha256':sha256_value(batch),
        'calibration':{'onset_tolerance_s':0.5,'visibility_threshold':0.5},
        'camera':{'motion':'fixed','basis':'caller_declared'}}


def rebind(value):
    batch=value['measurement_batch']
    for observation in batch['observations']:
        observation['id']='measurement_obs_'+hashlib.sha256(canonical_json_bytes({'job_id':batch['job_id'],'claim':observation['claim']})).hexdigest()[:24]
    batch['batch_id']='measurement_batch_'+hashlib.sha256(canonical_json_bytes({k:v for k,v in batch.items() if k!='batch_id'})).hexdigest()[:24]
    value['measurement_sha256']=sha256_value(batch)
    value['declaration_sha256']=sha256_value(value['declaration'])
    return value


class InitiationOrderTests(unittest.TestCase):
    def test_ordered_onset_and_replay(self):
        value=request()
        result=compare_initiation_order(value)
        self.assertEqual(result['status'],'ordered')
        self.assertEqual(result['onsets'], [
            {'joint':'left_hip','start_s':0.0,'end_s':2.0},
            {'joint':'left_knee','start_s':4.0,'end_s':6.0}])
        self.assertEqual(result,compare_initiation_order(copy.deepcopy(value)))
        self.assertEqual(result['measurement_sha256'],value['measurement_sha256'])
        self.assertEqual(result['declaration_sha256'],value['declaration_sha256'])
        self.assertEqual(result['camera']['basis'],'caller_declared')

    def test_reversed_onset(self):
        value=request({'left_hip':[(0,0),(0,0),(0,0),(1,0)],
                       'left_knee':[(0,0),(1,0),(1,0),(1,0)]})
        self.assertEqual(compare_initiation_order(value)['status'],'reversed')

    def test_indistinguishable_onset(self):
        value=request({'left_hip':[(0,0),(1,0),(1,0),(1,0)],
                       'left_knee':[(0,0),(1,0),(1,0),(1,0)]})
        self.assertEqual(compare_initiation_order(value)['status'],'indistinguishable')

    def test_sampling_windows_not_guessed_point_onsets(self):
        value=request({'left_hip':[(0,0),(1,0),(1,0),(1,0)],
                       'left_knee':[(0,0),(0,0),(1,0),(1,0)]})
        self.assertEqual(compare_initiation_order(value)['status'],'indistinguishable')

    def test_tolerance_is_explicit_and_changes_resolution(self):
        value=request();value['calibration']['onset_tolerance_s']=2.0
        self.assertEqual(compare_initiation_order(value)['status'],'indistinguishable')

    def test_missing_track(self):
        value=request({'left_hip':[(0,0),(1,0),(1,0),(1,0)]})
        result=compare_initiation_order(value)
        self.assertEqual(result['status'],'unobservable')
        self.assertEqual(result['reason'],'missing_track')

    def test_occluded_track(self):
        value=request();value['measurement_batch']['observations'][0]['claim']['positions'][1]['visibility']=0.1
        result=compare_initiation_order(rebind(value))
        self.assertEqual(result['status'],'unobservable')
        self.assertEqual(result['reason'],'occluded_track')

    def test_identity_uncertainty(self):
        value=request();value['measurement_batch']['summary']['possible_swap_frames']=1
        result=compare_initiation_order(rebind(value))
        self.assertEqual(result['status'],'unobservable')
        self.assertEqual(result['reason'],'identity_uncertainty')

    def test_camera_ambiguity(self):
        for motion in ['unknown','ambiguous']:
            value=request();value['camera']['motion']=motion
            result=compare_initiation_order(value)
            self.assertEqual(result['status'],'unobservable')
            self.assertEqual(result['reason'],'camera_ambiguity')

    def test_unset_calibration(self):
        for field in ['onset_tolerance_s','visibility_threshold']:
            value=request();value['calibration'][field]=None
            result=compare_initiation_order(value)
            self.assertEqual(result['status'],'uncalibrated')
            self.assertEqual(result['onsets'],[])

    def test_absent_calibration_is_uncalibrated(self):
        value=request();del value['calibration']
        self.assertEqual(compare_initiation_order(value)['status'],'uncalibrated')

    def test_stationary_track_is_unobservable(self):
        value=request({'left_hip':[(0,0)]*4, 'left_knee':[(0,0),(1,0),(1,0),(1,0)]})
        self.assertEqual(compare_initiation_order(value)['status'],'unobservable')

    def test_missing_beat_baseline_is_unobservable(self):
        value=request();value['declaration']['interval']['start_s']=1.0
        result=compare_initiation_order(rebind(value))
        self.assertEqual(result['status'],'unobservable')
        self.assertEqual(result['reason'],'incomplete_beat_coverage')

    def test_wrong_actor_is_not_substituted(self):
        value=request();value['declaration']['actor']='actor_B'
        self.assertEqual(compare_initiation_order(rebind(value))['status'],'unobservable')

    def test_supplied_verdict_rejected(self):
        for key in ['verdict','status','onsets']:
            value=request();value[key]='ordered'
            with self.assertRaises(ValueError): compare_initiation_order(value)
        value=request();value['declaration']['initiation_chain']['verdict']='ordered'
        with self.assertRaises(ValueError): compare_initiation_order(rebind(value))

    def test_hash_tampering_rejected(self):
        for key in ['measurement_batch','declaration']:
            value=request()
            if key=='measurement_batch': value[key]['observations'][0]['claim']['positions'][1]['x']=0.5
            else: value[key]['beat_id']='other_beat'
            with self.assertRaises(ValueError): compare_initiation_order(value)

    def test_detached_observation_rejected(self):
        value=request();value['measurement_batch']['observations'][0]['source_sha256']='b'*64
        with self.assertRaises(ValueError): compare_initiation_order(rebind(value))

    def test_root_and_path_must_agree(self):
        value=request();value['declaration']['initiation_chain']['root']='left_ankle'
        with self.assertRaises(ValueError): compare_initiation_order(rebind(value))

    def test_negative_and_nonfinite_tolerances_rejected(self):
        for tolerance in [-1.0, float('nan'), float('inf')]:
            value=request();value['calibration']['onset_tolerance_s']=tolerance
            with self.assertRaises(ValueError): compare_initiation_order(value)

    def test_public_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json';path.write_text(json.dumps(request()))
            run=subprocess.run([sys.executable,'-m','lab.verification.verify',
                'compare-initiation',str(path)],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(run.stdout)['status'],'ordered')
