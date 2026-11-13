# 来源与改动记录

本技能是知办AI项目的中文适配稿，版本 0.1.0，整理日期 2026-09-18。技能工作流按本项目规划和边界重新编写，不是上游项目官方产品或认证实现。

## 本项目依据

- `知办AI本期产品规划结论-中国市场验证-2026-09-18.md`：九位新增角色、二十七项任务、输入输出和权限边界。
- `知办AI数字员工命名与配置全量审计-2026-09-18.md`：正式名称、角色边界及L3升级要求。
- `KB-QAT-101《软件测试设计、执行证据与发布门禁》`：该角色当前公开方法知识映射。

## 开源方法参考

- [msitarzewski/agency-agents / testing/testing-evidence-collector.md](https://github.com/msitarzewski/agency-agents/blob/ad9264e309bd5e5422c04784372d7841b1e5d604/testing/testing-evidence-collector.md)
  - 锁定提交 `ad9264e309bd5e5422c04784372d7841b1e5d604`；许可：MIT。
- [msitarzewski/agency-agents / testing/testing-test-results-analyzer.md](https://github.com/msitarzewski/agency-agents/blob/ad9264e309bd5e5422c04784372d7841b1e5d604/testing/testing-test-results-analyzer.md)
  - 锁定提交 `ad9264e309bd5e5422c04784372d7841b1e5d604`；许可：MIT。

## 适配说明

复用的是任务拆解、证据链、检查表和失败降级等方法；已删除上游平台专属工具名、路径、命令、固定阈值和自动外发动作。企业规则、权限、数据和最终批准必须由实际部署环境提供。技能包不安装工具，也不声明已执行任何业务动作。

测试材料和人工标准答案没有写入本技能。验收条目只定义通用合格条件，避免运行时泄露盲测答案。

Apache-2.0和MIT许可文本随内层技能包提供。保留来源不代表第三方为知办背书，也不保证第三方连接器或服务免费可用。
