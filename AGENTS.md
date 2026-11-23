# OpenClashConfig 工作流（给 Agent 的操作手册）

本仓库是路由器 OpenClash 的配置定制项目。日常任务：按用户指示修改 `cfg/ClashMainConfig.ini`（订阅转换模板），验证后提交推送并落地到路由器。

## 真相源与边界

- 唯一配置文件：`cfg/ClashMainConfig.ini`（subconverter ini 模板语法，不是 Clash 运行配置）。
- 新增分流规则源文件放 `custom/rule/`（格式约定见其 README.md）。
- 上游规则 URL（Aethersailor 的 Custom_Direct/Proxy、Steam_CDN、Port_Direct）保持指向源仓库，不换成 fork 地址（用户明确决定）。
- 禁止改动：路由器 cron、`/root/mp-final-prep/`（内核哈希锁 restore-stable-core.sh）、dropbear、防火墙、网络配置。不修改仓库其他目录（rule/ py/ 等上游内容）。
- 路由器另有 MagicPanel-默认.yaml 一条配置线（`/etc/openclash/config/MagicPanel.yaml`），与本模板互不相干，别混淆；其改造需求见 `custom/magicpanel-alignment-brief.md`。

## 修改流程（每次都走全，缺一不可）

1. **修改** `cfg/ClashMainConfig.ini`。同一文件的多次 Edit 必须串行（一个工具调用一次编辑），并行写同一文件会竞态损坏行。
2. **深度检查**：`cd /Users/astral/Workspaces/路由器/OpenClashConfig && python3 -I custom/check.py`。全绿才能提交；检查器报错先修配置。若使用了检查器不支持的新语法，先扩展 `custom/check.py` 并做阴性测试（故意破坏验证能抓到）再提交。
3. **正则语义验证**：新增/修改 filter 正则时，用样例节点名跑 Python 实测该进进的、不该进的不进，不凭肉眼。
4. **diff 复查**：`git diff` 逐行读一遍，确认只有预期改动。
5. **提交推送**（用户已默认授权，无需再问）：`git add cfg/ClashMainConfig.ini && git commit -m "feat(cfg): ..." && git push origin main`。消息用 conventional commits（feat/fix/refactor/docs/style(cfg)）。
6. **落地路由器**：`zsh -ic 'ocupdate [检查分组名]'`（本机 ~/.zshrc 已定义；等效 `ssh root@10.0.1.1 "sh /root/oc-quick-update.sh [检查分组]"`）。默认检查分组 WireGuard：更新完成后内核里必须能找到它，找不到就说明新配置没生效。**只能验证「分组存在」，验证不了成员顺序**——纯链序改动用默认即可，顺序另按第 7 步核对。脚本会自动给模板地址加时间戳破后端缓存 → 更新订阅 → 等配置生成 → 重启内核 → 核对分组（全程约 10-30 秒，重启内核代理断几秒）。脚本副本在 `custom/oc-quick-update.sh`，刷固件覆盖层清空后从这里重新放回 `/root/`。
7. **API 实测复核**（结构性改动必做）：
   ```bash
   ssh root@10.0.1.1 "SECRET=\$(uci -q get openclash.config.dashboard_password); curl -s -H \"Authorization: Bearer \$SECRET\" 'http://127.0.0.1:9090/proxies'" > /tmp/mihomo.json
   python3 -I 解析 /tmp/mihomo.json 核对组数/链序/默认选中/检查分组存在
   ```

## 模板语法速查（细节见 custom/README.md）

- `ruleset=组名,来源[,间隔秒]`，顺序即分流优先级，总数 ≤64。内联：`[]GEOSITE,x`、`[]GEOIP,x[,no-resolve]`、`[]FINAL`（唯一且必须最后）。远程：`clash-domain:`/`clash-classic:`/`clash-ipcidr:` 只能接对应 payload 的 yaml/mrs，surge 语法的 .list 无前缀直引。
- `custom_proxy_group=组名\`类型\`成员...\`[测试URL\`interval[,timeout][,tolerance]]`。类型 select/url-test/fallback/load-balance。成员 `[]组名` 引用（允许前向引用）、正则筛节点、`[]DIRECT`。url-test 参数 `300,,50`，fallback `300,5`。
- fallback 只测连通性不解锁能力，取首个存活项（链中成员不得重复）；select 默认选中第一项。
- 组名带 emoji，url-test 组命名带"自动/测速"后缀。地区字母码正则用 `(?<![a-zA-Z])[xX][yY][zZ]?（可选尾字母）(?![a-zA-Z])` 形式防子串误匹配。

## 已知坑

- **后端缓存**：api.asailor.org 按模板 URL 缓存转换结果，ocupdate 的时间戳参数是唯一可靠绕过；模板地址01（jsDelivr）另有约 12h CDN 缓存，急用走 raw 地址。
- **并行编辑竞态**：同一文件多个 Edit 并行会粘连/丢行（历史上吃掉过整组定义），必须串行。
- 路由器是精简 OpenWrt：无 python3/stat/hostname；测 API 节点名的 URL 编码在本机做好再传。
- mihomo API secret 不在 yaml 里，取 `uci -q get openclash.config.dashboard_password`。
- ✅/❌类 Emoji 有 U+FE0F 变体选择符陷阱，替换含 emoji 的字符串前先 hexdump 核对字节。
- 组名引用遍布所有候选链：删组/改名用 replace_all 并随后 grep 残留归零；从排除正则删除地区关键字时同步确认对应节点有池可归。

## 用户偏好

- 每次修改默认 commit+push+ocupdate，不用重复询问。
- 改动交付说清：改了什么、验证证据（检查器+API 实测）、剩余影响。
- 候选链设计惯例：AI 组=美国自建测速→家宽自动→日本自建测速→…（住宅 IP 风控加固）；主链=新加坡自建测速→美国自建测速→日本自建测速→…；谷歌统一走 🇬 谷歌服务（含 YouTube/Gemini/FCM）；Netflix/Disney+/HBO/PrimeVideo/DAZN/Viu 归 🇸🇬 新加坡媒体；Telegram/PT/非标端口/Steam/苹果/微软直连优先；隧道节点（路由/WireGuard/Mieru/Juicity/Tailscale）归 🚇 WireGuard 组（默认直连）并被自动选择/其他自动排除。
- 用户网络：电信线路；自建池带宽充足；美国自建 IP 质量最好、新加坡自建看流媒体、日本自建延迟好看但电信吞吐一般。
