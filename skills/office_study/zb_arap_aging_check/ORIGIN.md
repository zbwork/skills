# 来源与改动记录

本技能是知办AI项目的中文适配稿，版本 0.1.0，整理日期 2026-09-18。技能工作流按本项目规划和边界重新编写，不是上游项目官方产品或认证实现。

## 本项目依据

- `知办AI本期产品规划结论-中国市场验证-2026-09-18.md`：九位新增角色、二十七项任务、输入输出和权限边界。
- `知办AI数字员工命名与配置全量审计-2026-09-18.md`：正式名称、角色边界及L3升级要求。
- `KB-ARP-101《应收应付匹配、账龄和对账差异》`：该角色当前公开方法知识映射。

## 开源方法参考

- [anthropics/knowledge-work-plugins / finance/skills/reconciliation/SKILL.md](https://github.com/anthropics/knowledge-work-plugins/blob/60eb554184003b8553eea733cce13c6e312cbeec/finance/skills/reconciliation/SKILL.md)
  - 锁定提交 `60eb554184003b8553eea733cce13c6e312cbeec`；许可：Apache-2.0。
- [anthropics/knowledge-work-plugins / finance/skills/variance-analysis/SKILL.md](https://github.com/anthropics/knowledge-work-plugins/blob/60eb554184003b8553eea733cce13c6e312cbeec/finance/skills/variance-analysis/SKILL.md)
  - 锁定提交 `60eb554184003b8553eea733cce13c6e312cbeec`；许可：Apache-2.0。

## 适配说明

复用的是任务拆解、证据链、检查表和失败降级等方法；已删除上游平台专属工具名、路径、命令、固定阈值和自动外发动作。企业规则、权限、数据和最终批准必须由实际部署环境提供。技能包不安装工具，也不声明已执行任何业务动作。

测试材料和人工标准答案没有写入本技能。验收条目只定义通用合格条件，避免运行时泄露盲测答案。

Apache-2.0和MIT许可文本随内层技能包提供。保留来源不代表第三方为知办背书，也不保证第三方连接器或服务免费可用。
