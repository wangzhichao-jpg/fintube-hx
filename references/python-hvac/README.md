# python-hvac 基准案例复现说明 (Reference Reproduction)

本目录记录了对国际开源项目 [TomLXXVI/python-hvac](https://github.com/TomLXXVI/python-hvac)（commit [`9424756`](https://github.com/TomLXXVI/python-hvac/commit/94247560a667905bfbf67e45a58965a58254fce8)，版本 0.1.3）典型盘管案例的独立复现与模型比对。

---

## 1. 算例复现对比

我们在独立的 Python 3.12 参考环境中执行了原 Notebook 中的计算单元（排除了绘图与建筑负荷模块），对比结果如下：

| 算例来源 Notebook | 独立复现换热量 | 原作者保存换热量 | 复现关键状态 |
| :--- | :---:| :---:| :--- |
| **水冷盘管**<br>`air_cooling_coil/air_cooling_coil_01.ipynb` | **4084.46 W** | 4084 W | 水出口 11.11 ℃，出风 15.92 ℃，空气侧压降 13.05 Pa |
| **直接蒸发器**<br>`vapor_compression/ex02_air_evaporator.ipynb` | **5914.86 W** | 5915 W | 流量 142.10 kg/h，出风 13.12 ℃，空气侧压降 45.90 Pa |
| **风冷冷凝器**<br>`vapor_compression/ex03_air_condenser.ipynb` | **7634.47 W** | 7635 W | 出口过冷度 4.16 K，出风 44.94 ℃，空气侧压降 39.54 Pa |

> **说明**：复现换热量与原作者保存的取整值相符；本次独立复现使用CoolProp 8.0.0，原Notebook的完整运行环境未独立核实，不将差异归因于某个单一原因。参考模型没有可比较的制冷剂压降输出，因此记为null，不是0。

---

## 2. 独立运行复现

可通过内置脚本在隔离环境中独立执行复现：

1. 克隆或下载对应 commit 的 `python-hvac` 源码。
2. 安装依赖并执行独立的复现工具：

```bash
uv venv --python 3.12 .refenv
uv pip install -r requirements-reference-lock.txt -e PATH_TO_PYTHON_HVAC

python reproduce.py water --source PATH_TO_PYTHON_HVAC --output water-rerun.json
python reproduce.py evaporator --source PATH_TO_PYTHON_HVAC --output evaporator-rerun.json
python reproduce.py condenser --source PATH_TO_PYTHON_HVAC --output condenser-rerun.json
```

脚本运行前核对上游419个源码文件的Git blob，确认源码版本；依赖环境并不因此与原作者环境完全一致。

---

## 3. 与 Fintube HX 的模型差异说明

在进行跨软件模型对照时，需注意以下建模差异：

1. **管排几何定义**：  
   - `python-hvac` 使用连续化等效管束模型（例如水盘管定义为 20.26 根管、第一排 7.09 根管）。
   - `fintube_hx` 采用实际整管排离散几何（水盘管离散化为 3 排 × 7 管 = 21 根管，迎风面高度相应由 180 mm 规整为 177.8 mm）。
2. **基准计算对比**：  
   - 保持已映射热工边界和节距，`fintube_hx`预测 **4363.49 W**（相较参考 **+6.83%**）；面高177.8mm与参考180mm不同，迎风面积不完全一致。
   - 该例出风16.772°C、出水11.389°C，空气芯体摩擦15.471Pa、水侧直管摩擦2435.369Pa；参考分别15.916°C、11.108°C、13.048Pa、774.812Pa。压降口径与回路/有效长度不同，不能将软件差异当成实测错误，或按比例缩放压降。差异可能涉及几何、传热/效率和湿模型，尚未完成单一原因归因。
3. **两相模型现状**：  
   - 本项目目前在开源库中提供蒸发与冷凝的基础输入 UA 校核，完整的独立两相流动沸腾与冷凝几何关联式拓展仍在持续演进中。

相关工况原始配置与差异比对明细参见 `water-community-comparison.json`。
第三方 MIT 引用与署名声明参见 `../../THIRD_PARTY_NOTICES.md`。
