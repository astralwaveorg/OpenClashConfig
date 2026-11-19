# custom/rule — 自定义分流规则

本目录存放后续新增的分流规则源文件，与 `cfg/ClashMainConfig.ini` 配套使用。

## 文件格式约定

- 源文件使用 `.list`（Surge 规则语法），一行一条规则，`#` 开头为注释。
- 支持的类型与上游 `rule/` 目录一致：`DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`IP-CIDR`、`IP-CIDR6`、`SRC-IP-CIDR`、`SRC-PORT`、`DST-PORT`、`GEOIP` 等。
- IP 类规则默认加 `no-resolve`，避免为匹配 IP 而触发 DNS 解析。
- 编码 UTF-8，无 BOM，LF 行尾（`.gitattributes` 已约定 `*.list text eol=lf`）。
- 纯域名列表建议独立成文件并命名为 `Xxx_Domain.list`；含 IP/端口等复合条件的命名为 `Xxx_Classical.list`，便于区分引用方式。

## 在模板中的引用方式

在 `cfg/ClashMainConfig.ini` 的 ruleset 区按需添加（顺序即分流优先级，总数不超过 64 条）。前缀必须与文件内容格式匹配：

```ini
; surge 语法的 .list（默认类型，不加前缀）
ruleset=🎯 全球直连,https://cdn.jsdelivr.net/gh/astralwaveorg/OpenClashConfig@refs/heads/main/custom/rule/Xxx_Direct.list,28800
; mrs 域名集 / classic yaml（上游 rule/ 目录的派生格式）
ruleset=🎯 全球直连,clash-domain:https://cdn.jsdelivr.net/gh/astralwaveorg/OpenClashConfig@refs/heads/main/custom/rule/Xxx_Domain.mrs,28800
ruleset=🎯 全球直连,clash-classic:https://cdn.jsdelivr.net/gh/astralwaveorg/OpenClashConfig@refs/heads/main/custom/rule/Xxx_Classical.yaml,28800
```

说明：

- `clash-domain:` / `clash-ipcidr:` / `clash-classic:` 只能接对应 payload 格式的 `.yaml` 或 `.mrs`，不能直接接 surge 语法的 `.list`。
- 末尾数字是规则更新间隔（秒）。
- 内联写法 `ruleset=组名,[]GEOSITE,xxx`、`[]GEOIP,xxx[,no-resolve]`、`[]FINAL` 不需要文件。
- 若后端访问 raw.githubusercontent.com 失败，SubConverter-Extended 会自动回落 jsDelivr。
- 新增 ruleset 后必须运行 `custom/check.py` 深度检查，通过后才能提交。
