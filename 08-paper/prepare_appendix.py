"""Deterministically typeset the frozen Markdown appendices; no compute runs."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / '08-paper'
PROJECT = PAPER / '完整论文-LaTeX'

def esc(text):
    return ''.join({'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$',
                    '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}.get(c, c) for c in text)

def convert_md(text):
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('|'):
            table = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', c) for c in row):
                    table.append(row)
                i += 1
            n = len(table[0])
            widths = {2: [0.22, .72], 3: [.09,.32,.51], 4:[.06,.29,.15,.40], 5:[.06,.20,.31,.16,.16]}[n]
            spec = ''.join('>{\\raggedright\\arraybackslash}p{'+str(w)+'\\linewidth}' for w in widths)
            out.append(r'{\small\setlength{\tabcolsep}{3pt}\begin{longtable}{'+spec+'}\n'+r'\toprule')
            for j, row in enumerate(table):
                out.append(' & '.join(esc(c.replace('`','')) for c in row)+r'\\')
                if j == 0:
                    out.append(r'\midrule\endhead')
            out.append(r'\bottomrule\end{longtable}}')
            continue
        if line.startswith('# '):
            pass
        elif line.startswith('## '):
            out.append(r'\section*{'+esc(line[3:])+'}')
        elif line.startswith('<https://'):
            out.append(r'{\raggedright\url{'+line.strip('<>')+r'}\par}')
        elif line:
            out.append(esc(line.removeprefix('> ').replace('`',''))+'\n')
        i += 1
    return '\n'.join(out)

source = ROOT / '07-appendix/appendix-draft.md'
md = source.read_text(encoding='utf-8-sig')
blocks = re.findall(r'^## `([^`]+)`\s*\n(.*?)^~~~~python\s*\n(.*?)^~~~~\s*$', md, re.M | re.S)
assert len(blocks) == 17, len(blocks)
lines = [r'\clearpage\section{源程序全文}',
         '以下程序由冻结的附录底稿逐段转换排版，未在论文阶段重新计算或改写算法。']
records = []
for i, (origin, note, code) in enumerate(blocks, 1):
    filename = f'program-{i:02d}.py'
    payload = code.encode('utf-8')
    for folder in [PAPER / 'code-sources', PROJECT / 'code']:
        folder.mkdir(exist_ok=True)
        (folder / filename).write_bytes(payload)
    lines += [r'\Needspace{10\baselineskip}\subsection{程序 '+str(i)+'：'+esc(Path(origin).name)+'}',
              r'{\raggedright\noindent 原文件：\path{'+origin+r'}\par}',
              esc(note.strip()),
              r'\begingroup\setstretch{1.0}',
              r'\VerbatimInput[fontsize=\fontsize{7.5}{9}\selectfont,breaklines=true,breakanywhere=true,numbers=left,numbersep=5pt]{code/'+filename+'}',
              r'\endgroup']
    records.append({'original_path': origin, 'typeset_copy': 'code/'+filename,
                    'sha256': hashlib.sha256(payload).hexdigest(), 'lines': len(code.splitlines())})
(PROJECT / 'appendix-code.tex').write_text('\n\n'.join(lines)+'\n', encoding='utf-8')
(PAPER / 'appendix-provenance.json').write_text(json.dumps({'source': str(source),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'programs': records},ensure_ascii=False,indent=2),encoding='utf-8')
ai = (ROOT / '07-appendix/AI 工具使用详情.md').read_text(encoding='utf-8-sig')
ai_tex = r'''\documentclass[UTF8,fontset=none,a4paper,12pt]{ctexart}
\usepackage[margin=2.5cm]{geometry}
\usepackage{booktabs,longtable,array,hyperref}
\setCJKmainfont[BoldFont=SimHei,ItalicFont=KaiTi]{SimSun}
\setCJKsansfont[BoldFont=SimHei]{SimHei}
\setCJKmonofont{SimSun}
\setCJKfamilyfont{zhhei}{SimHei}
\providecommand{\heiti}{\CJKfamily{zhhei}}
\hypersetup{hidelinks}
\setlength{\emergencystretch}{3em}
\raggedbottom
\begin{document}
\begin{center}\Large\heiti AI工具使用详情\end{center}
'''+convert_md(ai)+r'\end{document}'
(PROJECT / 'ai-details.tex').write_text(ai_tex,encoding='utf-8')
print(json.dumps({'programs':len(records),'code_lines':sum(r['lines'] for r in records)},ensure_ascii=False))
