"""Publication figures for the isolated internal-temperature-field route.
All plots use the Python backend and read only revision CSVs or frozen Q1 data.
"""
from pathlib import Path
import hashlib, json, shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[2]
REV=ROOT/'04-compute/revision-temp-field-20260913/results'
OUT=Path(__file__).resolve().parent
FIG=OUT/'figures'; PRE=OUT/'previews'; SNAP=OUT/'data-snapshots'; CON=OUT/'contracts'
for p in (FIG,PRE,SNAP,CON): p.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':9,'axes.unicode_minus':False,
                     'svg.fonttype':'none','pdf.fonttype':42,'axes.linewidth':.8})
BLUE='#0072B2'; ORANGE='#E69F00'; GREEN='#009E73'; BLACK='#111111'; GRID='#D9D9D9'

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def save(fid, fig, sources, claim):
    fig.set_size_inches(7.2,4.4)
    fig.tight_layout()
    fig.savefig(FIG/f'{fid}.pdf')
    fig.savefig(FIG/f'{fid}.svg')
    fig.savefig(FIG/f'{fid}.png',dpi=600)
    fig.savefig(PRE/f'{fid}-color.png',dpi=150)
    ImageOps.grayscale(Image.open(PRE/f'{fid}-color.png').convert('RGB')).save(PRE/f'{fid}-grayscale.png')
    plt.close(fig)
    snap=[{'path':str(src.relative_to(ROOT)),'sha256':sha(src)} for src in sources]
    meta={'figure_id':fid,'claim':claim,'sources':snap,'formats':['pdf','svg','png'],
          'png_dpi':600,'backend':'python/matplotlib','units':'as labelled'}
    (CON/f'{fid}.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')

# Q2 temperature trajectory.
t2=REV/'Q2-M4-field-fine-trajectory.csv'; d2=pd.read_csv(t2)
fig,ax=plt.subplots()
ax.plot(d2.time_s/3600,d2.center_T_C,'o-',color=BLUE,lw=1.6,ms=3.5,label='中截面轴心')
ax.plot(d2.time_s/3600,d2.surface_T_C,'s--',color=ORANGE,lw=1.4,ms=3.2,label='药材表面')
ax.set(xlabel='时间 (h)',ylabel='温度 (°C)',title='问题二：内部温度场的中心—表面变化')
ax.grid(axis='y',color=GRID,lw=.6); ax.spines[['top','right']].set_visible(False); ax.legend(frameon=False)
save('FIG-TEMP-FIELD-Q2-TEMP',fig,[t2],'实际温度场使中心温度和表面温度在升温阶段存在可辨差异')

# Q2 moisture profiles.
p2=REV/'Q2-M4-field-fine-profiles.csv'; dp=pd.read_csv(p2)
fig,ax=plt.subplots()
times=[1800,3600,5400,7200,9000,10800]
colors=plt.cm.viridis(np.linspace(.1,.9,len(times)))
for tt,c in zip(times,colors):
    g=dp[np.isclose(dp.time_s,tt)]
    ax.plot(g.radius_cm,g.C_kg_per_kg,'o-',ms=2.5,lw=1.1,color=c,label=f'{tt/3600:g} h')
ax.set(xlabel='径向位置 r (cm)',ylabel='干基含水率 C (kg/kg)',title='问题二：内部温度场下的含水率径向剖面')
ax.grid(axis='y',color=GRID,lw=.6); ax.spines[['top','right']].set_visible(False); ax.legend(ncol=3,frameon=False,fontsize=8)
save('FIG-TEMP-FIELD-Q2-PROFILES',fig,[p2],'表面先失水、中心后响应，实际温度场下的内部梯度随时间向中心推进')

# Q2 compare old prescribed route and new field route.
old=ROOT/'04-compute/revision-grid-conv-20260913/results/q2-model-trajectories/q2-model-trajectories.csv'
do=pd.read_csv(old); field=d2[['time_s','max_C','mean_C']].copy(); field['model']='M3 内部温度场（新）'
ctrl=do[do.model.isin(['M2 常物性','M3 主路线'])].copy()
ctrl['model']=ctrl.model.map({'M2 常物性':'M2 常物性（原）','M3 主路线':'M3 烘房温度（原）'})
all_df=pd.concat([ctrl[['model','time_s','max_C']],field[['model','time_s','max_C']]],ignore_index=True)
fig,ax=plt.subplots()
styles=[('M2 常物性（原）',BLACK,'-','o'),('M3 烘房温度（原）',ORANGE,'--','s'),('M3 内部温度场（新）',BLUE,'-','^')]
for lab,col,ls,m in styles:
    g=all_df[all_df.model==lab].sort_values('time_s')
    ax.plot(g.time_s/3600,g.max_C,color=col,ls=ls,marker=m,ms=3,lw=1.3,label=lab)
ax.set(xlabel='时间 (h)',ylabel='全域最大干基含水率 (kg/kg)',title='问题二：内部温度场对模型轨迹的影响')
ax.grid(axis='y',color=GRID,lw=.6); ax.spines[['top','right']].set_visible(False); ax.legend(frameon=False,fontsize=8)
fig.text(.5,-.015,'原路线与新路线的网格/时间步不完全相同，差异用于机制对照，不作精度排序',ha='center',fontsize=7,color='#444')
save('FIG-TEMP-FIELD-Q2-COMPARE',fig,[old,t2],'将内部温度场路线与原统一环境温度路线并列，显示温度处理会改变水分轨迹')

# Q3/Q4 threshold trajectories.
for fid,fn,title in [('FIG-TEMP-FIELD-Q3-THRESHOLD','Q3-M4-field-trajectory.csv','问题三：内部温度场下的全域达标判定'),
                      ('FIG-TEMP-FIELD-Q4-THRESHOLD','Q4-M4-field-trajectory.csv','问题四：收缩域内部温度场下的全域达标判定')]:
    src=REV/fn; d=pd.read_csv(src); fig,ax=plt.subplots()
    ax.plot(d.time_s/3600,d.max_C,color=BLUE,lw=1.5)
    ax.axhline(.15-1e-6,color=ORANGE,ls='--',lw=1.2,label=r'安全阈值 $0.15-10^{-6}$')
    # The trajectory is sampled hourly, so the exact first crossing is stored
    # in the summary (linear interpolation) rather than necessarily appearing
    # as a sampled row.
    sid='Q3-M4-field' if 'Q3' in fid else 'Q4-M4-field'
    sm=pd.read_csv(REV/'temperature-field-summary.csv')
    event_s=float(sm.loc[sm.label==sid,'interpolated_event_time_s'].iloc[0])
    ax.axvline(event_s/3600,color=BLACK,ls=':',lw=1,label=f'插值事件 {event_s/3600:.2f} h')
    ax.set(xlabel='时间 (h)',ylabel='全域最大干基含水率 (kg/kg)',title=title)
    ax.grid(axis='y',color=GRID,lw=.6); ax.spines[['top','right']].set_visible(False); ax.legend(frameon=False,fontsize=8)
    save(fid,fig,[src],'全域最大含水率首次低于安全阈值的事件判定')

# Q4 radius.
src=REV/'Q4-M4-field-trajectory.csv'; d=pd.read_csv(src)
fig,ax=plt.subplots(); ax.plot(d.time_s/3600,d.radius_m*100,color=BLACK,lw=1.5)
ax.set(xlabel='时间 (h)',ylabel='半径 R(t) (cm)',title='问题四：药材半径的观测插值与收缩')
ax.grid(axis='y',color=GRID,lw=.6); ax.spines[['top','right']].set_visible(False)
save('FIG-TEMP-FIELD-Q4-RADIUS',fig,[src],'半径随时间收缩，作为移动域几何输入')

# Q1 figures are unchanged and already solve the temperature field.
for fid,ext in [('FIG-Q1-C-FIELD','pdf'),('FIG-Q1-END-EFFECT','png')]:
    src=ROOT/'06-figure/figures'/f'{fid}.{ext}'
    if src.exists(): shutil.copy2(src,FIG/src.name)
print('TEMP_FIELD_FIGURES_PASS',len(list(FIG.glob('FIG-*.pdf'))))
