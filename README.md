# 知办AI 官方技能

独立仓库：分类、技能目录、图标和完整可编辑源码。员工目录在 zbwork/agents，按稳定 skill_uuid 引用这里的技能。

- catalog/v1/skills.json：目录元数据；修改技能内容时提升 latest_version。
- skills/<分类 code>/<code>/：SKILL.md、脚本与参考资源，保留第三方许可。
- assets/skills/：SHA-256 命名图标。
- resource.json：本次 release 版本，每次发布更新。

```sh
python3 scripts/build.py --check
python3 scripts/build.py --local
```

正常构建生成 Releases 版本化包地址；--local 生成本地相对地址。用户推送 main 后工作流先上传并逐字节核对包，再发布 Pages。同名不同内容的包禁止覆盖；发布不读原服务器。

先发布 skills，再发布 agents；后者校验已发布的技能引用。首次用户推送之前 Pages 不可用。Codex 只做本地 Git 提交，不执行 push。

## 分类浏览

- [办公学习](skills/office_study/README.md)
- [生活日常](skills/daily_life/README.md)
- [休闲娱乐](skills/leisure_entertainment/README.md)
- [未分类](skills/uncategorized/README.md)

参考 [mattpocock/skills engineering](https://github.com/mattpocock/skills/tree/main/skills/engineering)：分类 README → 单技能目录 → SKILL.md 与附属资源。source_path 只定位源码，技能 UUID/code、包内路径与安装协议保持不变。原无分类的 code_daily_summary 仍保留 category_id=null，只在源码索引归入未分类。
