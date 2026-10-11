# 贡献指南 (Contributing Guide)

欢迎参与 **Fintube HX** 的开发与改进！本项目致力于构建专业、严谨且易于使用的翅片管换热器仿真计算核心。

---

## 开发环境配置

本项目基于 **Python 3.12** 开发，推荐使用 `venv` 或 `uv` 构建隔离环境：

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安装开发依赖与可编辑包
pip install -r requirements-development-lock.txt
pip install -e ".[test]"

# 3. 运行自动化测试
pytest -q
```

---

## 提交规范

### 1. 代码风格与质量
- 保持代码清晰自解释，关键物性调用与经验公式需注明文献来源及适用边界（如 Reynolds 数、Prandtl 数范围）。
- 所有涉及热工与流动的函数必须遵循国际单位制（SI），内部状态计算保持物理量守恒（质量与能量闭合）。
- 提交前请确保现有测试套件全部通过：`pytest`。

### 2. 物理模型与关联式引入
如需引入新的传热/阻力关联式或流体模型：
- 请在文档或代码注释中明确其原始论文、适用流体、几何结构及经验常数。
- 必须附带单元测试（包括常规工况、临界/边界工况以及异常输入校验）。
- 确保引入的模型遵守相关开源许可证要求，第三方依赖引入请在 `THIRD_PARTY_NOTICES.md` 中补充声明。

### 3. Issue 与 Bug 报告
在提交问题报告时，建议包含以下信息以方便快速定位：
- 最小可复现的输入配置（脱敏后的 JSON 文件）。
- 运行环境（操作系统、Python 版本、关键依赖库版本）。
- 预期输出与实际输出（附带控制台日志或异常 Traceback）。

---

## 分支与 Pull Request 流程

1. Fork 本仓库至个人账号。
2. 基于 `main` 分支创建特性分支（如 `feature/new-correlation` 或 `fix/inverse-solver`）。
3. 提交修改并书写清晰的 Commit Message。
4. 提交 Pull Request，并在描述中简要说明变更背景、修改范围及测试验证方法。
