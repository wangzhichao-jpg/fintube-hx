# 版本发布核对清单 (Release Checklist)

本清单用于项目维护者在发布新版本时进行质量核验与多平台同步检查。

---

## 1. 发布前验证

- [ ] **测试与质量**
  - [ ] 本地全量单元测试通过：`pytest -q`
  - [ ] 多平台自动化 CI（Linux / Windows）运行通过
- [ ] **版本号与元数据**
  - [ ] 更新 `src/fintube_hx/__init__.py` 中的 `__version__`
  - [ ] 更新 `pyproject.toml` 中的版本声明与构建依赖
  - [ ] 核验 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 完整性
- [ ] **文档与示例**
  - [ ] 检查 `README.md` 中的安装说明、快速开始与代码示例
  - [ ] 校验 `examples/` 目录下所有案例均可正常执行
  - [ ] 验证 `references/python-hvac/` 参考复现脚本可独立运行
- [ ] **打包构建**
  - [ ] 构建标准源码包与 Wheel 包：`pip wheel --no-deps .`
  - [ ] 生成发布资产的 SHA-256 校验文件（`SHA256SUMS.txt`）
  - [ ] 在全新的隔离虚拟环境中安装 Wheel 包并执行冒烟测试

---

## 2. 发布与同步

- [ ] **Git 标签与提交**
  - [ ] 在 `main` 分支创建版本标签：`git tag vX.Y.Z`
  - [ ] 同步推送到 GitHub 与 Gitee 镜像仓库
- [ ] **Release 发布产物**
  - [ ] 在 GitHub Releases 与 Gitee Releases 上传源码包、Wheel 包与校验和清单
  - [ ] 匿名下载远端附件，验证文件哈希与本地构建产物完全一致
- [ ] **发布后冒烟测试**
  - [ ] 从公开镜像下载 Wheel 并验证独立安装运行正常
