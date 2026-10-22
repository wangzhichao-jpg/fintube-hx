# Fintube HX Community

[ [English](README.md) | **简体中文** ]

[![CI](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml/badge.svg)](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](pyproject.toml)
[![Bilibili](https://img.shields.io/badge/Bilibili-项目宣传片-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1Y1JC6FEs9/)
[![YouTube](https://img.shields.io/badge/YouTube-Overview_Video-FF0000?logo=youtube&logoColor=white)](https://youtu.be/anapOEsmAU0)

**物理透明、可复现的翅片管换热器热工水力基础计算核心（MIT 开源）。**  
覆盖**水盘管、风冷蒸发器、风冷冷凝器**的正向校核、有界流量反求、参数扫描与 CSV/Excel 报告导出。  
代码仓库：[GitHub](https://github.com/wangzhichao-jpg/fintube-hx) · [Gitee 国内镜像](https://gitee.com/bigtaurus/fintube-hx) ｜ 视频介绍：[B站中文宣传片](https://www.bilibili.com/video/BV1Y1JC6FEs9/) · [YouTube (EN)](https://youtu.be/anapOEsmAU0)

![Fintube HX 三大翅片管换热器三维错排结构与热工水力流路孪生](docs/coil-3d-showcase.png)

## 版本生态与定位

Fintube HX 采用“开源研究核心 → 专业工程工作台 → 实验驱动企业定制”三层架构，Community 与 Pro 共享同一套基础物性与求解内核（经回归测试与三轮外部评审）：

| 层级 | 定位与适用场景 | 核心能力边界 |
|---|---|---|
| **Community（本仓库，MIT）** | 高校科研、教学、算法复现与脚本批处理 | 集总参数/轴向分段基础模型、Wang & Chi (2000) 水盘管平片几何、Hausen/Gnielinski 管内换热、有界流量反求、CLI 与 JSON/CSV/XLSX 接口 |
| **Pro 专业工程工作台** | 换热器研发与选型工程师日常设计 | 工程单位表单、P-h/P-x 状态助手、**图形化逐管流路编辑与并联支路水力平衡**、管内两相沸腾/冷凝关联式、多工况批量评估、有限候选约束寻优、Word 计算书 |
| **企业定制与试验验证** | 主机厂与换热器制造企业专属研发 | 依托**建科环能科技有限公司（国家空调设备质检中心）**与**建筑安全与环境国家重点实验室**的试验平台，开展物理台位标定、特殊片型/管型/新工质关联式开发与软件定制 |

## 当前实现

| 对象 | 传热模型 | 几何与压降 |
|---|---|---|
| 纯水盘管 | **整体逆流ε-NTU**；干态显热或湿接触近似 | 输入UA，或连续平片/光管错排几何UA；可输出**干空气芯体摩擦**与**水侧直管摩擦** |
| 蒸发器 | 恒压P-h、逆流空气迭代、**轴向分段**；输入UA均分 | **仅输入UA**，没有制冷剂几何传热关联式或压降 |
| 冷凝器 | 同上，单相单元通过焓及段内温度联立体现有限热容量 | **仅输入UA**，没有制冷剂压降 |

水几何采用Wang-Chi平片j/f、Hausen/Gnielinski管内传热、Churchill摩擦与等面积环形翅片效率近似。湿几何会按增强空气侧系数重新计算**湿翅片效率代理值**，但不等同于严格部分湿模型。0.1.0.dev8新增可选的几何模式湿表面模型`model.wet_surface_model: "threlkeld_braun"`：Braun-Klein-Mitchell（1989）焓势ε-NTU加Threlkeld湿翅片效率（Le=1，湿表面沿用干表面j，忽略凝水膜热阻），整盘取干工况与全湿计算中换热量较大者；不填该字段时仍为原接触近似。

0.1.0.dev9为水盘管几何新增两种翅片：`geometry.fin_type: "louver"`（Wang、Lee、Chang、Lin 1999，IJHMT 42:1945；需`louver_pitch_m`、`louver_height_m`）和`"wavy_herringbone"`（Wang、Hwang、Lin 2002，IJR 25:673；需`wave_height_m`、`wave_projected_length_m`；翅片面积按展开面积secθ计）。两者只允许在文献样本范围内使用，翅片效率默认采用文献数据整理所用的Schmidt法（`geometry.fin_efficiency_method`，平片也可选）。两篇文献的j关联式都在Re_Dc=1000分段，多排盘管在分段点两侧可相差数十个百分点（数据低Re“平台”现象），按原文使用、不作平滑。湿表面沿用干表面j/f。0.1.0.dev10新增`geometry.correlation_range_tolerance`（不超过0.01）：显式声明后，百叶片/波纹片关联式的几何样本边界可放宽该相对幅度（Re与排数不放宽），结果逐项列出超出的参数并给出“边界外推”警告。

0.1.0.dev7新增两个可选几何项：`geometry.fin_count`输入实际片数（只改变换热面积，Wang关联式的水力直径仍按周期通道计算）；`model.exposed_tubes`计入位于气流中的外露光管直段和U形回弯（Churchill–Bernstein单管横掠、给定迎面风速、仅干工况，换热进入旁通气流，单独列出）。

工具支持JSON输入检查、输入/结果副本、单例/批量运行、参数扫描、CSV/XLSX，以及**出水温度、制冷剂过热度/过冷度**的流量反求。未实现指定出风温度反求。

## 快速开始

**要求Python 3.12（`>=3.12,<3.13`）；当前锁定环境不支持Python 3.13。** 请显式选解释器，避免直接使用系统默认版本：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-development-lock.txt -e .
# 激活：POSIX使用source .venv/bin/activate；Windows使用.venv\Scripts\activate
```

也可用`python3.12 -m venv .venv`，Windows用`py -3.12 -m venv .venv`，激活后通过pip安装。镜像缺包时可使用官方PyPI，保持TLS验证。

```bash
fintube-hx capabilities
fintube-hx run examples/water_geometry.json --output output/result.json --xlsx output/result.xlsx
fintube-hx scan examples/water_dry.json --parameter air.volume_flow_m3_h --values "[800,1000,1200]" --output output/scan.json
pytest -q
```

```python
from fintube_hx.engine import run_case
from fintube_hx.storage import load_case
result = run_case(load_case("examples/water_geometry.json"))
print(result["heat_transfer_w"], result["fluid_out"]["temperature_c"])
```

## 输入与结果口径

- 温度°C，绝对压力Pa，尺寸m，流量kg/s，风量为**入口实际m³/h**，RH为0–1。
- `fluid.inlet_t_c`与`fluid.inlet_h_j_kg`二选一；两相入口使用**P-h**。JSON没有入口干度字段。
- `model.segments`只控制制冷剂分段。水模型为整体模型，可不填；历史输入即使填写也不生成分段，结果`numerical_controls`明确标为**未应用**。
- 反求区间必须括住所选根。端点同号不证明内部无根，程序不认证非单调响应的全局唯一性。
- 压降是**直管/芯体摩擦分项**，不是完整盘管或系统总阻力；水侧未含回弯、集管和进出口附件。默认（旧口径）空气侧只有干表面芯体摩擦；可选的`model.pressure_scope: "v1"`（0.1.0.dev16）补入加速项和湿工况附加压降（见下文）。每个结果都在`model_coverage`中列出已计入、未计入、外推和降级的项目。

## 工程模型范围

水盘管默认按入口水温选择湿/干接触近似，不计算局部壁温与部分湿面积；可选的`wet_surface_model: "threlkeld_braun"`（dev8）改用焓势法湿表面和湿翅片效率。空气物性取入口，水物性采用迭代平均温度。Wang使用翅片套管外径Dc而非裸管外径Do；套管壁厚取片厚时Dc=Do+2tf，这是采用的等厚套管口径，实际成形尺寸未独立输入。默认等效片数为L/片距，可用`fin_count`输入实际片数；边缘开口采用理想化几何。

已提供百叶片和人字波纹片（dev9）、微肋管关联式（dev11，供扩展使用）、可选接触热导与管内污垢（dev13），以及清洁表面开始结霜的瞬时极限（dev14，仅用于逐管网络）。本核心没有真实逐管回路、逐排交叉流、中途分合流、溶液物性、霜层随时间增长，也不计相邻管通过共用翅片的导热。蒸发温度≤0°C默认拒绝，除非声明`subzero_evaporation`；关联式区间外不自动外推或裁切几何。

**已知问题（实测）：**冷凝器出口过冷度有偏大倾向：在关联式范围内的CETIAT工况偏大2.3～3.0 K；在超出范围的Joppolo 2015冷凝器上偏大2.5～5 K，换热量偏高1%～9%。原因尚未查明，也没有为此调整任何参数，详见`validation/measured-v6/`。

## 实测验证

当前验收集：[`validation/measured-v6/`](validation/measured-v6/README.zh-CN.md)。目录中记录了来源及页码/表格定位、每项输入的 D0–D4 推导等级、运行前声明的容差，以及全部结果。没有拟合，也没有使用修正倍率。

| 数据集 | 工况数 | 计算版本 | 换热量偏差 | 出口状态偏差 | 结论 |
|---|---:|---|---|---|---|
| CETIAT 百叶片盘管，冷凝（IEA HPT Annex 54） | 8 | Pro 逐管网络 | +0.8～+2.7% | 过冷度 +1.0～+3.0 K | 换热量 8/8 在 ±5% 内；过冷度 2/8 在 ±2 K 内 |
| CETIAT 百叶片盘管，蒸发 | 12 | Pro 逐管网络 | +0.8～+1.8% | 过热度 +0.9～+3.3 K | 换热量 12/12 在 ±5% 内；过热度 11/12 在 ±3 K 内 |
| 谭爱华 2015 风机盘管湿工况 | 62 | Pro 逐管网络（按论文流路） | 平均 +3.9%（−1.4～+11.5%） | 显热比平均 −0.028 | 58/62 达标（Qw ±10%，SHR ±0.05） |
| 谭爱华 2015 风机盘管湿工况 | 55 | **本仓库**（整盘模型） | 平均 +5.7%（+0.6～+11.9%） | 显热比平均 −0.040 | 36 台稳健通过、2 台条件通过；17 台显热比超差 |
| 康海军 1994 平片空气侧 | 8 个试件 | 本仓库 | — | — | j/f 交叉参考：7/8 在 −22%～+17% 内 |
| Batista 2022、Joppolo 2015 | 9 + 6 | 仅外推 | — | — | 超出所有已发表关联式的范围，只作参考，不计入验收 |

**已知问题：**冷凝器过冷度偏大：CETIAT 上偏大 2.3～3.0 K，Joppolo 上偏大 2.5～5 K。

制冷剂工况需要逐管回路模型。该模型属于 Fintube HX Pro，不在本仓库中；这里公开其计算结果，以便核查。

**为什么整盘模型与逐管网络的结果不同？**本仓库的整盘模型把整个盘管当作理想逆流，也无法表示不通水的盲管。Pro 逐管网络则按实际流路逐排计算。在两种方法都计算过的 48 台谭爱华盘管上，整盘模型平均 +5.3%，逐管网络平均 +4.6%。这部分差距几乎全部来自有 2 根盲管的 pre‑03# 盘管：该盘管上两者相差 5.3 个百分点，其余盘管平均只差 0.04 个百分点。表中两个平均值（+5.7% 和 +3.9%）不同，还因为逐管网络另外计算了 14 台盘管（post‑03#/04#），整盘模型没有计算这些盘管。

整盘结果可用 `python tools/run_measured_v6_tan.py --check` 复现：同一平台上逐位一致；换用不同 CPU 或数学库时，换热量偏差的差别在 1e-7 以内。

早期的 v5 验收集（[`validation/measured/`](validation/measured/README.zh-CN.md)，6 个工况）已被取代。原因有两点：水盘管工况的风道有旁通，边界条件不完整；CETIAT 工况当时用平片关联式代替了百叶片。旧表保留在该目录中，仅供追溯。

## 可复现的软件对照

[`references/python-hvac/`](references/python-hvac/README.md)提供固定版本上游复现与水例映射。映射水例为**4363.49W**，参考复现为**4084.46W**，差异+6.83%。这是几何/模型定义不同的软件交叉比较，不是实测精度或拟合结果。

**0.1.0.dev16**（核心 API 2）新增以下内容，所有旧结果保持逐位不变（Community 72 例、专业版 289 例逐位核对）：

- **`model.pressure_scope`**：缺省或`"legacy_v0"`时输出与以前完全相同；`"v1"`时输出`air_pressure_drop_breakdown_pa`（芯体摩擦、进出口、加速、湿附加）和`air_pressure_drop_total_pa`。经核对原文，Wang 1999/2000/2002 的摩擦系数在数据整理时**已包含**进出口损失，因此标为`included_in_f`、不再重复叠加；原文整理时扣除的加速项 (1+σ²)(ρ1/ρ2−1) 予以补入。`v1`要求填写`geometry.fin_surface`（`"bare_aluminum"`裸铝或`"hydrophilic"`亲水涂层，不提供“未知”）。
- **湿工况空气摩擦**（无亲水涂层的平片）：Wang、Lin、Lee 2000（IJHMT 43:1869，式 11–15；31 个无涂层样本，Re 300–5000，片距 1.19–3.2 mm）。亲水涂层、百叶片和波纹片，或超出样本范围时，湿附加标为`not_computed`并说明原因，换热量不受影响。
- **声明式外推**：平片`geometry.fin_pitch_extrapolation: true`（片距 8.7–12 mm，只放宽片距及由片距决定的水力直径）；`geometry.row_extrapolation: "saturate_at_row_6"`配合逐排接口`air_side_factors_by_row`，供 7–12 排的逐管网络使用（第 1–6 排取 6 排平均值，第 7 排起取第 6 排局部值 6·j(6)−5·j(5)）。本仓库的整盘模型仍拒绝超过 6 排。所有外推结果都会标注，不作为验收依据。
- **结构化中文错误**`fintube_hx.errors.ModelRangeError`（`ValueError`的子类），包含字段、允许范围、关联式出处和可选的降级路径；条缝片、Dc < 6.9 mm 小管径、顺排、扁管，以及 CoolProp 未内置的混合工质（如 R454B），都会明确提示“本版本不支持，规划中”。

**0.1.0.dev14**在湿表面单元中支持`subzero_evaporation: "initial_frost"`（清洁表面开始结霜的瞬时极限：沉积按冰计入融化焓，饱和曲线在0 ℃分段；不计霜层厚度、霜层热阻与堵塞）。集总接触因子制冷剂模型会拒绝该选项，它用于严格湿表面的逐管网络。**0.1.0.dev13**新增可选`geometry.contact_conductance_w_m2_k`（翅片套管-管接触热导，按管外表面积π·Do·L计）和`geometry.inner_fouling_resistance_m2_k_w`（管内污垢热阻），均按常数串联、不设默认值；不填时一切不变。**0.1.0.dev12**新增蒸发器可选项`model.subzero_evaporation: "dry_only"`：表面温度≤0 ℃时，只要不低于当地进风霜点（CoolProp在0 ℃以下按冰面饱和）、即不发生结霜，就按干表面计算；低于霜点则因需要结霜模型而拒绝。判定以制冷剂温度代表表面温度，偏保守。默认（`reject`）不变。**0.1.0.dev11**新增`geometry.tube_type: "microfin"`及模块`fintube_hx.microfin`：NIST TN 2224（Kedzierski & Lin 2023）微肋管几何与沸腾Nu关联式（含混合物滑移修正）、NISTIR 6333（Choi、Kedzierski、Domanski 1999）两相压降；几何参数超出TN 2224数据库范围即报错。本核心的集总水盘管明确拒绝微肋管，关联式供扩展调用（专业版蒸发器网络使用）。目前仅完成对原文算例和几何的实现核对，尚无整盘实测验收。**0.1.0.dev10**新增显式声明的`correlation_range_tolerance`，不填时一切不变。**0.1.0.dev9**新增百叶片、人字波纹片与Schmidt翅片效率（模块`fintube_hx.airside`），未设`fin_efficiency_method`的平片算例逐位不变。**0.1.0.dev8**新增可选`wet_surface_model`（模块`fintube_hx.wet_surface`），不填时所有既有结果逐位不变。**0.1.0.dev7**新增`fin_count`、`exposed_tubes`及实测验证数据集；未提供这两个字段时，所有既有结果逐位不变。

制冷剂整体分段模型未提供`solver.max_iterations`时，默认采用`max(200, 2*segments+20)`；用户显式上限不增加，预算偏低会提示，未收敛仍退出2。**0.1.0.dev6**纳入此修复，不改变传热方程。

三轮外部评审每一项的状态（已修复/已澄清/未解决）见[docs/EXTERNAL_REVIEW_STATUS.md](docs/EXTERNAL_REVIEW_STATUS.md)。[v3反馈复核](docs/EXTERNAL_REVIEW_V3.md)补充固定工况湿分支对照并更新版本状态。[外部评审复核](docs/EXTERNAL_REVIEW_2026-10-13.md)逐项列出判断、修正与依据。**0.1.0.dev5**修正对角最小流通间隙的翅片阻塞项与反求括根错误提示；现有横向间隙控制的基准容量不变。

## 许可

原创代码遵循[MIT](LICENSE)；第三方依赖及python-hvac改编表达式保留各自许可与署名。见[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、[CORE_API.md](CORE_API.md)、[CONTRIBUTING.md](CONTRIBUTING.md)。
