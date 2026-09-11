function render_from_compute()
out=fileparts(fileparts(mfilename('fullpath'))); snap=fullfile(out,'data-snapshots'); figdir=fullfile(out,'figures'); prev=fullfile(out,'previews');
ids={'FIG-Q1-C-FIELD','FIG-Q1-END-EFFECT','FIG-Q1-GRID-CONV','FIG-Q2-C-PROFILES','FIG-Q2-MODEL-ABLATION','FIG-Q2-GRID-CONV','FIG-Q2-V02-MARGIN','FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q3-BRACKET-ZOOM','FIG-Q3-TIME-CONV','FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q3-SPACE-CONV','FIG-Q4-RADIUS-TIME','FIG-Q4-THRESHOLD-TRAJECTORY','FIG-Q4-BRACKET-ZOOM','FIG-Q4-SPACE-CONV','FIG-Q4-IMPLEMENTATION-AGREEMENT','FIG-Q4-JACOBIAN-ABLATION','FIG-Q4-COMBINED-BOUNDARY','FIG-Q4-DRY-SOLID-CONTINUITY','FIG-VAL-BALANCE-RESIDUAL'};
for i=1:numel(ids),draw(ids{i},snap,figdir,prev);end; contact(ids,prev); fprintf('NEW_MATLAB_RENDER_PASS %d\n',numel(ids));
end
function draw(id,snap,figdir,prev)
T=readtable(fullfile(snap,[id '.csv']),'TextType','string','VariableNamingRule','preserve'); blue=[0 .447 .698]; orange=[.902 .624 0]; red=[.835 .369 0]; green=[0 .62 .451]; gray=[.35 .35 .35];
f=figure('Visible','off','Color','w','InvertHardcopy','off','Units','centimeters','Position',[2 2 16.6 10.8]); ax=axes(f);hold(ax,'on');paper(ax);
switch id
case {'FIG-Q1-C-FIELD','FIG-Q2-C-PROFILES'}
 u=unique(T.time_s,'stable'); colors=parula(numel(u)); ls={'-','--',':','-.'}; for k=1:numel(u),q=T.time_s==u(k); plot(ax,T.radius_cm(q),T.C_kg_per_kg(q),'Color',colors(k,:),'LineStyle',ls{mod(k-1,4)+1},'Marker','o','MarkerIndices',[1 sum(q)],'LineWidth',1.35,'DisplayName',sprintf('%g h',u(k)/3600));end; xlabel('半径 r (cm)');ylabel('干基含水率 C (kg/kg)');legend('Location','southwest','NumColumns',2); boundary(ax,'条件仿真场，非实测');
case 'FIG-Q1-END-EFFECT'
 y=1:2; plot(ax,T.final_mean_C,y,'-','Color',gray,'LineWidth',1.1); scatter(ax,T.final_mean_C,y,70,[blue;orange],'filled');yticks(y);yticklabels({'M1 一维基线','M2 二维主干'});xlabel('1800 s 平均干基含水率 (kg/kg)'); text(mean(T.final_mean_C),1.5,sprintf('差值 %.10f',abs(diff(T.final_mean_C))),'HorizontalAlignment','center','BackgroundColor','w');ylim([.6 2.4]);boundary(ax,'模型差异不等于精度提升');
case 'FIG-Q1-GRID-CONV'
 close(f);f=figure('Visible','off','Color','w','Units','centimeters','Position',[2 2 16.6 10.8]);tl=tiledlayout(f,2,2,'Padding','compact','TileSpacing','compact'); mets={'final_max_C','final_mean_C'}; fam={'M1','M2'};for j=1:2,for k=1:2,a=nexttile(tl);paper(a);q=T.metric==mets{j}&T.family==fam{k};x=T.nr(q).*T.nz(q);plot(a,x,T.value(q),'-o','Color',blue,'LineWidth',1.2);xlabel(a,'总网格数 n_r n_z');ylabel(a,strrep(mets{j},'_',' '));title(a,[fam{k},' · ',strrep(mets{j},'_',' ')]);end,end
case 'FIG-Q2-MODEL-ABLATION'
 y=1:height(T); stem(ax,y,T.final_max_C,'filled','Color',blue,'MarkerFaceColor',blue,'LineWidth',1.1);xticks(y);xticklabels(T.model);ylabel('3 h 最大含水率 (kg/kg)');for k=1:height(T),text(k,T.final_max_C(k)+.025,sprintf('%.4f',T.final_max_C(k)),'HorizontalAlignment','center');end;ylim([0 2.35]);boundary(ax,'消融差异不是现实准确率排名');
case 'FIG-Q2-GRID-CONV'
 plot(ax,T.nr,T.value,'-o','Color',blue,'MarkerFaceColor','w','LineWidth',1.4);xlabel('径向网格数 n_r');ylabel('3 h 最大含水率 (kg/kg)');yyaxis right;plot(ax,T.nr,T.adjacent_change,'--s','Color',orange,'MarkerFaceColor','w');ylabel('相邻变化 (kg/kg)');yline(5e-5,':','验收线 5e-5');yyaxis left;boundary(ax,'最细变化 4.00114e-5：窄裕量 PASS');
case 'FIG-Q2-V02-MARGIN'
 obs=T.observed(1);thr=T.threshold(1);barh(ax,1,thr,'FaceColor',[.9 .9 .9],'EdgeColor','none');scatter(ax,obs,1,80,orange,'filled');xline(thr,'--','阈值');yticks(1);yticklabels('V02');xlabel('登记场变化 (kg/kg)');xlim([0 thr*1.12]);text(obs,1.15,sprintf('观测 %.6g\n裕量 %.3g',obs,thr-obs),'HorizontalAlignment','center');
case {'FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q4-THRESHOLD-TRAJECTORY'}
 close(f);f=figure('Visible','off','Color','w','Units','centimeters','Position',[2 2 16.6 10.8]);tl=tiledlayout(f,2,1,'Padding','compact','TileSpacing','compact');a=nexttile(tl);paper(a);plot(a,T.time_s/3600,T.max_C,'Color',blue,'LineWidth',1.45,'DisplayName','最大值');hold(a,'on');plot(a,T.time_s/3600,T.mean_C,'--','Color',orange,'LineWidth',1.2,'DisplayName','均值');yline(a,.149999,':','判据');ylabel(a,'C (kg/kg)');legend(a,'Location','northeast');a=nexttile(tl);paper(a);plot(a,T.time_s/3600,T.center_C,'Color',green,'LineWidth',1.3,'DisplayName','中心');hold(a,'on');plot(a,T.time_s/3600,T.surface_C,'-.','Color',red,'LineWidth',1.2,'DisplayName','表面');xlabel(a,'时间 (h)');ylabel(a,'C (kg/kg)');legend(a,'Location','northeast');
case {'FIG-Q3-BRACKET-ZOOM','FIG-Q4-BRACKET-ZOOM'}
 plot(ax,T.time_s,T.max_C,'-o','Color',blue,'MarkerFaceColor','w','LineWidth',1.3);yline(T.threshold(1),'--','判据');xline(T.interpolated_event_time_s(1),':','插值时刻');xline(T.reported_event_time_s(1),'-.','60 s报告时刻');xlabel('时间 (s)');ylabel('最大含水率 (kg/kg)');boundary(ax,'插值用于数值夹逼，不代表物理秒级精度');
case 'FIG-Q3-TIME-CONV'
 barh(ax,1,T.absolute_change(1),'FaceColor',blue);xline(60,'--','目标 60 s');yticks(1);yticklabels('时间步细化');xlabel('事件时刻变化 (s)');xlim([0 68]);text(T.absolute_change(1),1.15,sprintf('47.5654 s；登记 48 s'),'HorizontalAlignment','right');boundary(ax,'有限裕量，不是零误差');
case {'FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q4-COMBINED-BOUNDARY'}
 labs=labels(T);n=height(T);for k=1:n,ok=logical_value(T.crossed(k)); if ok,scatter(ax,T.t_star_s(k)/3600,k,65,blue,'filled');else,scatter(ax,72,k,80,red,'x','LineWidth',1.8);text(ax,71.5,k,'未达标','HorizontalAlignment','right','Color',red);end,end;xline(72,'--','72 h上限');yticks(1:n);yticklabels(labs);xlabel('达标时间 (h；×为右删失)');ylim([.3 n+.7]);boundary(ax,'有界压力测试，不是概率或置信区间');
case {'FIG-Q3-SPACE-CONV','FIG-Q4-SPACE-CONV'}
 yyaxis left;plot(ax,T.nr,T.interpolated_event_time_s/3600,'-o','Color',blue,'MarkerFaceColor','w','LineWidth',1.35);ylabel('插值事件时刻 (h)');yyaxis right;bar(ax,T.nr,T.adjacent_change_s,.35,'FaceColor',orange,'FaceAlpha',.55,'EdgeColor','none');ylabel('相邻变化 (s)');xlabel('径向网格数 n_r');boundary(ax,'仅证明空间离散稳定性');
case 'FIG-Q4-RADIUS-TIME'
 plot(ax,T.time_s/3600,T.radius_m*100,'Color',blue,'LineWidth',1.6);area(ax,T.time_s/3600,T.radius_m*100,1.1,'FaceColor',blue,'FaceAlpha',.08,'EdgeColor','none');xlabel('时间 (h)');ylabel('半径 R(t) (cm)');text(ax,.98,.9,sprintf('收缩 %.1f%%',100*(1-T.radius_m(end)/T.radius_m(1))),'Units','normalized','HorizontalAlignment','right');boundary(ax,'冻结收缩律，非尺寸实测');
case 'FIG-Q4-IMPLEMENTATION-AGREEMENT'
 d=(T.interpolated_event_time_s-T.interpolated_event_time_s(1))*1e9;stem(ax,1:2,d,'filled','Color',blue,'LineWidth',1.2);xticks(1:2);xticklabels({'reference','moving-FV'});ylabel('相对 reference 的时差 (ns)');ylim([-.05 .75]);text(ax,.04,.86,sprintf('基准 %.6f s\n两者均报告 183840 s',T.interpolated_event_time_s(1)),'Units','normalized');boundary(ax,'实现一致性不等于现实准确性');
case 'FIG-Q4-JACOBIAN-ABLATION'
 y=1:2;semilogx(ax,T.balance_error,y,'o','Color',blue,'MarkerFaceColor','w','MarkerSize',8,'LineWidth',1.5);yticks(y);yticklabels(T.route);xlabel('归一化水分平衡误差（对数轴）');xlim([1e-8 2]);text(T.balance_error(2),2,'  V10：消融失败','Color',red);boundary(ax,'失败保留；守恒检查不是现实验证');
case 'FIG-Q4-DRY-SOLID-CONTINUITY'
 v=T.value;v(v==0)=1e-18;barh(ax,1:3,v,'FaceColor',blue);set(ax,'XScale','log');yticks(1:3);yticklabels(T.metric);xlabel('误差/残差（对数轴；零值以 <10^{-18} 标示）');text(v(3),3,' <10^{-18}','HorizontalAlignment','left');boundary(ax,'V12数值诊断，非真实性验证');
case 'FIG-VAL-BALANCE-RESIDUAL'
 semilogy(ax,1:height(T),T.normalized_moisture_balance_error,'o','Color',blue,'MarkerFaceColor','w','DisplayName','平衡误差');semilogy(ax,1:height(T),T.max_linear_relative_residual,'s','Color',orange,'MarkerFaceColor','w','DisplayName','线性残差');xlabel('正式运行序号');ylabel('无量纲误差（对数轴）');legend('Location','northwest');boundary(ax,'全部运行保留；数值质量不代表现实准确性');
end
for a=reshape(findall(f,'Type','axes'),1,[]),paper(a);end;set(findall(f,'Type','legend'),'Box','off','Color','w','TextColor',[.1 .1 .1],'FontName','Microsoft YaHei','FontSize',7.5);set(findall(f,'Type','text'),'FontName','Microsoft YaHei');
exportgraphics(f,fullfile(figdir,[id '.svg']),'ContentType','vector');exportgraphics(f,fullfile(figdir,[id '.png']),'Resolution',600);exportgraphics(f,fullfile(prev,[id '-color.png']),'Resolution',150);im=imread(fullfile(prev,[id '-color.png']));g=uint8(.2126*double(im(:,:,1))+.7152*double(im(:,:,2))+.0722*double(im(:,:,3)));imwrite(g,fullfile(prev,[id '-grayscale.png']));close(f);
end
function paper(a),set(a,'FontName','Microsoft YaHei','FontSize',8,'Color','w','XColor',[.1 .1 .1],'YColor',[.1 .1 .1],'Box','off','TickDir','out','LineWidth',.7);grid(a,'on');a.GridColor=[.78 .78 .78];a.GridAlpha=.3;end
function boundary(a,s),text(a,.01,.02,s,'Units','normalized','FontSize',7,'Color',[.25 .25 .25],'VerticalAlignment','bottom');end
function ok=logical_value(x),ok=strcmpi(string(x),'true')||strcmpi(string(x),'1');end
function x=labels(T),x=strings(height(T),1);for k=1:height(T),f=string(T.factor(k));l=string(T.level(k));if contains(f,'combined'),x(k)="联合-"+l;elseif f=="terminal_window_s",x(k)="窗口 "+string(round(double(T.value(k))/60))+" min";elseif f=="h_mult",x(k)="h-"+l;elseif f=="hm_mult",x(k)="hm-"+l;elseif f=="pref",x(k)="系数-"+l;elseif f=="exponent",x(k)="指数-"+l;else,x(k)=f+"-"+l;end,end,end
function contact(ids,prev),th=300;tw=460;sheet=uint8(255*ones(ceil(numel(ids)/3)*th,3*tw,3));for i=1:numel(ids),im=imread(fullfile(prev,[ids{i} '-color.png']));sc=min((th-8)/size(im,1),(tw-8)/size(im,2));im=imresize(im,sc);r=floor((i-1)/3);c=mod(i-1,3);y=r*th+5;x=c*tw+5;sheet(y:y+size(im,1)-1,x:x+size(im,2)-1,:)=im;end;imwrite(sheet,fullfile(prev,'contact-sheet-color.png'));g=uint8(.2126*double(sheet(:,:,1))+.7152*double(sheet(:,:,2))+.0722*double(sheet(:,:,3)));imwrite(g,fullfile(prev,'contact-sheet-grayscale.png'));end
