# Fintube HX

[![CI](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml/badge.svg)](https://github.com/wangzhichao-jpg/fintube-hx/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](pyproject.toml)

> 开源翅片管换热器热工水力仿真与设计计算核心库  
> 国内镜像仓库：[Gitee / bigtaurus / fintube-hx](https://gitee.com/bigtaurus/fintube-hx)

**Fintube HX** 是一个基于 Python 3.12 的翅片管换热器（Fin-tube Heat Exchanger）热工与流动计算核心库。

本项目专注于提供清晰、严谨、物理守恒的换热器基准模型，覆盖水盘管、蒸发器与冷凝器的校核计算及流量反求。计算引擎基于 [CoolProp](http://www.coolprop.org/) 高精度物性库与公开发表的传热流阻经验关联式，支持命令行批处理、单参数扫描及原生 Excel / CSV 报表导出。

---

## 主要特性

- **三种经典换热器模型**
  - **水盘管（Air-to-Water Coil）**：支持冷却去湿与显热加热工况，提供集总参数模型与平片管束几何解析模型。
  - **空气蒸发器（Air Evaporator）**：支持吸热汽化与湿空气传热耦合，基于平衡干度与相变状态核算。
  - **空气冷凝器（Air Condenser）**：支持过热气相降温、两相冷凝与过冷液相段的传热核算。
- **平片管束几何与经验关联式**
  - 连续平平翅片（Plain Fin）与错排圆管（Staggered Tubes）参数化几何解析。
  - 空气侧对流传热与阻力采用经典 Wang & Chi (2000) 关联式。
  - 管内单相对流传热采用 Gnielinski (1975) 及 Hausen 内部流动模型，摩擦阻力基于 Churchill 关联式。
- **稳健的反求求解器**
  - 基于有界二分 / Brent 算法，支持指定出风/出水温度或过热度/过冷度的质量流量反求。
  - 严格校验物性状态与相平衡，执行双侧能量守恒闭合检查。
- **工程化数据接口与工具链**
  - 采用严格规范的 JSON Schema 描述几何与工况，结果保留完整的计算快照与溯源信息。
  - 原生 CLI 工具支持单工况评估、批量计算与单参数扫描。
  - 原生生成多工作表 Excel（.xlsx）和 CSV 报表，便于工程归档与数据分析。
- **参考软件对照基准**
  - 内置对国际经典开源项目 [TomLXXVI/python-hvac](https://github.com/TomLXXVI/python-hvac) 典型盘管案例的复现环境与几何比对说明。

---

## 快速开始

### 1. 安装环境

推荐在 Python 3.12 虚拟环境中安装：

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 从锁定的依赖文件安装
pip install -r requirements-development-lock.txt
pip install -e .
```

国内用户可使用清华镜像源加速安装：

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-development-lock.txt
pip install -e .
```

### 2. 命令行使用

**查看支持的能力与模型**：
```bash
fintube-hx capabilities
```

**运行单工况仿真并导出 Excel 报告**：
```bash
fintube-hx run examples/water_geometry.json --output output/result.json --xlsx output/result.xlsx
```

**执行参数扫描（例如风量对换热量的影响）**：
```bash
fintube-hx scan examples/water_dry.json --parameter air.volume_flow_m3_h --values "[800,1000,1200]" --output output/scan.json --xlsx output/scan.xlsx
```

**运行测试套件**：
```bash
pytest -q
```

### 3. Python API 调用示例

```python
from fintube_hx.engine import run_case
from fintube_hx.storage import load_case

# 载入案例配置
case = load_case("examples/water_geometry.json")

# 执行热工计算
result = run_case(case)

# 输出计算结果
print(f"换热量: {result['heat_transfer_w']:.2f} W")
print(f"出风干球温度: {result['air_out']['t_db_c']:.2f} ℃")
print(f"水侧出口温度: {result['fluid_out']['temperature_c']:.2f} ℃")
print(f"空气侧阻力: {result['geometry_model']['air_core_friction_pressure_drop_pa']:.2f} Pa")
```

---

## 物理约定与输入规范

为保证计算的确定性与物理自洽，输入定义遵循以下规范：

| 物理量 | 单位 | 说明 |
| :--- | :--- | :--- |
| **温度** | ℃ | 干球温度、介质入口温度等 |
| **压力** | Pa | 绝对压力（非表压），例如标准大气压 `101325 Pa` |
| **风量** | m³/h | 入口实际体积流量（非标态体积） |
| **相对湿度** | 0.0 ~ 1.0 | 湿空气相对湿度比例（例如 50% 写作 `0.5`） |
| **几何尺寸** | m | 管径、节距、片厚、片距等尺寸均采用标准米制 |
| **质量流量** | kg/s | 换热介质质量流量 |

- **制冷剂状态**：对于蒸发与冷凝工况，两相入口需明确指定绝对压力与焓值（P-h）或压力与饱和干度，避免两相区温度定义歧义。
- **结果不可逆覆盖**：输出结果包含独立的计算快照与输入副本，计算过程不修改原始输入文件。

---

## 基准测试与验证

本项目在 [`references/python-hvac/`](references/python-hvac/README.md) 中提供了与经典换热器库 [TomLXXVI/python-hvac](https://github.com/TomLXXVI/python-hvac)（commit `9424756`）的复现与对比验证：

- **基准复现**：通过独立的重跑脚本复现了原始 Notebook 的计算结果（水冷盘管 4084 W、蒸发器 5915 W、冷凝器 7635 W）。
- **几何模型对照**：在水盘管案例中，将原模型的连续等效管排映射为标准整管排结构后，无外加校正因子的纯几何预测换热量偏差为 +6.83%，详细说明参见参考文档。

---

## 模型范围与边界

本项目定位为**轻量、可扩展的热工计算核心**，目前的模型边界如下：

1. **翅片与管束类型**：当前几何模块针对连续平平翅片（Plain Fin）与光管错排结构，波纹片、百叶窗翅片及内螺纹强化管暂未内置于本开源库。
2. **流动配置**：提供集总参数与基础整排逆交叉流近似；制冷剂复杂分支网络与非均匀风场 CFD 耦合求解不在当前轻量内核范畴。
3. **工程适用性**：经验关联式基于公开发表文献，在标准实验参数范围内具有良好代表性；工程设计与制造选型建议结合实测数据校准。

---

## 开源协议与引用

- **原创代码**：本项目原创代码遵循 [MIT License](LICENSE)。
- **第三方关联式与依赖**：本项目使用了 CoolProp、SciPy、ht、fluids 等开源成果，部分翅片几何计算借鉴了公开文献与相关实现，完整许可声明参见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

欢迎提交 Issue 和 Pull Request 参与交流与建设，详情请见 [CONTRIBUTING.md](CONTRIBUTING.md)。
