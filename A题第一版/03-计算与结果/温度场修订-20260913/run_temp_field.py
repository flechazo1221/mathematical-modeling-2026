"""Isolated no-latent temperature-field revision.

This script deliberately does not replace the frozen COMPUTE outputs.  It uses
the same solver with ``temp_mode='field'`` so Q2--Q4 retain their supplied
thermal properties while no longer setting the internal temperature equal to
the chamber temperature.  Latent heat is not added here because its data
requirements are not present in the problem attachments.
"""
from __future__ import annotations
import csv, hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '04-compute' / 'src'))
from formal_compute import RunConfig, simulate

OUT = ROOT / '04-compute' / 'revision-temp-field-20260913'
RESULTS = OUT / 'results'
LOGS = OUT / 'logs'
RESULTS.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b): h.update(b)
    return h.hexdigest()

cases = [
    ('Q2-M4-field-fine', RunConfig('Q2-M4-field-fine', 140, 36, 5.0, 10800, 2, 'M4', sample_every=600, temp_mode='field')),
    ('Q3-M4-field', RunConfig('Q3-M4-field', 140, 36, 60.0, 259200, 3, 'M4', sample_every=3600, stop_threshold=0.15-1e-6, temp_mode='field')),
    ('Q4-M4-field', RunConfig('Q4-M4-field', 140, 32, 60.0, 259200, 4, 'M4', sample_every=3600, stop_threshold=0.15-1e-6, moving_impl='reference', temp_mode='field')),
]

rows=[]
with (LOGS/'run.log').open('w',encoding='utf-8') as log:
    log.write('command='+' '.join(sys.argv)+'\n')
    log.write('python='+sys.version+'\nplatform='+platform.platform()+'\n')
    for label,cfg in cases:
        started=datetime.now(timezone.utc).isoformat(); log.write(f'START {label} {started}\n'); log.flush()
        run=simulate(cfg)
        m=run['metrics']; last=run['states'][-1]
        row={'label':label,'q':cfg.q,'nr':cfg.nr,'nz':cfg.nz,'dt_s':cfg.dt,'duration_s':cfg.duration,
             'temp_mode':cfg.temp_mode,'center_T_C':float(run['records'][-1]['center_T_C']),
             'surface_T_C':float(run['records'][-1]['surface_T_C']),
             'final_max_C':m['final_max_C'],'final_mean_C':m['final_mean_C'],
             'interpolated_event_time_s':m['interpolated_event_time_s'] or '',
             'reported_event_time_s':m['reported_event_time_s'] or '',
             'normalized_moisture_balance_error':m['normalized_moisture_balance_error'],
             'max_linear_relative_residual':m['max_linear_relative_residual'],
             'runtime_s':m['runtime_s']}
        rows.append(row); log.write('DONE '+json.dumps(row,ensure_ascii=False)+'\n'); log.flush()

with (RESULTS/'temperature-field-summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
manifest={'schema_version':'1.0','stage':'COMPUTE_REVISION','status':'REVIEWABLE_ISOLATED',
          'created_at':datetime.now(timezone.utc).astimezone().isoformat(),
          'source':'04-compute/src/formal_compute.py','source_sha256':sha256(ROOT/'04-compute/src/formal_compute.py'),
          'purpose':'内部显热温度场、无潜热的可计算修订；不覆盖冻结结果',
          'cases':[r for r in rows],
          'data_audit':{'available_for_sensible_temperature':['T0','T_infty(t)','rho(C)','cp(C)','k(C)','h'],
                        'missing_for_latent_coupling':['latent_heat_vaporization','evaporation_or_phase_change_rate_law',
                            'equilibrium_vapor_pressure_or_moisture_potential','internal_temperature_measurements_for_validation'],
                        'conclusion':'无潜热显热温度场可以计算；含潜热模型不能仅凭现有附件唯一确定。'}}
(OUT/'revision-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':manifest['status'],'rows':len(rows)},ensure_ascii=False))
