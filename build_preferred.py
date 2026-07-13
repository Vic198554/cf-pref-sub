#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_preferred.py - 合并多个公开 CF 优选 IP 源，生成去重的 preferred_ips.txt
用于 edgetunnel / CloudflareST 的『优选订阅地址』栏。

运行: python build_preferred.py
依赖: 仅需标准库 + 网络(走代理)。无需第三方包。

可通过环境变量 SOURCES 覆盖源列表(JSON数组)，或代理环境变量 HTTPS_PROXY。
"""
import os
import re
import sys
import urllib.request

# ---- 优选源 (每行 IP:PORT#地区[备注]，或纯 IP:PORT) ----
DEFAULT_SOURCES = [
    "https://cf.junzhen.qzz.io/best_ips.txt",
    "https://cf.junzhen.qzz.io/full_ips.txt",
    "https://raw.githubusercontent.com/cmliu/WorkerVless2sub/main/addressesapi.txt",
    "https://raw.githubusercontent.com/KafeMars/best-ips-domains/main/cf-bestips.txt",
    "https://raw.githubusercontent.com/HandsomeMJZ/cfip/main/best_ips.txt",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def norm_ipkey(line):
    m = re.match(r"([\d.]+):(\d+)", line)
    return f"{m.group(1)}:{m.group(2)}" if m else None

def main():
    sources = DEFAULT_SOURCES
    if os.environ.get("SOURCES"):
        try:
            import json
            sources = json.loads(os.environ["SOURCES"])
        except Exception:
            pass

    # 离线优先: 直接用本地已下载的源文件，不碰网络（避免代理抖动丢数据）
    local_files = ["src_best.txt", "src_full.txt", "src_cmliu.txt", "src_kafe.txt", "src_handsome.txt"]
    local_sources = [f for f in local_files if os.path.exists(f)]
    if local_sources:
        print(f"[离线模式] 使用本地源: {local_sources}", file=sys.stderr)
        sources = local_sources
        priority = {f: i for i, f in enumerate(local_sources)}
    else:
        priority = {url: i for i, url in enumerate(sources)}

    seen = set()
    ordered = []  # (prio, seq, unified_text)
    seq = 0
    total_raw = 0

    for src in sources:
        try:
            if src.startswith("http"):
                text = fetch(src)
            else:
                text = open(src, encoding="utf-8", errors="replace").read()
        except Exception as e:
            print(f"[跳过] {src} 读取失败: {e}", file=sys.stderr)
            continue
        lines = text.splitlines()
        total_raw += len(lines)
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            ipkey = norm_ipkey(line)
            if not ipkey:
                continue
            rest = line[len(ipkey):]
            if "#" not in rest:
                rest = "#MIX" + rest
            unified = ipkey + rest
            if ipkey in seen:
                continue
            seen.add(ipkey)
            seq += 1
            ordered.append((priority.get(src, 99), seq, unified))

    ordered.sort(key=lambda x: (x[0], x[1]))
    out = [x[2] for x in ordered]

    header = [
        f"# CF 优选 IP 合并清单 | 共 {len(out)} 条 | 由 {len(sources)} 个公开源合并去重",
        "# 来源: " + " + ".join(sources),
        "# 带速度标注的最优选在前。可直接填进 edgetunnel『优选订阅地址』",
        "",
    ]
    with open("preferred_ips.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(header) + "\n".join(out) + "\n")

    print(f"生成 preferred_ips.txt: 合并 {total_raw} 行 -> 去重 {len(out)} 条")

if __name__ == "__main__":
    main()
