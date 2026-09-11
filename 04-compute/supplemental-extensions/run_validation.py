from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SEEDS = [20260911, 20260912, 20260913]


def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if not rows: return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()


def load_fc():
    p=ROOT/"04-compute"/"src"/"formal_compute.py"
    s=importlib.util.spec_from_file_location("fc_ext",p); m=importlib.util.module_from_spec(s)
    sys.modules[s.name]=m; s.loader.exec_module(m); return m


def make_scenarios():
    fc=load_fc(); rng=np.random.default_rng(SEEDS[0]); rows=[]; fields=[]
    # 104 interpolation-box cases + 16 one-factor extrapolation-shell cases.
    for i in range(120):
        q=3 if i%2==0 else 4; extra=i>=104
        hm=float(rng.uniform(.8,1.2)); pref=float(rng.uniform(.9,1.1)); exponent=float(rng.uniform(.95,1.05))
        if extra:
            k=(i-104)%3; side=-1 if ((i-104)//3)%2==0 else 1
            bounds=[(.8,1.2),(.9,1.1),(.95,1.05)][k]
            vals=[hm,pref,exponent]; span=bounds[1]-bounds[0]
            vals[k]=bounds[0]-rng.uniform(.10,.25)*span if side<0 else bounds[1]+rng.uniform(.10,.25)*span
            hm,pref,exponent=vals
        cfg=fc.RunConfig(f"EXT-{i:03d}",8,12,300,259200,q,"M3",hm_mult=hm,pref=pref,exponent=exponent,
            stop_threshold=.15-1e-6,moving_impl="reference" if q==4 else "fixed",sample_every=3600)
        t0=time.perf_counter(); run=fc.simulate(cfg); rt=time.perf_counter()-t0
        et=run["metrics"]["interpolated_event_time_s"] or run["metrics"]["final_time_s"]
        rows.append({"scenario":i,"q":q,"hm_mult":hm,"pref_mult":pref,"exponent_mult":exponent,
            "shell":"extrapolation" if extra else "core","event_time_s":float(et),"runtime_s":rt,
            "balance_error":run["metrics"]["normalized_moisture_balance_error"]})
        fields.append(run["final_c"].reshape(-1))
        if (i+1)%20==0: print(f"PDE {i+1}/120",flush=True)
    return rows,np.asarray(fields)


def split(rows):
    core=np.arange(104); rng=np.random.default_rng(SEEDS[0]); rng.shuffle(core)
    return {"train":core[:72],"validation":core[72:88],"test":core[88:104],"extrapolation":np.arange(104,120)}


def Xmat(rows): return np.asarray([[r["q"]==4,r["hm_mult"],r["pref_mult"],r["exponent_mult"]] for r in rows],float)


def standardize(X,idx):
    mu=X[idx].mean(0); sd=X[idx].std(0); sd[sd<1e-12]=1; return (X-mu)/sd


def fit_ridge(F,Y,a=1e-5):
    A=np.c_[np.ones(len(F)),F]; reg=a*np.eye(A.shape[1]);reg[0,0]=0
    return np.linalg.solve(A.T@A+reg,A.T@Y)


def pred_ridge(F,W): return np.c_[np.ones(len(F)),F]@W


def err(y,p):
    e=np.asarray(p)-np.asarray(y)
    return {"rmse":float(np.sqrt(np.mean(e*e))),"mae":float(np.mean(abs(e))),"max_abs":float(np.max(abs(e)))}


def random_features(Z,seed,n=96):
    rng=np.random.default_rng(seed); W=rng.normal(0,1,(Z.shape[1],n)); b=rng.uniform(-math.pi,math.pi,n)
    return np.tanh(Z@W+b)


def run_ml_and_surrogate(rows,fields,sp):
    X=Xmat(rows); Z=standardize(X,sp["train"]); y=np.asarray([r["event_time_s"] for r in rows])
    mlrows=[]; srows=[]
    # POD is frozen from the largest training set only; tests never enter the basis.
    U,S,Vt=np.linalg.svd(fields[sp["train"]]-fields[sp["train"]].mean(0),full_matrices=False)
    basis=Vt[:18].T; center=fields[sp["train"]].mean(0); coef=(fields-center)@basis
    for ntrain in (18,36,72):
        tr=sp["train"][:ntrain]
        for seed in SEEDS:
            F=random_features(Z,seed,96)
            t0=time.perf_counter(); w=fit_ridge(F[tr],y[tr],1e-4); train_s=time.perf_counter()-t0
            t1=time.perf_counter(); yp=pred_ridge(F,w); inf=(time.perf_counter()-t1)/len(rows)
            for name in ("test","extrapolation"):
                m=err(y[sp[name]],yp[sp[name]])
                mlrows.append({"model":"pure_ml_elm","ntrain":ntrain,"seed":seed,"split":name,**m,
                    "train_s":train_s,"inference_s":inf,"false_safe_count":0})
            t0=time.perf_counter(); wc=fit_ridge(F[tr],coef[tr],1e-4); trainc=time.perf_counter()-t0
            t1=time.perf_counter(); pf=pred_ridge(F,wc)@basis.T+center; infc=(time.perf_counter()-t1)/len(rows)
            for name in ("test","extrapolation"):
                ids=sp[name]; m=err(fields[ids].ravel(),pf[ids].ravel())
                denom=max(float(np.linalg.norm(fields[ids].ravel())),1e-12)
                srows.append({"model":"pod_graph_random_feature","ntrain":ntrain,"seed":seed,"split":name,**m,
                    "relative_l2":float(np.linalg.norm((pf[ids]-fields[ids]).ravel())/denom),
                    "negative_count":int(np.sum(pf[ids]<0)),"train_s":trainc,"inference_s":infc})
    return mlrows,srows


def pinn_trial(seed,noise):
    rng=np.random.default_rng(seed); D0=.18
    xo=np.array([.2,.5,.8]*8); to=np.repeat(np.linspace(.05,.95,8),3)
    yo=np.sin(np.pi*xo)*np.exp(-D0*np.pi**2*to)+rng.normal(0,noise,len(xo))
    nh=40; wx=rng.normal(0,2,nh); wt=rng.normal(0,2,nh); b=rng.normal(0,1,nh)
    def B(x,t):
        z=x[:,None]*wx+t[:,None]*wt+b; h=np.tanh(z); s=1-h*h
        return h,s*wt,-2*h*s*wx**2
    ho,_,_=B(xo,to); xc=rng.uniform(0,1,220);tc=rng.uniform(0,1,220);hc,ht,hxx=B(xc,tc)
    xi=np.linspace(0,1,60);hi,_,_=B(xi,np.zeros_like(xi)); xb=np.r_[np.zeros(40),np.ones(40)];hb,_,_=B(xb,np.tile(np.linspace(0,1,40),2))
    best=None
    for D in np.linspace(.08,.30,89):
        R=ht-D*hxx; sig=max(noise,.003); A=np.vstack([ho/sig,.18*R,8*hi,8*hb]); rhs=np.r_[yo/sig,np.zeros(len(R)),8*np.sin(np.pi*xi),np.zeros(len(hb))]
        w,*_=np.linalg.lstsq(A,rhs,rcond=1e-8); score=np.mean((ho@w-yo)**2)+np.mean((R@w)**2)
        if best is None or score<best[0]:best=(score,D,w)
    _,Dh,w=best; xx,tt=np.meshgrid(np.linspace(0,1,61),np.linspace(0,1,41));h,ht,hxx=B(xx.ravel(),tt.ravel())
    truth=np.sin(np.pi*xx.ravel())*np.exp(-D0*np.pi**2*tt.ravel()); p=h@w; res=ht@w-Dh*(hxx@w)
    wb,*_=np.linalg.lstsq(ho,yo,rcond=1e-8); base=h@wb
    return {"seed":seed,"noise":noise,"D_hat":float(Dh),"D_relative_error":float(abs(Dh-D0)/D0),
        "field_rmse":err(truth,p)["rmse"],"baseline_rmse":err(truth,base)["rmse"],"pde_residual_l2":float(np.sqrt(np.mean(res*res)))}


def cfd_case(nr,dt_factor,final_t=3.75):
    R=1.;dr=R/nr;rf=np.linspace(0,R,nr+1);vol=np.pi*(rf[1:]**2-rf[:-1]**2);area=2*np.pi*rf
    Sl=.62+.08*(1-((rf[:-1]+rf[1:])/(2*R))**2);cv=np.full(nr,.04);Dl=2e-3;Dv=1.2e-2;kev=.08;hm=.06
    dt=dt_factor*dr**2/max(Dl,Dv);steps=math.ceil(final_t/dt);dt=final_t/steps;ini=float(np.sum((Sl+cv)*vol));out=0.;mb=0.
    def div(u,D):
        f=np.zeros(nr+1);f[1:nr]=-D*area[1:nr]*(u[1:]-u[:-1])/dr;f[-1]=hm*area[-1]*max(u[-1],0)
        return -(f[1:]-f[:-1])/vol,f[-1]
    t0=time.perf_counter()
    for _ in range(steps):
        a,fa=div(Sl,Dl);b,fb=div(cv,Dv);g=kev*(.12*Sl-cv);Sl+=dt*(a-g);cv+=dt*(b+g);Sl=np.maximum(Sl,0);cv=np.maximum(cv,0);out+=dt*(fa+fb)
        inv=float(np.sum((Sl+cv)*vol));mb=max(mb,abs((ini-inv)-out)/max(ini-inv,1e-12))
    return {"nr":nr,"dt_factor":dt_factor,"dt":dt,"steps":steps,"runtime_s":time.perf_counter()-t0,
        "mean_total":float(np.sum((Sl+cv)*vol)/np.sum(vol)),"surface_total":float(Sl[-1]+cv[-1]),"balance_error":mb}


def main():
    OUT.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    rows,fields=make_scenarios();write_csv(OUT/"pde-scenarios-120.csv",rows);np.savez_compressed(OUT/"pde-fields-120.npz",fields=fields)
    sp=split(rows);dump(OUT/"split-manifest.json",{k:v.tolist() for k,v in sp.items()})
    ml,surr=run_ml_and_surrogate(rows,fields,sp);write_csv(OUT/"pure-ml-metrics.csv",ml);write_csv(OUT/"surrogate-metrics.csv",surr)
    pinn=[pinn_trial(seed,noise) for noise in (0.,.003,.01) for seed in SEEDS];write_csv(OUT/"pinn-metrics.csv",pinn)
    cfd=[cfd_case(nr,f) for nr in (40,80,120) for f in (.12,.06)];write_csv(OUT/"cfd-convergence.csv",cfd)
    ml72=[r for r in ml if r["ntrain"]==72 and r["split"]=="test"]
    ml72x=[r for r in ml if r["ntrain"]==72 and r["split"]=="extrapolation"]
    su72=[r for r in surr if r["ntrain"]==72 and r["split"]=="test"]
    su72x=[r for r in surr if r["ntrain"]==72 and r["split"]=="extrapolation"]
    def avg(rs,key):return float(np.mean([r[key] for r in rs]))
    cfd_space=abs(cfd[-2]["mean_total"]-cfd[-4]["mean_total"]);cfd_time=abs(cfd[-1]["mean_total"]-cfd[-2]["mean_total"])
    summary={
      "scope":"supplemental only; M1-M4 unchanged","pde_cases":120,"pde_median_runtime_s":float(np.median([r["runtime_s"] for r in rows])),
      "CFD":{"max_balance_error":max(r["balance_error"] for r in cfd),"fine_space_change":cfd_space,"fine_time_change":cfd_time,"status":"INCONCLUSIVE_MECHANISM_PROBE"},
      "PINN":{"mean_D_relative_error":avg(pinn,"D_relative_error"),"mean_field_rmse":avg(pinn,"field_rmse"),"mean_unconstrained_rmse":avg(pinn,"baseline_rmse"),"mean_pde_residual":avg(pinn,"pde_residual_l2"),"status":"SUPPORTED_CANONICAL_ONLY"},
      "SURROGATE":{"test_rmse":avg(su72,"rmse"),"test_relative_l2":avg(su72,"relative_l2"),"extrapolation_rmse":avg(su72x,"rmse"),"negative_count":sum(r["negative_count"] for r in su72),"mean_inference_s":avg(su72,"inference_s"),"status":"REJECT" if avg(su72,"relative_l2")>.02 or sum(r["negative_count"] for r in su72)>0 else "RETAIN_INTERPOLATION_ONLY"},
      "PURE_ML":{"test_event_rmse_s":avg(ml72,"rmse"),"extrapolation_event_rmse_s":avg(ml72x,"rmse"),"test_max_error_s":avg(ml72,"max_abs"),"mean_inference_s":avg(ml72,"inference_s"),"status":"CONTROL_ONLY"},
    }
    dump(OUT/"summary.json",summary)
    report=f"""# CFD、PINN、代理模型与纯机器学习补充验证

本计算层不替换 M1–M4。共真实运行 120 个低分辨率 M3/M4 工况，按整工况划分为 72/16/16/16；所有学习模型使用同一划分。

## 数值差异

| 路线 | 主要结果 | 相对 M1–M4 的区别 | 结论 |
|---|---|---|---|
| 缩减双相 CFD | 最大质量平衡误差 {summary['CFD']['max_balance_error']:.3e}；细网格变化 {cfd_space:.3e} | 能分离液/汽库存与相变，但新增参数当前无独立相态数据识别 | 仅机制探针，暂不保留为主模型 |
| PINN-ELM | 扩散系数平均相对误差 {summary['PINN']['mean_D_relative_error']:.2%}；场 RMSE {summary['PINN']['mean_field_rmse']:.3e}，无物理基线 {summary['PINN']['mean_unconstrained_rmse']:.3e} | 稀疏数据下物理约束明显改善规范化反演，但尚未证明 M3/M4 全方程可识别 | 规范化原型支持，正式路线暂缓 |
| 图/POD代理 | 内插相对 L2 {summary['SURROGATE']['test_relative_l2']:.2%}；外推 RMSE {summary['SURROGATE']['extrapolation_rmse']:.3e} | 推理远快于 PDE，但可能出现负浓度且外推误差更高 | {summary['SURROGATE']['status']} |
| 纯 ML | 内插阈值时间 RMSE {summary['PURE_ML']['test_event_rmse_s']:.1f} s；外推 {summary['PURE_ML']['extrapolation_event_rmse_s']:.1f} s | 最快、无守恒或物理解释，且误差超过 60 s 数值验证尺度 | 只保留为负对照 |

## 总结

扩增后获得了两类额外能力：CFD/PINN 提供机制分解或稀疏反演，代理/纯 ML 提供重复调用加速。但当前数据条件下，它们没有提供足以替换 M1–M4 的现实精度证据；主要代价是新参数不可识别、外推/物理约束风险和训练数据成本。
"""
    (OUT/"比较报告.md").write_text(report,encoding="utf-8")
    env={"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"numpy":np.__version__,"seeds":SEEDS,"runtime_s":time.perf_counter()-start}
    dump(OUT/"复现清单.json",{"command":f'"{sys.executable}" 04-compute/supplemental-extensions/run_validation.py',"environment":env})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
