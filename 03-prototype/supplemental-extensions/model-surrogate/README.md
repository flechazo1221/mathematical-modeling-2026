# SUP-GNN 降级原型

因 PyTorch/torch_geometric 不可用，采用预注册思想的固定一维邻接消息聚合特征，并训练线性读出进行自回归。它是消息传递代理的 NumPy 最小代表，不冒充完整 GNN。
