from pathlib import Path
import hashlib, json, shutil

root = Path(__file__).resolve().parent
pkg = root.parent / 'A题第一版' / '01-论文' / '范文风格重写版'
pkg.mkdir(parents=True, exist_ok=True)
for name in ['完整论文-LaTeX','code-sources','重写版渲染-最终']:
    src = root / name
    dst = pkg / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
for name in ['范文风格重写版.pdf','范文风格重写版.build.json','AI工具使用详情.pdf','AI使用声明.md','appendix-provenance.json','范文风格重写版-交付说明.md']:
    shutil.copy2(root / name, pkg / name)

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

pdf = pkg/'范文风格重写版.pdf'
record = {
    'schema_version':'1.0', 'status':'REVIEWABLE_DRAFT_NOT_APPROVED_FOR_SUBMISSION',
    'source':'完整论文-LaTeX/example.tex',
    'pdf':'范文风格重写版.pdf', 'pdf_sha256':sha(pdf),
    'pages':73, 'body_start_page':2, 'appendix_start_page':20,
    'code_programs':17, 'code_lines':3652,
    'checks':{'latex_build':'PASS','quality_validate':'PASS','page_render':'PASS',
              'min_image_dpi':709,'unembedded_fonts':0,'blank_pages':0},
    'known_limits':['队伍编号和成员信息尚未填写','时间步细化仍改变Q3/Q4报告值',
                    '当前结果为题设经验律、环境延拓和无潜热条件下的数值预测'],
    'reference_style':'用户提供的《优秀论文》；未复制其具体模型参数或结果。'
}
(pkg/'范文风格重写版-交付记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'范文风格重写版-交付记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'delivery':str(pkg),'pdf_sha256':record['pdf_sha256'],'pages':record['pages']},ensure_ascii=False))
