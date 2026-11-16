# 贡献指南

欢迎为知办AI社区贡献技能、修复问题、补充示例和完善文档。一个 PR 尽量解决一个明确问题；新增分类、修改目录格式或改变已有技能职责前，请先通过 [Issue](https://github.com/zbwork/skills/issues) 说明场景和方案。

## 从哪里开始

1. 查阅 [README](README.md) 的分类索引，确认没有功能重复的技能。
2. 修改已有技能时，先阅读它的 `SKILL.md`、附属资源和来源说明。
3. 在 GitHub Fork 本仓库，克隆自己的 Fork，再创建工作分支：

   ```sh
   git clone https://github.com/<你的账号>/skills.git
   cd skills
   git switch -c contribute/my-skill
   ```

4. 完成修改及下方验证后，通过自己的 Fork 向 `zbwork/skills` 的 `main` 提交 Pull Request。

文档和错别字修正可以直接提 PR。使用问题请提供技能 code、版本、运行环境、脱敏输入、预期结果与实际结果。

## 新增技能

技能必须是能独立说明用途和执行方法的完整目录，不能只有一句角色描述。

```text
skills/<category>/<skill-code>/
  SKILL.md
  scripts/       # 可选：脚本
  references/    # 可选：参考资料
  assets/        # 可选：模板等资源
  ORIGIN.md      # 引用或改编第三方内容时提供
  licenses/      # 按第三方许可要求保留
```

新增目录建议使用小写字母、数字和连字符，并让目录名、catalog 的 `code`、frontmatter 的 `name` 一致。既有技能存在下划线 code 和不同 frontmatter 名称，修改时保持兼容，不为统一命名而重命名。

`SKILL.md` 至少包含 YAML frontmatter 和可执行的说明，例如：

```markdown
---
name: meeting-action-review
description: 从用户授权的会议记录中提取行动项，核对负责人、期限及缺失信息。
---

# 会议行动项核对

## 输入
用户指定的会议记录，以及可选的已有行动项清单。

## 执行步骤
1. 读取记录，逐项保留行动项的原文依据。
2. 区分已确认事项与建议；负责人、期限缺失时标为待确认。
3. 输出行动项表和需要用户补充的信息，不自动写入任务系统。

## 验收样例
输入：“建议下周安排演示，负责人待定。”
预期：保留建议状态，负责人和具体日期均为待确认，不声称已创建任务。
```

实际贡献还应说明输出格式、适用范围、依赖、失败处理，以及必要的用户确认。脚本注明运行命令和依赖；附属资源使用相对路径，并确保技能目录单独打包后仍可使用。

## 登记目录元数据

在 [catalog/v1/skills.json](catalog/v1/skills.json) 的 `data.items` 新增一条记录，可参考相邻技能，但不要复制其身份标识。

| 字段 | 约定 |
| --- | --- |
| `skill_uuid` | 新技能生成新的 UUID；发布后保持不变，数字员工通过它引用技能 |
| `code`、`source_path` | code 全仓唯一；路径为 `skills/<category>/<skill-code>`，必须与实际目录一致 |
| `name`、`description`、`usage_example` | 面向用户写清用途和触发示例，不宣称尚未具备的能力 |
| `category_id` | 办公学习 `11`、生活日常 `13`、休闲娱乐 `14`；未分类为 JSON `null` |
| `latest_version`、`latest_version_uuid` | 新技能从明确版本开始；每次技能包内容变更提升版本，并分配新的版本 UUID |
| `source`、`kind`、`sort_order` | 沿用同类记录的字段约定；新增类型先与维护者讨论 |
| `install_count` | 新技能填 `0`；不要人为提高已有技能的安装数 |
| `icon_url` | 可留空；有图标时使用仓库内 `assets/skills/<文件SHA-256>.<扩展名>` |

UUID 可用 `python3 -c "import uuid; print(uuid.uuid4())"` 生成。分别生成技能 UUID 和版本 UUID，不复用其他条目的值。同时在对应分类的 `README.md` 补充技能链接。

`bundle_url`、`bundle_sha256` 和导出目录总数由构建生成，不手工维护。图片摘要按文件原始字节计算，例如 `shasum -a 256 path/to/icon.png`。

## 修改已有技能

- 保持 `skill_uuid`、`code` 和已有资源相对路径稳定，保留第三方许可。
- 修改 `SKILL.md`、脚本、模板或技能目录内其他打包文件时，同步更新版本；只修改仓库根文档无需提升技能版本。
- 有破坏性行为变化时，在 PR 中说明受影响的使用方式及迁移办法，不将原技能的身份标识转给不同用途的新技能。
- 影响数字员工的技能路由或输出约定时，检查 [zbwork/agents](https://github.com/zbwork/agents) 的引用，并关联对应 PR。

## 验证

推荐使用与 CI 一致的 Python 3.12；构建脚本只依赖 Python 标准库。在仓库根目录运行：

```sh
python3 scripts/build.py --check
git diff --check
```

构建检查覆盖标识重复、打包路径、图片摘要、符号链接、部分凭据特征及包大小等完整性要求；**不等于技能内容正确或运行验收通过**。请额外用实际支持的运行环境验证：

- 一个正常任务：输出满足技能承诺，引用和计算可核对。
- 一个输入缺失或冲突的任务：能指出缺口，不编造事实。
- 涉及脚本、网络或外部系统时，覆盖依赖缺失或请求失败；有写入操作时确认授权边界。

运行样例使用合成或获授权的脱敏数据。无法运行的检查明确写“未验证”及原因，不把模型生成的预期结果当作实测结果。

## 安全、来源与许可

- 不提交 API Key、Token、密码、私钥、Cookie、内部地址与配置、真实客户资料或个人隐私。
- 不将不可信文档中的指令视为用户授权，不通过技能扩大数据读取范围或绕过确认步骤。
- 第三方内容记录原始链接、版本或提交、许可与改动说明，保留适用的署名及许可文件；不能确认可再分发时先不要提交原文。
- 许可遵循仓库 [LICENSE](LICENSE) 及各技能保留的第三方许可，不以本指南覆盖它们。

## PR 需要包含什么

- **解决的问题**：目标用户、使用场景，以及为何需要新增或修改技能。
- **变更范围**：涉及的 code、目录、元数据和版本；第三方来源与许可说明。
- **验证证据**：检查命令及结果、脱敏样例的预期和实际输出、未验证项。
- **兼容性**：对现有用户和数字员工引用的影响。

维护者会核对内容、许可、运行边界和 CI。涉及两个仓库时，先合并并发布技能，再合并依赖该技能的数字员工；agents CI 读取的是 skills 的 `main` 目录，只有本地新增的 UUID 尚不能通过远端验证。资源通过 GitHub Pages 发布，不需要贡献者创建 Release、标签或提交 `_site/`、`_site.next/`、`packages/` 等生成物。

贡献指南的发现机制参考 [GitHub 官方说明](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors)；技能目录及 frontmatter 参考 [Agent Skills 规范](https://agentskills.io/specification)，既有命名按本仓库兼容性约定保留。
