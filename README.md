# 知办AI 官方技能

官方技能源码仓库。按分类浏览，每个技能都有独立目录、SKILL.md 和完整附属资源。

## 分类

- [办公学习](skills/office_study/README.md)
- [生活日常](skills/daily_life/README.md)
- [休闲娱乐](skills/leisure_entertainment/README.md)
- [未分类](skills/uncategorized/README.md)

```text
skills/
  office_study/
    README.md
    <skill-code>/
      SKILL.md
      scripts/        # 有脚本的技能
      references/     # 有参考资源的技能
```

组织方式参考 [mattpocock/skills engineering](https://github.com/mattpocock/skills/tree/main/skills/engineering)。沿用既有分类与技能内容，不改变 UUID、code、版本或附属资源的相对路径。原无分类的 code_daily_summary 保持 category_id=null，在源码索引归入未分类。

## 维护与校验

- 技能内容在 skills/<分类 code>/<code>/ 中编辑。
- catalog/v1/skills.json 保存元数据与 source_path，assets/skills/ 保存原图标。
- 图标按文件 SHA-256 命名；技能内容更新应提升 latest_version。
- 保留各技能自带的第三方许可文件。

```sh
python3 scripts/build.py --check
```

PR CI 只做完整性校验；main 推送或手动运行 Deploy Pages 会构建目录、图标和技能包并部署到 GitHub Pages。不创建 Release 或标签。客户端匿名读取 https://zbwork.github.io/skills/catalog/v1/skills.json ，包通过同站点 packages/ 下载。数字员工在 [zbwork/agents](https://github.com/zbwork/agents)，通过稳定 skill_uuid 引用此仓库。

Codex 只能本地提交；远端推送由仓库所有者执行。
