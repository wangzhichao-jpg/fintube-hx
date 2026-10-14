# Fintube HX Community

[ [English](README.md) | **简体中文** ]

[![CI](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml/badge.svg)](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](pyproject.toml)

独立的翅片管换热器基础计算核心。[GitHub](https://github.com/wangzhichao-jpg/fintube-hx) · [Gitee](https://gitee.com/bigtaurus/fintube-hx)

## 当前实现

| 对象 | 传热模型 | 几何与压降 |
|---|---|---|
| 纯水盘管 | **整体逆流ε-NTU**；干态显热或湿接触近似 | 输入UA，或连续平片/光管错排几何UA；可输出**干空气芯体摩擦**与**水侧直管摩擦** |
| 蒸发器 | 恒压P-h、逆流空气迭代、**轴向分段**；输入UA均分 | **仅输入UA**，没有制冷剂几何传热关联式或压降 |
| 冷凝器 | 同上，单相单元通过焓及段内温度联立体现有限热容量 | **仅输入UA**，没有制冷剂压降 |

水几何采用Wang-Chi平片j/f、Hausen/Gnielinski管内传热、Churchill摩擦与等面积环形翅片效率近似。湿几何会按增强空气侧系数重新计算**湿翅片效率代理值**，但不等同于严格部分湿模型。

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
- 压降是**直管/芯体摩擦分项**，不是完整盘管或系统总阻力；未含回弯、集管、进出口收缩/扩张及湿膜额外损失。

## 工程模型范围

水盘管按入口水温选择湿/干接触近似，不计算局部壁温与部分湿面积。空气物性取入口，水物性采用迭代平均温度。Wang使用翅片套管外径Dc而非裸管外径Do；套管壁厚取片厚时Dc=Do+2tf，这是采用的等厚套管口径，实际成形尺寸未独立输入。等效片数为L/片距，边缘开口采用理想化几何。

没有真实逐管回路、逐排交叉流、中途分合流、溶液物性、百叶/波纹片、强化管、污垢/接触热阻或结霜模型。蒸发温度≤0°C会拒绝；关联式区间外不自动外推或裁切几何。

## 可复现的软件对照

[`references/python-hvac/`](references/python-hvac/README.md)提供固定版本上游复现与水例映射。映射水例为**4363.49W**，参考复现为**4084.46W**，差异+6.83%。这是几何/模型定义不同的软件交叉比较，不是实测精度或拟合结果。

制冷剂整体分段模型未提供`solver.max_iterations`时，默认采用`max(200, 2*segments+20)`；用户显式上限不增加，预算偏低会提示，未收敛仍退出2。**0.1.0.dev6**纳入此修复，不改变传热方程。

[v3反馈复核](docs/EXTERNAL_REVIEW_V3.md)补充固定工况湿分支对照并更新版本状态。[外部评审复核](docs/EXTERNAL_REVIEW_2026-10-13.md)逐项列出判断、修正与依据。**0.1.0.dev5**修正对角最小流通间隙的翅片阻塞项与反求括根错误提示；现有横向间隙控制的基准容量不变。

## 许可

原创代码遵循[MIT](LICENSE)；第三方依赖及python-hvac改编表达式保留各自许可与署名。见[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、[CORE_API.md](CORE_API.md)、[CONTRIBUTING.md](CONTRIBUTING.md)。
