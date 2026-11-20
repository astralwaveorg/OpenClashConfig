# MagicPanel-默认 对齐改造交接文档

目标：把生产运行的 MagicPanel-默认 配置（分流规则 + 策略组）对齐到本仓库 `cfg/ClashMainConfig.ini` 的当前状态。本文档是唯一需求真相源；执行中如遇本文档与 MagicPanel 构建器硬校验冲突，以硬校验为准并在交付说明中记录差异。

## 一、背景与现状

- 生产：路由器 OpenClash 运行 MagicPanel-默认.yaml（MagicPanel build 300 产物），订阅名 `MagicPanel`，更新命令 `sh /usr/share/openclash/openclash.sh 'MagicPanel-默认'`。
- 现行生产配置可在路由器 `/etc/openclash/config/MagicPanel.yaml` 读取——这是了解 MagicPanel 规则/策略组格式的首要样本（先读它再动手）。
- 目标形态：本仓库 `cfg/ClashMainConfig.ini`（另一条订阅转换路径的模板，已在线上稳定运行）。其语法速查见 `custom/README.md`。
- MagicPanel 构建器硬校验：**尾块顺序固定为 cn → cn-ip → direct → private-ip → MATCH**，改序无法通过校验。模板中 private 在最前、cn 在尾部的排布若与该校验冲突，按 MagicPanel 的框架排布执行，不得强行对齐。

## 二、目标策略组（57 个）

### 节点池（url-test，16 个）

测速参数全部 `https://www.gstatic.com/generate_204`，300 秒间隔，50ms 容差：

| 组名 | 节点筛选正则 |
|---|---|
| ♻️ 自动选择 | `^(?!.*(路由\|[Ww]ire[Gg]uard\|[Mm]ieru\|[Jj]uicity\|[Tt]ailscale)).*`（排除隧道节点，防内网穿透入口混入全节点竞争） |
| 🇭🇰 香港自动 | `🇭🇰\|港\|hk\|Hong Kong\|HKG\|九龙\|Kowloon\|深港\|新界\|沙田\|荃湾\|葵涌` 等完整正则见模板 |
| 🇺🇸 美国自动 | 美/US/USA/城市名/机场码等完整正则见模板 |
| 🇯🇵 日本自动 | 日本/JP/JPN/城市名等完整正则见模板 |
| 🇸🇬 新加坡自动 | 新加坡/SG/SGP/狮城等 |
| 🇼🇸 台湾自动 / 🇰🇷 韩国自动 / 🇨🇦 加拿大自动 / 🇬🇧 英国自动 / 🇩🇪 德国自动 / 🇹🇷 土耳其自动 | 各地区完整正则见模板 |
| 🌐 其他地区自动 | 负向前瞻排除：全部地区关键字 + 家宽/家庭宽带/住宅/Residential + 路由 + WireGuard/Mieru/Juicity/Tailscale |
| 🏠 家宽自动 | `家宽\|家庭宽带\|住宅\|Residential` |
| 🇯🇵 日本自建测速 / 🇺🇸 美国自建测速 / 🇸🇬 新加坡自建测速 | 双前瞻且关系：须同时含地区词（日本/JP/JPN、美国/US/USA、新加坡/SG/SGP，字母码前后不得邻接字母）与"自建" |

### 业务组（fallback 28 + select 13，共 41 个）

`→` 表示候选顺序；fallback 取首个测速存活项，select 默认选中第一项。**"无直连"组**（Telegram 除外是直连优先）不得在尾部补直连。

| 组名 | 类型 | 候选链 |
|---|---|---|
| 🚀 故障转移 | fallback | 🇸🇬新加坡自建测速 → 🇺🇸美国自建测速 → 🇯🇵日本自建测速 → 🇭🇰香港自动 → 🇺🇸美国自动 → 🇯🇵日本自动 → 🇸🇬新加坡自动 → 🇼🇸台湾自动 → 🇰🇷韩国自动 → 🇨🇦加拿大自动 → 🇬🇧英国自动 → 🇩🇪德国自动 → 🇹🇷土耳其自动 → 🌐其他地区自动 → 🏠家宽自动 → ♻️自动选择 |
| 📨 Telegram | fallback | **🎯全球直连** → 香港 → 美国 → 日本 → 新加坡 → 台湾 → 韩国 → 加拿大 → 英国 → 德国 → 土耳其 → 其他地区 → 家宽 → 自动选择 |
| 🎧 Discord / 📞 Talkatone / 💬 即时通讯 / 🌐 社交媒体 / 🌎 国外媒体 / 📰 新闻资讯 / 🛒 国外电商 / 🪙 加密货币 / 🐟 漏网之鱼 | fallback | 香港自动 → 美国自动 → 日本自动 → 新加坡自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择（无直连） |
| 📹 Zoom | fallback | 香港开头同上，**末位追加 🎯全球直连** |
| 🚀 GitHub / 📦 容器服务 | fallback | 🇸🇬新加坡自建测速 → 🇯🇵日本自建测速 → 🇺🇸美国自建测速 → 🇸🇬新加坡自动 → 🇯🇵日本自动 → 🇺🇸美国自动 → 香港自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择 → **🎯全球直连** |
| 💻 开发者服务 | fallback | 🇺🇸美国自建测速 → 🇯🇵日本自建测速 → 香港自动 → 美国自动 → 日本自动 → 新加坡自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择 → 🎯全球直连 |
| 📚 学术资源 | fallback | 香港开头标准链 + 末位 🎯全球直连 |
| 🤖 ChatGPT / 🤖 Copilot / 🤖 Claude / 🤖 Grok / 🤖 国外AI服务 | fallback | 🇺🇸美国自建测速 → **🏠家宽自动** → 🇯🇵日本自建测速 → 🇸🇬新加坡自动 → 🇯🇵日本自动 → 🇭🇰香港自动 → 🇺🇸美国自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 自动选择（无直连；家宽自动全链只出现一次） |
| 🎶 TikTok | fallback | 🇸🇬新加坡自建测速 → 🇯🇵日本自建测速 → 🇺🇸美国自建测速 → 🇸🇬新加坡自动 → 🇯🇵日本自动 → 🇺🇸美国自动 → 香港自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择 |
| 🇸🇬 新加坡媒体 | select | 🇸🇬新加坡自建测速 → 🇸🇬新加坡自动 |
| 🎥 AppleTV+ / 🎥 Emby / 🎻 Spotify | fallback | 🇸🇬新加坡自动 → 🇯🇵日本自动 → 香港自动 → 美国自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择 |
| 📺 Bahamut | fallback | 台湾自动 → 香港自动 → 🚀故障转移 → 🎯全球直连 |
| 🇬 谷歌服务 | fallback | 🇺🇸美国自建测速 → 🇺🇸美国自动 → 🇸🇬新加坡自建测速 → 🇯🇵日本自建测速 → 🇯🇵日本自动 → 🇸🇬新加坡自动 → 香港自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择 |
| 🍎 苹果服务 / Ⓜ️ 微软服务 / 💾 OneDrive / 🎮 游戏平台 / 🎮 Steam / 🚀 测速工具 | select | 🎯全球直连 → 香港自动 → 美国自动 → 日本自动 → 新加坡自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 → 自动选择 |
| 💳 PayPal | select | 🇺🇸美国自建测速 → 🇺🇸美国自动 → 🇼🇸台湾自动 → 🇯🇵日本自动 → 🇭🇰香港自动 → 🇬🇧英国自动 → 🎯全球直连 → ♻️自动选择 |
| 🌍 国外域名 | select | 🎯全球直连 → 🚀故障转移 → ♻️自动选择 → 香港自动 → 美国自动 → 日本自动 → 新加坡自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 |
| 🤖 国内AI服务 | select | 🎯全球直连 → 🚀故障转移 → ♻️自动选择 → 香港自动 → 美国自动 → 日本自动 → 新加坡自动 → 台湾自动 → 韩国自动 → 加拿大自动 → 英国自动 → 德国自动 → 土耳其自动 → 其他地区自动 → 家宽自动 |
| 🔀 非标端口 | select | 🎯全球直连 → 🐟漏网之鱼（**直连必须是默认**，BT/PT 流量依赖它） |
| 🚇 WireGuard | select | 🎯全球直连 + 关键字筛选拥有节点：`路由\|WireGuard\|Mieru\|Juicity\|Tailscale`（内网穿透/自组网节点收容组） |
| 🎯 全球直连 | select | DIRECT |

## 三、目标分流规则（61 条，顺序即优先级）

```
 1 GEOSITE,private                          → 🎯 全球直连
 2 GEOIP,private,no-resolve                 → 🎯 全球直连
 3 RULE-SET Custom_Direct_Domain(1800)      → 🎯 全球直连
 4 RULE-SET Custom_Direct_Classical_IP      → 🎯 全球直连
 5 RULE-SET Custom_Proxy_Domain             → 🚀 故障转移
 6 RULE-SET Custom_Proxy_Classical_IP       → 🚀 故障转移
 7 GEOSITE,category-games@cn                → 🎯 全球直连
 8 RULE-SET Steam_CDN_Classical             → 🎯 全球直连
 9 GEOSITE,category-game-platforms-download → 🎯 全球直连
10 GEOSITE,category-public-tracker          → 🎯 全球直连
11 GEOSITE,zoom                             → 📹 Zoom
12 GEOSITE,talkatone                        → 📞 Talkatone
13 GEOSITE,telegram                         → 📨 Telegram
14 GEOSITE,discord                          → 🎧 Discord
15 GEOSITE,category-communication           → 💬 即时通讯
16 GEOSITE,xai                              → 🤖 Grok
17 GEOSITE,category-social-media-!cn        → 🌐 社交媒体
18 GEOSITE,openai                           → 🤖 ChatGPT
19 GEOSITE,onedrive                         → 💾 OneDrive
20 GEOSITE,bing                             → 🤖 Copilot
21 GEOSITE,anthropic                        → 🤖 Claude
22 GEOSITE,google                           → 🇬 谷歌服务   ⚠️ 必须位于 category-ai-!cn 之前
23 GEOSITE,category-ai-!cn                  → 🤖 国外AI服务
24 GEOSITE,category-ai-cn                   → 🤖 国内AI服务
25 GEOSITE,docker                           → 📦 容器服务
26 GEOSITE,category-container               → 📦 容器服务
27 GEOSITE,github                           → 🚀 GitHub
28 GEOSITE,category-dev                     → 💻 开发者服务
29 GEOSITE,category-scholar-!cn             → 📚 学术资源
30 GEOSITE,category-speedtest               → 🚀 测速工具
31 GEOSITE,steam                            → 🎮 Steam
32 GEOSITE,apple-tvplus                     → 🎥 AppleTV+   ⚠️ 必须位于 apple 之前
33 GEOSITE,apple                            → 🍎 苹果服务
34 GEOSITE,microsoft                        → Ⓜ️ 微软服务
35 GEOSITE,tiktok                           → 🎶 TikTok
36 GEOSITE,netflix                          → 🇸🇬 新加坡媒体
37 GEOSITE,disney                           → 🇸🇬 新加坡媒体
38 GEOSITE,hbo                              → 🇸🇬 新加坡媒体
39 GEOSITE,primevideo                       → 🇸🇬 新加坡媒体
40 GEOSITE,dazn                             → 🇸🇬 新加坡媒体
41 GEOSITE,viu                              → 🇸🇬 新加坡媒体
42 GEOSITE,category-emby                    → 🎥 Emby
43 GEOSITE,spotify                          → 🎻 Spotify
44 GEOSITE,bahamut                          → 📺 Bahamut
45 GEOSITE,category-games                   → 🎮 游戏平台
46 GEOSITE,category-media                   → 📰 新闻资讯
47 GEOSITE,category-entertainment           → 🌎 国外媒体
48 RULE-SET pt-domains                      → ⏬ PT站点
49 GEOSITE,paypal                           → 💳 PayPal
50 GEOSITE,category-ecommerce               → 🛒 国外电商
51 GEOSITE,category-cryptocurrency          → 🪙 加密货币
52 GEOSITE,gfw                              → 🚀 故障转移
53 GEOIP,telegram,no-resolve                → 📨 Telegram
54 GEOIP,twitter,no-resolve                 → 🌐 社交媒体
55 GEOIP,facebook,no-resolve                → 🌐 社交媒体
56 GEOIP,google,no-resolve                  → 🇬 谷歌服务
57 GEOSITE,geolocation-!cn                  → 🌍 国外域名
58 GEOSITE,cn                               → 🎯 全球直连（MagicPanel 尾块 cn 位）
59 GEOIP,cn,no-resolve                      → 🎯 全球直连（MagicPanel 尾块 cn-ip 位）
60 Custom_Port_Direct 规则                  → 🔀 非标端口（MagicPanel 尾块 direct 位语义）
61 MATCH                                    → 🐟 漏网之鱼
```

规则源：前 7 个 RULE-SET 用上游 `cdn.jsdelivr.net/gh/Aethersailor/Custom_OpenClash_Rules@main/rule/`（用户明确选择跟随上游维护）；pt-domains 用 `raw.githubusercontent.com/FUJIWARESHINE/pt-domains/refs/heads/main/pt-domains.mrs`。MagicPanel 若有自己的规则源机制，等价替换即可，语义不变。

## 四、关键设计决策（改动的理由，勿"顺手改回"）

1. Telegram 直连优先：用户使用 TG 内建代理，直连是明确选择。
2. 谷歌全家桶统一：Search/Gmail/YouTube/Gemini/FCM/Android/Firebase 等全部归 🇬 谷歌服务（geosite google 含 18 个子类别），统一出口降低谷歌风控；google 规则必须排在 category-ai-!cn 之前，防止 Gemini/DeepMind 被 AI 组截走。
3. 新加坡媒体组：Netflix/Disney+/HBO Max/Prime Video/DAZN/Viu 六服务合并，select 双候选，默认新加坡自建（流媒体自建盒）。
4. AI 组链：美国自建 → 家宽自动（住宅 IP 风控加固）→ 日本自建 → …；家宽自动在链中只能出现一次。
5. 主链故障转移 SG→US→JP 自建打头（自建带宽充足，SG 延迟 129ms 实测最优；JP 37ms 是移动中转入口的表象，用户走电信）。
6. PT/非标端口直连优先：BT 流量不得进机场。
7. TikTok 香港不可用，链以 SG 自建打头。
8. 隧道节点（路由/WireGuard/Mieru/Juicity/Tailscale）收容进 🚇 WireGuard 组，其他地区与自动选择均排除它们。
9. MagicPanel 特有能力保留：游戏日本 UDP 候选池机制（模板的 游戏平台 直连默认可与之共存或由其替代——保留现有游戏池实现，直连作为可选项）；Google 严格资格检测/自动跨区**不要**尝试实现（明确不在范围）。

## 五、硬性边界

- 不改 OpenClashConfig 仓库与 `cfg/ClashMainConfig.ini`（只读真相源）。
- 不动路由器 cron、`restore-stable-core.sh`（内核哈希锁）、dropbear、防火墙、网络配置。
- 改 MagicPanel 前先备份当前 MagicPanel-默认 配置（NAS `/opt/magicpanel/data/router-maintenance/` 目录惯例，带日期）。
- 构建必须通过 MagicPanel 硬校验才能发布；发布即影响全屋网络，发布前口头向用户确认一次。
- NAS `*/5 watchdog` 与 tunnel-health.timer 保留不动。

## 六、验收清单

1. 构建通过硬校验，产物规则/组语义与本文档清单一致（框架性差异记录即可）。
2. `sh /usr/share/openclash/openclash.sh 'MagicPanel-默认'` 更新生效后，API 校验：
   ```
   SECRET=$(uci -q get openclash.config.dashboard_password)
   curl -s -H "Authorization: Bearer $SECRET" http://127.0.0.1:9090/proxies
   ```
   核对：组总数、🇬 谷歌服务/🇸🇬 新加坡媒体/🚇 WireGuard 存在、AI 组链序（美国自建测速→家宽自动→日本自建测速）。
3. 分流抽查（结合 dashboard 连接页）：google.com 与 youtube.com → 🇬 谷歌服务；netflix.com → 🇸🇬 新加坡媒体；telegram → 📨 Telegram（直连）；github.com → 🚀 GitHub；国内域名（如 qq.com）→ 直连；BT 客户端非 80/443 端口连接 → 🔀 非标端口（直连）。
4. Telegram 手机端收发正常（走内建代理，不受影响）。
5. 交付物：变更清单 + 验收证据（组数/抽查截图或 API 输出）+ 回退方式（备份文件路径）。
