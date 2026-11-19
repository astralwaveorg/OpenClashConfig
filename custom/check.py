#!/usr/bin/env python3
"""ClashMainConfig.ini 深度检查工具。

用法：
    python3 -I custom/check.py            # 检查 cfg/ClashMainConfig.ini
    python3 -I custom/check.py <file>     # 检查指定文件

每次修改 cfg/ClashMainConfig.ini 后必须运行，全部通过才能提交。
退出码：0 = 通过；1 = 存在错误。

检查范围（对应 subconverter 兼容模板语法）：
  A. 文件编码：UTF-8 无 BOM、LF 行尾、无粘连行、语句格式合法
  B. ruleset 行：目标组存在、来源格式（[] 内联 / [type:]URL[,interval]）、
     []FINAL 唯一且居末、总数 ≤ 64、无重复行
  C. custom_proxy_group 行：组名唯一、类型合法、[] 引用存在、
     测试 URL 与 interval[,timeout][,tolerance] 参数格式、成员正则可编译、
     空字段、组间循环引用
  D. 尾部开关：enable_rule_generator / overwrite_original_rules 保持 true
"""

import re
import sys
from pathlib import Path

MAX_RULESETS = 64
GROUP_TYPES = {"select", "url-test", "fallback", "load-balance"}
REMOTE_TYPES = {"", "surge", "quanx", "clash-domain", "clash-ipcidr", "clash-classic"}
BUILTIN_TARGETS = {"DIRECT", "REJECT", "GLOBAL", "PASS"}
# [] 内联规则：类型 -> (最小参数数, 最大参数数)
INLINE_RULE_TYPES = {
    "GEOSITE": (1, 1),
    "GEOIP": (1, 2),
    "FINAL": (0, 0),
    "MATCH": (0, 0),
    # 通用 clash 规则类型，宽松校验（参数数 ≥1）
    "DOMAIN": (1, 99), "DOMAIN-SUFFIX": (1, 99), "DOMAIN-KEYWORD": (1, 99),
    "IP-CIDR": (1, 99), "IP-CIDR6": (1, 99), "SRC-IP-CIDR": (1, 99),
    "SRC-PORT": (1, 99), "DST-PORT": (1, 99), "PROCESS-NAME": (1, 99),
}
TAIL_KEYS = {"enable_rule_generator": "true", "overwrite_original_rules": "true"}
URL_RE = re.compile(r"^https?://\S+$")
NUM_RE = re.compile(r"^(\d+)(,\d*){0,2}$")


class Checker:
    def __init__(self, path: Path):
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.group_names: list[str] = []
        self.group_map: dict[str, list[str]] = {}  # 组名 -> 该组成员字段列表
        self.rulesets: list[tuple[int, str, str]] = []  # (行号, 目标组, 来源)
        self._fail = self.errors.append
        self._warn = self.warnings.append

    # ---------- A. 文件与结构 ----------
    def load(self) -> list[str] | None:
        try:
            raw = self.path.read_bytes()
        except OSError as e:
            self._fail(f"无法读取文件：{e}")
            return None
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as e:
            self._fail(f"文件不是合法 UTF-8：{e}")
            return None
        if text.startswith("\ufeff"):
            self._fail("文件带 UTF-8 BOM，订阅转换后端可能解析异常")
        if "\r" in text:
            self._fail("文件含 CR（CRLF 行尾），必须保持 LF")
        if not text.endswith("\n"):
            self._warn("文件末尾缺少换行符")
        return text.split("\n")

    def structure(self, lines: list[str]) -> list[tuple[int, str]]:
        """返回合法语句行列表 [(行号, 内容)]，并做结构检查。"""
        seen_custom = False
        statements: list[tuple[int, str]] = []
        tail_seen = False
        for no, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped != line.rstrip():
                self._warn(f"第 {no} 行有行尾空白")
            if not stripped or stripped.startswith(";"):
                continue
            if stripped == "[custom]":
                if seen_custom:
                    self._fail(f"第 {no} 行：[custom] 段重复")
                seen_custom = True
                continue
            is_rs = stripped.startswith("ruleset=")
            is_cg = stripped.startswith("custom_proxy_group=")
            if not is_rs and not is_cg:
                known_tail = stripped.split("=", 1)[0].strip() in TAIL_KEYS
                if seen_custom and known_tail:
                    tail_seen = True
                    key, _, val = stripped.partition("=")
                    if val.strip() != TAIL_KEYS[key]:
                        self._fail(f"第 {no} 行：尾部开关 {key} 必须保持 {TAIL_KEYS[key]}，当前为 {val.strip()}")
                    continue
                self._fail(f"第 {no} 行：无法识别的语句（必须以 ruleset= / custom_proxy_group= 开头）：{stripped[:60]}")
                continue
            if not seen_custom:
                self._fail(f"第 {no} 行：语句出现在 [custom] 段之前")
            if tail_seen:
                self._fail(f"第 {no} 行：语句出现在尾部开关之后")
            # 粘连检查：一行内同类前缀只能出现一次
            for prefix in ("ruleset=", "custom_proxy_group="):
                cnt = stripped.count(prefix)
                if cnt > 1:
                    self._fail(f"第 {no} 行：{prefix} 出现 {cnt} 次，疑似粘连行（历史事故模式）")
            if is_cg and "ruleset=" in stripped:
                self._fail(f"第 {no} 行：分组行中混入 ruleset=，疑似粘连行")
            if is_rs and "custom_proxy_group=" in stripped:
                self._fail(f"第 {no} 行：规则行中混入 custom_proxy_group=，疑似粘连行")
            statements.append((no, stripped))
        if not seen_custom:
            self._fail("缺少 [custom] 段")
        return statements

    # ---------- B. ruleset ----------
    def check_rulesets(self, statements: list[tuple[int, str]]) -> None:
        rs_lines = [(no, s) for no, s in statements if s.startswith("ruleset=")]
        seen_lines: set[str] = set()
        for no, s in rs_lines:
            if s in seen_lines:
                self._fail(f"第 {no} 行：ruleset 与前面某条完全重复：{s[:70]}")
            seen_lines.add(s)
            body = s[len("ruleset="):]
            parts = body.split(",")
            if len(parts) < 2:
                self._fail(f"第 {no} 行：ruleset 字段不足（组名,来源[,间隔]）：{s[:70]}")
                continue
            # 精确拆分：来源可能含逗号（如 []GEOIP,cn,no-resolve），末段若是纯数字才视为更新间隔
            group, source, interval = self._parse_ruleset(body, no)
            self.rulesets.append((no, group, source))
            if group not in self.group_map and group not in BUILTIN_TARGETS:
                self._fail(f"第 {no} 行：ruleset 目标组「{group}」未在 custom_proxy_group 中定义")
            self._check_source(no, source, interval)
        n = len(self.rulesets)
        if n > MAX_RULESETS:
            self._fail(f"ruleset 共 {n} 条，超过后端兼容上限 {MAX_RULESETS}")
        finals = [(no, src) for no, _, src in self.rulesets if src in ("[]FINAL", "[]MATCH")]
        if len(finals) > 1:
            self._fail(f"[]FINAL/[]MATCH 出现 {len(finals)} 次，只允许一条：行 {finals}")
        if finals and self.rulesets and finals[0][0] != self.rulesets[-1][0]:
            self._fail(f"[]FINAL（第 {finals[0][0]} 行）必须是最后一条 ruleset")
        if not finals and n:
            self._fail("缺少 []FINAL 兜底规则")
        print(f"  ruleset 共 {n} 条（上限 {MAX_RULESETS}，剩余 {MAX_RULESETS - n} 个空位）")

    @staticmethod
    def _looks_like_interval(s: str) -> bool:
        return bool(re.fullmatch(r"\d+", s.strip()))

    def _parse_ruleset(self, body: str, no: int) -> tuple[str, str, str]:
        interval = ""
        parts = body.split(",")
        if len(parts) >= 3 and self._looks_like_interval(parts[-1]):
            interval = parts[-1]
            parts = parts[:-1]
        group = parts[0]
        source = ",".join(parts[1:])
        if not interval and not source.startswith("[]"):
            self._warn(f"第 {no} 行：远程规则未设置更新间隔（建议 1800/28800）")
        return group, source, interval

    def _check_source(self, no: int, source: str, interval: str) -> None:
        if source.startswith("[]"):
            inner = source[2:]
            segs = inner.split(",") if inner else []
            rtype = segs[0] if segs else ""
            args = segs[1:]
            if rtype in INLINE_RULE_TYPES:
                lo, hi = INLINE_RULE_TYPES[rtype]
                if not (lo <= len(args) <= hi):
                    self._fail(f"第 {no} 行：[]{rtype} 参数数应为 {lo}-{hi}，实际 {len(args)}：{source}")
                elif rtype == "GEOIP" and len(args) == 2 and args[1] != "no-resolve":
                    self._fail(f"第 {no} 行：[]GEOIP 第二参数只允许 no-resolve：{source}")
            else:
                self._fail(f"第 {no} 行：未知的 [] 内联规则类型「{rtype}」：{source}")
            return
        # 远程来源：[type:]URL
        rtype = ""
        url = source
        if ":" in source and not source.startswith("http"):
            maybe, rest = source.split(":", 1)
            if maybe.lower() in REMOTE_TYPES:
                rtype, url = maybe.lower(), rest
        if not URL_RE.match(url):
            self._fail(f"第 {no} 行：远程规则地址非法（须 http(s)://）：{source[:80]}")
            return
        if rtype not in REMOTE_TYPES:
            self._fail(f"第 {no} 行：未知的规则类型前缀「{rtype}:」：{source[:80]}")
        if interval and not self._looks_like_interval(interval):
            self._fail(f"第 {no} 行：规则更新间隔须为正整数秒，实际「{interval}」")
        # 格式匹配提示（仅警告，避免误伤）
        low = url.lower()
        if rtype == "clash-domain" and not (low.endswith(".mrs") or low.endswith(".yaml")):
            self._warn(f"第 {no} 行：clash-domain: 建议指向 .mrs/.yaml 域名集：{url[:70]}")
        if rtype == "clash-classic" and not (low.endswith(".yaml") or low.endswith(".mrs") or low.endswith(".list")):
            self._warn(f"第 {no} 行：clash-classic: 建议指向 classic payload 的 .yaml：{url[:70]}")

    # ---------- C. custom_proxy_group ----------
    def check_groups(self, statements: list[tuple[int, str]]) -> None:
        cg_lines = [(no, s) for no, s in statements if s.startswith("custom_proxy_group=")]
        processed: set[str] = set()
        for no, s in cg_lines:
            fields = s[len("custom_proxy_group="):].split("`")
            for i, f in enumerate(fields):
                if f == "" or f.strip() == "":
                    self._fail(f"第 {no} 行：第 {i + 1} 个字段为空（连续反引号或行尾反引号）")
            if len(fields) < 3:
                self._fail(f"第 {no} 行：分组字段不足（名称`类型`成员...）：{s[:70]}")
                continue
            name, gtype = fields[0], fields[1]
            if name in processed:
                self._fail(f"第 {no} 行：分组「{name}」重复定义")
                continue
            processed.add(name)
            if gtype not in GROUP_TYPES:
                self._fail(f"第 {no} 行：分组「{name}」类型非法「{gtype}」（仅支持 {'/'.join(sorted(GROUP_TYPES))}）")
                continue
            members = fields[2:]
            # 拆出测试 URL 与数字参数
            url_idx = next((i for i, m in enumerate(members) if URL_RE.match(m)), None)
            if url_idx is not None:
                rest = members[url_idx + 1:]
                if gtype in ("url-test", "fallback", "load-balance"):
                    if not rest:
                        self._fail(f"第 {no} 行：分组「{name}」缺少测速间隔参数")
                    elif not NUM_RE.match(rest[0]):
                        self._fail(f"第 {no} 行：分组「{name}」测速参数格式非法（应为 interval[,timeout][,tolerance]）：{rest[0]!r}")
                    elif rest[1:]:
                        self._fail(f"第 {no} 行：分组「{name}」测速参数后有多余字段：{rest[1:]}")
                elif rest:
                    self._fail(f"第 {no} 行：分组「{name}」（select）URL 后出现多余字段：{rest}")
                members = members[:url_idx]
            elif gtype in ("url-test", "fallback", "load-balance"):
                self._fail(f"第 {no} 行：分组「{name}」（{gtype}）缺少测试 URL")
            # 成员校验：[] 引用 / 正则
            for m in members:
                if m.startswith("[]"):
                    ref = m[2:]
                    if ref not in self.group_map and ref not in BUILTIN_TARGETS:
                        self._fail(f"第 {no} 行：分组「{name}」引用了未定义的组「{ref}」")
                elif m.startswith("!!") or m.startswith("script:") or m == "ssid":
                    self._fail(f"第 {no} 行：分组「{name}」使用了本模板未用过的成员语法「{m[:40]}」，请人工确认后更新检查器")
                else:
                    try:
                        re.compile(m)
                    except re.error as e:
                        self._fail(f"第 {no} 行：分组「{name}」成员正则无法编译：{e}（成员：{m[:60]}）")
            self.group_names.append(name)
            self.group_map[name] = fields[2:]
        counts: dict[str, int] = {}
        for _, s in cg_lines:
            t = s.split("`")[1] if "`" in s else "?"
            counts[t] = counts.get(t, 0) + 1
        stat = "，".join(f"{k} {v}" for k, v in sorted(counts.items()))
        print(f"  分组共 {len(self.group_map)} 个（{stat}）")

    def check_cycles(self) -> None:
        color: dict[str, int] = {g: 0 for g in self.group_map}

        def dfs(g: str, stack: list[str]) -> None:
            color[g] = 1
            stack.append(g)
            for m in self.group_map.get(g, []):
                if not m.startswith("[]"):
                    continue
                ref = m[2:]
                if ref not in color:
                    continue
                if color[ref] == 1:
                    self._fail(f"检测到分组循环引用：{' -> '.join(stack + [ref])}")
                elif color[ref] == 0:
                    dfs(ref, stack)
            stack.pop()
            color[g] = 2

        for g in self.group_map:
            if color[g] == 0:
                dfs(g, [])

    # ---------- 汇总 ----------
    def run(self) -> int:
        lines = self.load()
        if lines is None:
            self.report()
            return 1
        statements = self.structure(lines)
        # 先收集分组（ruleset 目标组校验依赖组定义）
        for no, s in statements:
            if s.startswith("custom_proxy_group="):
                name = s[len("custom_proxy_group="):].split("`")[0]
                if name and name not in self.group_map:
                    self.group_map[name] = []  # 占位，check_groups 中重填并校验
        self.check_rulesets(statements)
        self.check_groups(statements)
        self.check_cycles()
        self.report()
        return 1 if self.errors else 0

    def report(self) -> None:
        for w in self.warnings:
            print(f"  [警告] {w}")
        if self.errors:
            for e in self.errors:
                print(f"  [错误] {e}")
            print(f"检查未通过：{len(self.errors)} 个错误，{len(self.warnings)} 个警告")
        else:
            print("检查通过 ✓")


def main() -> int:
    default = Path(__file__).resolve().parent.parent / "cfg" / "ClashMainConfig.ini"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    print(f"深度检查：{path}")
    if not path.is_file():
        print(f"  [错误] 文件不存在：{path}")
        return 1
    return Checker(path).run()


if __name__ == "__main__":
    sys.exit(main())
