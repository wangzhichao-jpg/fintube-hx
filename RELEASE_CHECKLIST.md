# Community发布检查单

状态：Community 0.1.0.dev4已在两边公开；同提交/标签、匿名clone/逐文件SHA和GitHub Ubuntu/Windows CI已核验。

所有者已授权：GitHub wangzhichao-jpg/fintube-hx、Gitee bigtaurus/fintube-hx，两边公开；原创代码MIT。无需向助手提供账号密码或令牌，复用现有已授权工具凭据。

- [x] 所有者确认MIT；LICENSE和项目元数据已加入，候选升至0.1.0.dev4，保留dev3旧wheel
- [x] 两个目标与公开可见性已确认；只初始化允许清单生成的公共树，不初始化项目总根或Professional
- [x] 本次85文件允许清单/源码、参考数据、文档和完整依赖许可复审
- [ ] 在独立目录安装最终wheel，确认不依赖Professional；源回归与wheel烟测
- [x] 从允许清单创建干净公共树/单一Git历史，仅向批准目标推送；历史无私有代码
- [ ] GitHub/Gitee标签/说明/附件SHA单独核对；不做双向合并或假定自动同步
- [x] GitHub Ubuntu/Windows实际CI通过；两端公开匿名clone与参考说明随源码可读
- [ ] 正式稳定版/更广Python及平台安装矩阵后续验收（不以dev4预发行提前关闭）

已准备：源树允许清单、依赖与第三方许可、48项本地回归、独立公共wheel、固定python-hvac原例题复现与限制说明、贡献文档与只读CI模板。48项数量是当前证据，不代表未来CI自动通过。

不得发布：私有网络/工程工作台、私有源/独立安装包、客户或商业材料、旧完整ZIP、项目历史总根。PyInstaller不是代码保密机制。本清单不是原创许可声明，也不是模型精度证明。
