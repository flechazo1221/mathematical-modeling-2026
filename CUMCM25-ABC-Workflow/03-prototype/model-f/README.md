# F 最小原型

`../run_prototypes.py` 中 `estimate_F` 只在固定窗口内线性重采样到等距波数网格，使用 Hann 窗和固定 FFT 峰规则；与 B 共用数据、窗口、掩码、预算与停止规则。
