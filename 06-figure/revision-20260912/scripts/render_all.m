function render_all()
root=fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
out=fullfile(root,'06-figure','revision-20260912'); snap=fullfile(out,'data-snapshots');
figdir=fullfile(out,'figures'); prev=fullfile(out,'previews'); if ~isfolder(figdir),mkdir(figdir);end; if ~isfolder(prev),mkdir(prev);end
ids={ 'FIG-Q1-C-FIELD','FIG-Q1-END-EFFECT','FIG-Q1-GRID-CONV','FIG-Q2-C-PROFILES','FIG-Q2-MODEL-ABLATION','FIG-Q2-GRID-CONV','FIG-Q2-V02-MARGIN','FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q3-BRACKET-ZOOM','FIG-Q3-TIME-CONV','FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q3-SPACE-CONV','FIG-Q4-RADIUS-TIME','FIG-Q4-THRESHOLD-TRAJECTORY','FIG-Q4-BRACKET-ZOOM','FIG-Q4-IMPLEMENTATION-AGREEMENT','FIG-Q4-JACOBIAN-ABLATION','FIG-Q4-COMBINED-BOUNDARY','FIG-Q4-SPACE-CONV','FIG-VAL-BALANCE-RESIDUAL'};
for k=1:numel(ids), draw_one(ids{k},snap,figdir,prev); end
make_contact(ids,prev);
fprintf('MATLAB_RENDER_PASS %d figures\n',numel(ids));
end

function draw_one(id,snap,figdir,prev)
T=readtable(fullfile(snap,[id '.csv']),'TextType','string','VariableNamingRule','preserve');
f=figure('Visible','off','Color','w','InvertHardcopy','off','Units','inches','Position',[1 1 6.535 4.15]);
ax=axes(f); hold(ax,'on'); C=[0 .447 .698;.902 .624 0;0 .62 .451;.835 .369 0;.8 .475 .655;.337 .706 .914;.35 .35 .35];
set(ax,'FontName','Microsoft YaHei','FontSize',8,'LineWidth',.7,'Color','w','XColor',[.1 .1 .1],'YColor',[.1 .1 .1],'ColorOrder',C,'Box','off','TickDir','out'); grid(ax,'on'); ax.GridColor=[.75 .75 .75]; ax.GridAlpha=.35; ax.XMinorGrid='off';
switch id
case {'FIG-Q1-C-FIELD','FIG-Q2-C-PROFILES'}
 u=unique(T.time_s,'stable'); ls={'-','--',':','-.'}; mk={'o','s','^','d'};
 for i=1:numel(u), q=T.time_s==u(i); plot(ax,T.radius_cm(q),T.C_kg_per_kg(q),'LineWidth',1.2,'LineStyle',ls{mod(i-1,4)+1},'Marker',mk{mod(i-1,4)+1},'MarkerIndices',unique(round(linspace(1,sum(q),min(6,sum(q))))),'DisplayName',sprintf('%g h',u(i)/3600)); end
 xlabel(ax,'半径 r (cm)'); ylabel(ax,'干基含水率 C (kg/kg)'); legend(ax,'Location','best','NumColumns',2); note(ax,'条件仿真，非实测');
case 'FIG-Q1-END-EFFECT'
 y=T.final_mean_C; plot(ax,y,[1 1],'-','Color',C(7,:)); scatter(ax,y,[1 1],50,C(1:2,:),'filled'); yticks(ax,[]); xlabel(ax,'1800 s 平均干基含水率 (kg/kg)'); text(ax,y(1),.96,'M1','HorizontalAlignment','center'); text(ax,y(2),1.04,'M2','HorizontalAlignment','center'); text(ax,mean(y),1.09,sprintf('差值 %.10f',abs(diff(y))),'HorizontalAlignment','center'); ylim(ax,[.9 1.13]);
case 'FIG-Q1-GRID-CONV'
 delete(ax); tl=tiledlayout(f,1,2,'Padding','compact','TileSpacing','compact'); mets={'final_max_C','final_mean_C'};
 for j=1:2, a=nexttile(tl); hold(a,'on'); fam=unique(T.family(T.metric==mets{j}),'stable'); for i=1:numel(fam),q=T.metric==mets{j}&T.family==fam(i); plot(a,T.nr(q),T.value(q),'-o','DisplayName',fam(i),'Color',C(i,:));end; styleax(a); xlabel(a,'径向网格数 n_r'); ylabel(a,strrep(mets{j},'_','\_')); legend(a,'Location','best'); end
case 'FIG-Q2-MODEL-ABLATION'
 scatter(ax,1:height(T),T.final_max_C,55,C(1:height(T),:),'filled'); xticks(ax,1:height(T)); xticklabels(ax,T.model); ylabel(ax,'3 h 最大干基含水率 (kg/kg)'); note(ax,'模型差异不代表现实准确率排序');
case 'FIG-Q2-GRID-CONV'
 plot(ax,T.nr,T.value,'-o','Color',C(1,:)); xlabel(ax,'径向网格数 n_r'); ylabel(ax,'3 h 最大干基含水率 (kg/kg)'); text(ax,T.nr(end),T.value(end),sprintf('  最细变化 4.00114e-5\n  阈值 5e-5（窄裕量）'),'VerticalAlignment','bottom');
case 'FIG-Q2-V02-MARGIN'
 scatter(ax,T.absolute_change,1,60,C(2,:),'filled'); xline(ax,T.threshold,'--','验收线 5e-5'); yticks(ax,1); yticklabels(ax,{'V02'}); xlabel(ax,'最大登记场变化 (kg/kg)'); text(ax,T.absolute_change,1.08,sprintf('4.00114e-5；余 %.3g',T.margin),'HorizontalAlignment','center'); ylim(ax,[.8 1.2]);
case {'FIG-Q3-THRESHOLD-TRAJECTORY','FIG-Q4-THRESHOLD-TRAJECTORY'}
 cols={'max_C','mean_C','center_C','surface_C'}; names={'最大值','均值','中心','表面'}; ls={'-','--',':','-.'}; for i=1:4,plot(ax,T.time_s/3600,T.(cols{i}),'LineStyle',ls{i},'Color',C(i,:),'DisplayName',names{i});end; yline(ax,.149999,'--','阈值 0.149999'); xlabel(ax,'时间 (h)');ylabel(ax,'干基含水率 C (kg/kg)');legend(ax,'Location','best','NumColumns',2);note(ax,'条件仿真；报告时刻不表示物理秒级精度');
case {'FIG-Q3-BRACKET-ZOOM','FIG-Q4-BRACKET-ZOOM'}
 plot(ax,T.time_s,T.max_C,'-o','Color',C(1,:)); yline(ax,.149999,'--','阈值'); xlabel(ax,'时间 (s)');ylabel(ax,'最大干基含水率 (kg/kg)');note(ax,'局部夹逼与取整规则；非额外实验精度');
case 'FIG-Q3-TIME-CONV'
 scatter(ax,1:height(T),T.absolute_change,55,C(1:height(T),:),'filled'); yline(ax,60,'--','目标 60 s'); xticks(ax,1:height(T)); xticklabels(ax,replace(T.metric,'_','-')); ylabel(ax,'事件时刻变化 (s)'); text(ax,height(T),T.absolute_change(end),sprintf('  %.4f s；登记48 s，裕量有限',T.absolute_change(end)));
case {'FIG-Q3-SENS-ONEFACTOR','FIG-Q3-COMBINED-BOUNDARY','FIG-Q4-COMBINED-BOUNDARY'}
 n=height(T); for i=1:n, crossed=strcmpi(string(T.crossed(i)),'true') || strcmpi(string(T.crossed(i)),'1'); fail=~crossed || (T.display_h(i)>=72 && T.final_max_C(i)>.149999); if fail, scatter(ax,i,72,65,C(4,:),'x','LineWidth',1.5); ha='center'; if i==1,ha='left';elseif i==n,ha='right';end; text(ax,i,70.5,'72 h内未达标','HorizontalAlignment',ha,'Color',C(4,:)); else, scatter(ax,i,T.display_h(i),50,C(1,:),'o','filled'); end; end; yline(ax,72,'--'); xticks(ax,1:n); xticklabels(ax,short_scenario(T)); xtickangle(ax,25); ylabel(ax,'达标时间 (h；×为未达标)'); note(ax,'有界压力测试，不是概率分布或置信区间');
case {'FIG-Q3-SPACE-CONV','FIG-Q4-SPACE-CONV'}
 plot(ax,T.nr,T.interpolated_event_time_s/3600,'-o','Color',C(1,:)); xlabel(ax,'径向网格数 n_r'); ylabel(ax,'插值事件时刻 (h)'); note(ax,'仅表明空间离散稳定性');
case 'FIG-Q4-RADIUS-TIME'
 plot(ax,T.time_s/3600,T.radius_m*100,'Color',C(1,:)); xlabel(ax,'时间 (h)');ylabel(ax,'半径 R(t) (cm)');note(ax,'冻结收缩律的条件仿真，非尺寸实测');
case 'FIG-Q4-IMPLEMENTATION-AGREEMENT'
 delta_ns=(T.event_time_s-T.event_time_s(1))*1e9; scatter(ax,1:height(T),delta_ns,55,C(1:height(T),:),'filled'); xticks(ax,1:height(T));xticklabels(ax,T.implementation);ylabel(ax,'相对 reference 的时差 (ns)'); ylim(ax,[-.08 max(.75,max(delta_ns)+.12)]); text(ax,.02,.88,sprintf('基准 %.6f s\n报告时刻 183840 s',T.event_time_s(1)),'Units','normalized','HorizontalAlignment','left'); note(ax,'差 5.82e-10 s；实现一致性不等于现实准确性');
case 'FIG-Q4-JACOBIAN-ABLATION'
 scatter(ax,1:height(T),T.balance_error,60,C([1 4],:),'filled'); set(ax,'YScale','log'); xticks(ax,1:height(T));xticklabels(ax,T.route);ylabel(ax,'归一化平衡误差（对数轴）');note(ax,'Jacobian 消融失败必须保留；非现实验证');
case 'FIG-Q4-DRY-SOLID-CONTINUITY'
 stem(ax,1:height(T),T.plot_value,'filled','Color',C(1,:));set(ax,'YScale','log');xticks(ax,1:height(T));xticklabels(ax,T.metric);xtickangle(ax,15);ylabel(ax,'误差/残差（对数轴）');note(ax,'守恒诊断，不是真实性验证');
case 'FIG-VAL-BALANCE-RESIDUAL'
 x=1:height(T); semilogy(ax,x,T.normalized_moisture_balance_error,'o','Color',C(1,:),'DisplayName','平衡误差'); semilogy(ax,x,T.max_linear_relative_residual,'s','Color',C(2,:),'DisplayName','线性残差'); set(ax,'YScale','log'); xlabel(ax,'正式运行序号');ylabel(ax,'无量纲误差（对数轴）');legend(ax,'Location','best');note(ax,'全部运行均绘制；数值质量不代表现实准确性');
end
styleax(findall(f,'Type','axes')); set(findall(f,'Type','text'),'Color',[.1 .1 .1]); set(findall(f,'Type','legend'),'Box','off','Color','w','TextColor',[.1 .1 .1],'FontName','Microsoft YaHei','FontSize',7.5);
exportgraphics(f,fullfile(figdir,[id '.svg']),'ContentType','vector'); exportgraphics(f,fullfile(figdir,[id '.png']),'Resolution',600);
exportgraphics(f,fullfile(prev,[id '-color.png']),'Resolution',150); im=imread(fullfile(prev,[id '-color.png'])); g=uint8(.2126*double(im(:,:,1))+.7152*double(im(:,:,2))+.0722*double(im(:,:,3))); imwrite(g,fullfile(prev,[id '-grayscale.png'])); close(f);
end

function styleax(axs)
for a=reshape(axs,1,[]),set(a,'FontName','Microsoft YaHei','FontSize',8,'LineWidth',.7,'Color','w','XColor',[.1 .1 .1],'YColor',[.1 .1 .1],'Box','off','TickDir','out');grid(a,'on');a.GridColor=[.75 .75 .75];a.GridAlpha=.35;end
end
function note(ax,s), text(ax,.01,.02,s,'Units','normalized','FontName','Microsoft YaHei','FontSize',7,'Color',[.25 .25 .25],'VerticalAlignment','bottom'); end
function labels=short_scenario(T)
labels=strings(height(T),1);
for i=1:height(T)
 f=string(T.factor(i)); lev=string(T.level(i));
 if contains(f,'combined'), labels(i)="联合"+replace(lev,["low","high"],["不利","有利"]);
 elseif f=="terminal_window_s", labels(i)="窗口"+string(round(double(T.value(i))/60))+"min";
 elseif f=="h_mult", labels(i)="h-"+lev;
 elseif f=="hm_mult", labels(i)="hm-"+lev;
 elseif contains(f,'prefactor'), labels(i)="系数-"+lev;
 elseif contains(f,'exponent'), labels(i)="指数-"+lev;
 else, labels(i)=replace(string(T.scenario(i)),'_','-'); end
end
end
function make_contact(ids,prev)
ims=cell(size(ids));for i=1:numel(ids),ims{i}=imread(fullfile(prev,[ids{i} '-color.png']));end
thumbH=360;thumbW=560;sheet=uint8(255*ones(ceil(numel(ids)/3)*thumbH,3*thumbW,3));
for i=1:numel(ids),im=ims{i}; sc=min((thumbH-10)/size(im,1),(thumbW-10)/size(im,2)); im=imresize(im,sc); r=floor((i-1)/3);c=mod(i-1,3); y=r*thumbH+6;x=c*thumbW+6;sheet(y:y+size(im,1)-1,x:x+size(im,2)-1,:)=im;end
imwrite(sheet,fullfile(prev,'contact-sheet-color.png')); gray=uint8(.2126*double(sheet(:,:,1))+.7152*double(sheet(:,:,2))+.0722*double(sheet(:,:,3)));imwrite(gray,fullfile(prev,'contact-sheet-grayscale.png'));
end
