"""Build PDF review contact sheets and record text/page checks."""
from pathlib import Path
import json
from PIL import Image, ImageDraw
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
reader = PdfReader(HERE/'范文风格重写版.pdf')
pages = sorted((HERE/'重写版渲染').glob('page-*.png'))[:len(reader.pages)]
assert len(pages) == len(reader.pages)
for start in range(0,len(pages),20):
    canvas = Image.new('RGB',(1500,1880),'#dddddd')
    draw = ImageDraw.Draw(canvas)
    for j,p in enumerate(pages[start:start+20]):
        im = Image.open(p).convert('RGB')
        im.thumbnail((290,435))
        x,y=(j%5)*300,(j//5)*470
        canvas.paste(im,(x+(300-im.width)//2,y+24))
        draw.text((x+12,y+5),f'Page {start+j+1}',fill='black')
    canvas.save(HERE/'重写版渲染'/f'contact-{start+1:02d}-{min(start+20,len(pages)):02d}.jpg',quality=92)
texts=[p.extract_text() for p in reader.pages]
report={'pages':len(texts),'appendix_start_page':20,'body_start_page':2,'body_pages':18,
        'code_start_page':22,'code_programs':17,
        'short_pages':[i+1 for i,t in enumerate(texts) if len(t.strip())<80],
        'page_text_lengths':[len(t) for t in texts]}
(HERE/'重写版页面检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='page_text_lengths'}))
