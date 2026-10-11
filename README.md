# Fintube HX Community

翅片管换热器社区版，当前0.1.0.dev4开发候选，**尚未公开发布**。批准范围是基础模型开放；逐管网络和工程增强首发保留专业版。此目录不依赖专业版代码，也不包含旧完整发行包或客户材料。

## 当前实际能力

- 水盘管/蒸发器/冷凝器输入UA整体基线，水盘管平片光管几何整体模型。
- 水出口温度、蒸发过热、冷凝过冷的有界总流量反求，最终冷启动复算。
- 正向/反求API、CLI单点/批量/单标量扫描、完整JSON、CSV及原生XLSX快照/来源/限制。
- 9个理论/合成示例、异常/守恒/原有数值回归。

没有实际逐管网络、非均匀空气列、工程冷凝能力设计或社区版GUI表单。传入这些模型会明确拒绝，不能以整体模式悄悄替代。基础表单在计划下一阶段实施，不把CLI候选称成完整产品。

参照项目是python-hvac，不是OpenHVAC社区；已有适用MIT表达式来源见THIRD_PARTY_NOTICES。固定提交三类整盘管原例题已在独立环境复现，见`references/python-hvac/README.md`（公开独立复现脚本/锁/源树哈希/结果）。水几何显式近似映射对照+6.8314%，两器独立几何能力对照仍未完成；不将复现、同源表达式或近似几何对照宣称为实测精度或全面超过python-hvac。

## 安装和运行

Python3.12，推荐独立虚拟环境、国内源优先清华：

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe --index-url https://pypi.tuna.tsinghua.edu.cn/simple -c requirements-development-lock.txt -e ".[test]"
.\.venv\Scripts\python.exe -m fintube_hx capabilities
.\.venv\Scripts\python.exe -m fintube_hx run examples\water_geometry.json --output output\result.json --xlsx output\result.xlsx
.\.venv\Scripts\python.exe -m fintube_hx scan examples\water_dry.json --parameter air.volume_flow_m3_h --values "[800,1000,1200]" --output output\scan.json --csv output\scan.csv --xlsx output\scan.xlsx
.\.venv\Scripts\python.exe -m pytest -q
```

输入温度℃，绝对压力Pa，入口实际风量m³/h，RH比例0-1，尺寸m，总质量流量kg/s；两相入口用明确P-h，入口温度与焓必须二选一。不得把结果JSON直接当输入项目。风量不是标准状态体积。

## 授权和发布状态

所有者已明确原创公共代码采用MIT，见LICENSE；许可不等于产品精度或制造保证。第三方许可/署名独立保留。本次目标为公开仓库 https://github.com/wangzhichao-jpg/fintube-hx 和 https://gitee.com/bigtaurus/fintube-hx；远程实际发布结果另行记录，不把目标URL当作已经上线。首发检查见RELEASE_CHECKLIST.md，参与开发见CONTRIBUTING.md。Professional现已安装并复用本核心；基础物性/热模型/几何/反求/单位与合同不再双份维护。API及私有扩展方向见CORE_API.md，允许清单/边界见PORTING.md及实施计划。
