# custom — 路由器配置定制区

本目录存放 OpenClashConfig 仓库的定制内容。当前定制目标只有一份配置：`cfg/ClashMainConfig.ini`（基于上游 `Custom_Clash_Full_Fallback.ini` 的深度分流故障转移版）。

## 文件清单

| 路径 | 用途 |
|---|---|
| [`check.py`](./check.py) | ClashMainConfig.ini 深度检查工具，每次修改后必须运行 |
| [`rule/`](./rule/) | 新增分流规则源文件（格式与引用方式见其 README） |

## 修改流程（强制约定）

1. 只改 `cfg/ClashMainConfig.ini`；仓库其余文件不动（上游规则、脚本、文档保持原样）。
2. 修改后运行深度检查，全部通过才能提交：
   ```bash
   python3 -I custom/check.py
   ```
3. 每次修改一次 git commit，改完推送到远程（`git push origin main`）。
4. 提交信息用 conventional commits 风格（`feat(cfg): ...` / `fix(cfg): ...`）。

## 模板语法速查（改文件前必读）

- **ruleset 顺序即分流优先级**，从上往下遍历，先命中先生效；调整顺序会改变分流结果。
- `ruleset=组名,来源[,间隔秒]`：
  - 内联来源：`[]GEOSITE,名`、`[]GEOIP,名[,no-resolve]`、`[]FINAL`（兜底，必须最后一条且唯一）。
  - 远程来源：`clash-domain:`（.mrs/.yaml 域名集）、`clash-classic:`（classic payload yaml）、`clash-ipcidr:`，或无前缀（默认按 surge 语法解析 `.list`）。
  - 内联规则不需要更新间隔；远程规则的间隔秒建议 1800/28800。
- `custom_proxy_group=组名`类型`成员...`[测试URL`interval[,timeout][,tolerance]]`：
  - 类型：`select` 手动 / `url-test` 自动最低延迟 / `fallback` 按候选顺序故障转移 / `load-balance` 负载均衡。
  - 成员：`[]组名` 引用其他组（允许前向引用）；正则按节点名筛选；`[]DIRECT` 内置直连。
  - fallback 只测连通性，不判断解锁能力；重要业务组末位是否带 `[]🎯 全球直连` 决定"代理全挂时是否裸连"，修改候选链时注意保持原有语义。
  - 常用参数：url-test 用 `300,,50`（300 秒测速、默认超时、50ms 容差）；fallback 用 `300,5`（300 秒、5 秒超时）。
- `ruleset` 总数上限 64（`max_allowed_rulesets` 兼容值），新增前先看剩余空位。
- 尾部 `enable_rule_generator=true`、`overwrite_original_rules=true` 固定不动。

## 已知事实

- 本仓库是 Aethersailor/Custom_OpenClash_Rules 的 fork；`cfg/ClashMainConfig.ini` 头部标注了模板使用地址（jsDelivr，指向本仓库 main 分支）。
- 模板改动只影响下一次订阅转换的产物；路由器侧需重新更新订阅才能生效。
- 2026-11-19：已删除 🇫🇷 法国 / 🇳🇱 荷兰 / 🇷🇺 俄罗斯 / 🐢 低倍率 四个节点分组，相关节点名现归入 🌐 其他地区。
