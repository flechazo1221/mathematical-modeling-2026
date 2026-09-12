# 内部温度场补全：继续加密结果

状态：**候选数值复审；不进入正式 COMPUTE/EVIDENCE/FIGURE/PAPER。**

本轮读取既有 L/M/H 结果，新增 X/Y 空间层（27×27、36×36）和 X/Y/Z 时间层（75、37.5、18.75 s），均对基线与内部温度候选成对运行。阈值仍为 `0.15−1e−6`，没有调阈值或删除失败算例。

## 空间梯子

|实现|问题|层级|网格|dt(s)|t*(s)|相邻变化(s)|判读|
|---|---|---|---:|---:|---:|---:|---|
|prescribed-T-baseline|Q3|L|8×8|300.0|221538||NA|
|prescribed-T-baseline|Q3|M|12×12|300.0|213074|8464.1|DECREASING|
|prescribed-T-baseline|Q3|H|18×18|300.0|209988|3085.93|DECREASING|
|prescribed-T-baseline|Q3|X|27×27|300.0|208707|1280.6|DECREASING|
|prescribed-T-baseline|Q3|Y|36×36|300.0|208248|459.131|DECREASING|
|prescribed-T-baseline|Q4|L|8×8|300.0|189599||NA|
|prescribed-T-baseline|Q4|M|12×12|300.0|186537|3061.94|DECREASING|
|prescribed-T-baseline|Q4|H|18×18|300.0|185304|1233.57|DECREASING|
|prescribed-T-baseline|Q4|X|27×27|300.0|184777|526.583|DECREASING|
|prescribed-T-baseline|Q4|Y|36×36|300.0|184593|183.843|DECREASING|
|internal-temperature|Q3|L|8×8|300.0|221841||NA|
|internal-temperature|Q3|M|12×12|300.0|213374|8466.89|DECREASING|
|internal-temperature|Q3|H|18×18|300.0|210287|3087.19|DECREASING|
|internal-temperature|Q3|X|27×27|300.0|209006|1281.17|DECREASING|
|internal-temperature|Q3|Y|36×36|300.0|208547|459.332|DECREASING|
|internal-temperature|Q4|L|8×8|300.0|189886||NA|
|internal-temperature|Q4|M|12×12|300.0|186821|3064.91|DECREASING|
|internal-temperature|Q4|H|18×18|300.0|185586|1234.95|DECREASING|
|internal-temperature|Q4|X|27×27|300.0|185059|527.189|DECREASING|
|internal-temperature|Q4|Y|36×36|300.0|184875|184.105|DECREASING|

## 时间梯子

|实现|问题|层级|网格|dt(s)|t*(s)|相邻变化(s)|判读|
|---|---|---|---:|---:|---:|---:|---|
|prescribed-T-baseline|Q3|L|12×12|600.0|214021||NA|
|prescribed-T-baseline|Q3|M|12×12|300.0|213074|947.526|DECREASING|
|prescribed-T-baseline|Q3|H|12×12|150.0|212598|475.444|DECREASING|
|prescribed-T-baseline|Q3|X|12×12|75.0|212360|237.997|DECREASING|
|prescribed-T-baseline|Q3|Y|12×12|37.5|212241|119.321|DECREASING|
|prescribed-T-baseline|Q3|Z|12×12|18.75|212181|59.6552|PASS_60S|
|prescribed-T-baseline|Q4|L|12×12|600.0|187246||NA|
|prescribed-T-baseline|Q4|M|12×12|300.0|186537|708.317|DECREASING|
|prescribed-T-baseline|Q4|H|12×12|150.0|186182|354.808|DECREASING|
|prescribed-T-baseline|Q4|X|12×12|75.0|186005|177.229|DECREASING|
|prescribed-T-baseline|Q4|Y|12×12|37.5|185916|88.9563|DECREASING|
|prescribed-T-baseline|Q4|Z|12×12|18.75|185872|44.5053|PASS_60S|
|internal-temperature|Q3|L|12×12|600.0|214315||NA|
|internal-temperature|Q3|M|12×12|300.0|213374|940.812|DECREASING|
|internal-temperature|Q3|H|12×12|150.0|212903|471.661|DECREASING|
|internal-temperature|Q3|X|12×12|75.0|212667|235.963|DECREASING|
|internal-temperature|Q3|Y|12×12|37.5|212548|118.269|DECREASING|
|internal-temperature|Q3|Z|12×12|18.75|212489|59.1166|PASS_60S|
|internal-temperature|Q4|L|12×12|600.0|187531||NA|
|internal-temperature|Q4|M|12×12|300.0|186821|709.544|DECREASING|
|internal-temperature|Q4|H|12×12|150.0|186466|355.135|DECREASING|
|internal-temperature|Q4|X|12×12|75.0|186289|177.328|DECREASING|
|internal-temperature|Q4|Y|12×12|37.5|186200|88.9983|DECREASING|
|internal-temperature|Q4|Z|12×12|18.75|186155|44.5228|PASS_60S|

## 最后一层 60 秒检查

|实现|问题|梯子|最后层|相邻变化(s)|结论|
|---|---|---|---|---:|---|
|prescribed-T-baseline|Q3|spatial|Y|459.131|INCONCLUSIVE|
|prescribed-T-baseline|Q4|spatial|Y|183.843|INCONCLUSIVE|
|internal-temperature|Q3|spatial|Y|459.332|INCONCLUSIVE|
|internal-temperature|Q4|spatial|Y|184.105|INCONCLUSIVE|
|prescribed-T-baseline|Q3|time|Z|59.6552|PASS_60S|
|prescribed-T-baseline|Q4|time|Z|44.5053|PASS_60S|
|internal-temperature|Q3|time|Z|59.1166|PASS_60S|
|internal-temperature|Q4|time|Z|44.5228|PASS_60S|

## 失败保留

失败算例数：0。失败结果保留在各算例目录的 `raw-result.json` 或日志中。


## 证据边界

- 60 秒判据只评价离散事件时间，不证明内部温度场具有现实测量准确性。
- 潜热、相分辨库存和 Q4 物理热闭合问题不因本轮数值加密而解除。
- 若最后一层仍超过 60 秒，结论保持 `INCONCLUSIVE`，不能写成‘基本收敛’。
