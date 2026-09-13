from pathlib import Path
import csv, hashlib, json

root = Path(__file__).resolve().parents[2]
out = root / '04-compute' / 'revision-temp-field-20260913'
rows = list(csv.DictReader((out/'results'/'temperature-field-summary.csv').open(encoding='utf-8-sig')))

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

manifest = {
    'schema_version':'1.0', 'stage':'COMPUTE_REVISION', 'status':'REVIEWABLE_ISOLATED',
    'purpose':'将问题二至四的内部温度由烘房温度改为显热温度场；仍不加入潜热；不覆盖冻结结果。',
    'source':'04-compute/revision-temp-field-20260913/formal_compute_temp_field.py',
    'source_sha256':digest(out/'formal_compute_temp_field.py'),
    'results':rows,
    'data_audit':{
        'available_for_sensible_temperature':[
            '初始温度 T0=301.15 K', '附件1烘房温度 T_infty(t)',
            '问题二/三 rho(C), cp(C), k(C)', '问题四 rho(C), cp(C), k(C)',
            '传热系数 h=25 W/(m^2 K)', '几何尺寸及问题四半径 R(t)'
        ],
        'missing_for_latent_heat_coupling':[
            '汽化潜热或等效相变焓 L_v(C,T)',
            '蒸发/相变速率方程或气液平衡关系',
            '内部蒸汽分压、孔隙率/渗透率等气相传输参数',
            '多位置内部温度和含水率实测（用于验证，而非仅求解）'
        ],
        'conclusion':'无潜热显热温度场可以由现有数据计算；含潜热模型的参数和验证数据不完整，不能唯一确定。'
    },
    'limitations':[
        'Q2--Q4修订仍使用题设经验扩散关系和4 h后环境恒定延拓。',
        '修订结果与冻结主路线的差异包含温度处理和离散配置影响，不能直接当作单一机制的因果效应。',
        '没有内部实测时，实际温度只能称为模型预测温度，不能称为实验真实值。'
    ]
}
(out/'revision-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':manifest['status'],'rows':len(rows),'manifest':str(out/'revision-manifest.json')},ensure_ascii=False))
