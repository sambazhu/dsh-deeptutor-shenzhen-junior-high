#!/usr/bin/env python3
"""将学习台账中的错题库与七年级全科教材资料单向（只读）导出并同步至 DeepTutor 知识库。

遵循原则：
1. 台账是唯一事实源（Single Source of Truth），本脚本对台账错题库完全只读。
2. 知识库列表：
   - qiuyu-wrongbook     ：汇总各学科 `错题集/题库.json` 中的错题、错因、解析与变式
   - sz-g7-chinese-tb    ：统编版七年级上册语文（含官方目录页码与逐页全文）
   - sz-g7-math-bsd      ：北师大版七年级上册数学（章节核心考点大纲 + 官方目录页码表 + MinerU 云端解析全文）
   - sz-g7-english-hj    ：沪教牛津版七年级上册英语（含官方目录页码与逐页全文）
   - sz-g7-geography-xj  ：湘教版七年级上册地理（含官方目录页码与逐页全文）
   - sz-g7-history-tb    ：统编版七年级上册中国历史（含官方目录页码与逐页全文）
   - sz-g7-biology-rj    ：人教版七年级上册生物学（含官方目录页码与逐页全文）
   - sz-g7-morality-tb   ：统编版七年级上册道德与法治（含官方目录页码与逐页全文）
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

LEDGER_ROOT = Path(__file__).resolve().parents[1]
RAW_TEXTBOOK_ROOT = Path(os.environ.get("RAW_TEXTBOOK_ROOT", Path.home() / "dshworkplace/初中"))
DEEPTUTOR_HOME = Path(os.environ.get("DEEPTUTOR_HOME", Path.home() / ".deeptutor")).expanduser()
DEEPTUTOR_BIN = Path(os.environ.get("DEEPTUTOR_LOCAL_BIN", Path.home() / ".local/bin/deeptutor")).expanduser()
EXPORT_ROOT = DEEPTUTOR_HOME / "data" / "ledger_export"
DOC_PARSING_JSON = DEEPTUTOR_HOME / "data" / "user" / "settings" / "document_parsing.json"

SUBJECT_FOLDERS = {
    "语文": "01_语文",
    "数学": "02_数学",
    "英语": "03_英语",
    "地理": "04_地理",
    "历史": "05_历史",
    "生物": "06_生物",
    "道法": "07_道法",
}

G7_VOL1_TEXTBOOKS: list[dict[str, Any]] = [
    {
        "subject": "语文",
        "dir": "01_语文",
        "edition": "统编版",
        "kb": "sz-g7-chinese-tb",
        "src_rel": "语文/统编版/（根据2022年版课程标准修订）义务教育教科书·语文七年级上册.pdf",
        "dst_pdf": "义务教育教科书·语文七年级上册（统编版）.pdf",
        "is_scanned": False,
    },
    {
        "subject": "数学",
        "dir": "02_数学",
        "edition": "北师大版",
        "kb": "sz-g7-math-bsd",
        "src_rel": "数学/北师大版/（根据2022年版课程标准修订）义务教育教科书•数学七年级上册.pdf",
        "dst_pdf": "义务教育教科书·数学七年级上册（北师大版）.pdf",
        "is_scanned": True,
    },
    {
        "subject": "英语",
        "dir": "03_英语",
        "edition": "沪教牛津版（上海教育出版社）",
        "kb": "sz-g7-english-hj",
        "src_rel": "英语/沪教版/[沪教版] （根据2022年版课程标准修订）义务教育教科书 英语 七年级 上册.pdf",
        "dst_pdf": "义务教育教科书·英语七年级上册（沪教版）.pdf",
        "is_scanned": False,
    },
    {
        "subject": "地理",
        "dir": "04_地理",
        "edition": "湘教版",
        "kb": "sz-g7-geography-xj",
        "src_rel": "地理/湘教版/（根据2022年版课程标准修订）义务教育教科书•地理七年级上册.pdf",
        "dst_pdf": "义务教育教科书·地理七年级上册（湘教版）.pdf",
        "is_scanned": False,
    },
    {
        "subject": "历史",
        "dir": "05_历史",
        "edition": "统编版",
        "kb": "sz-g7-history-tb",
        "src_rel": "历史/统编版/（根据2022年版课程标准修订）义务教育教科书·中国历史七年级上册.pdf",
        "dst_pdf": "义务教育教科书·中国历史七年级上册（统编版）.pdf",
        "is_scanned": False,
    },
    {
        "subject": "生物",
        "dir": "06_生物",
        "edition": "人教版",
        "kb": "sz-g7-biology-rj",
        "src_rel": "生物学/人教版/（根据2022年版课程标准修订）义务教育教科书·生物学七年级上册.pdf",
        "dst_pdf": "义务教育教科书·生物学七年级上册（人教版）.pdf",
        "is_scanned": False,
    },
    {
        "subject": "道法",
        "dir": "07_道法",
        "edition": "统编版",
        "kb": "sz-g7-morality-tb",
        "src_rel": "道德与法治/统编版/（根据2022年版课程标准修订）义务教育教科书·道德与法治七年级上册.pdf",
        "dst_pdf": "义务教育教科书·道德与法治七年级上册（统编版）.pdf",
        "is_scanned": False,
    },
]


def run_dt_kb(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DEEPTUTOR_HOME"] = str(DEEPTUTOR_HOME)
    cmd = [str(DEEPTUTOR_BIN), "kb", *args]
    return subprocess.run(cmd, env=env, text=True, capture_output=True)


def kb_exists(name: str) -> bool:
    kb_dir = DEEPTUTOR_HOME / "data" / "knowledge_bases" / name
    return kb_dir.exists()


def rebuild_kb_from_dir(kb_name: str, docs_dir: Path) -> None:
    files = sorted(p for p in docs_dir.rglob("*") if p.is_file() and not p.name.startswith("."))
    if not files:
        print(f"[跳过] {kb_name}: 导出目录为空 ({docs_dir})")
        return

    if kb_exists(kb_name):
        run_dt_kb(["delete", kb_name, "--yes"])
        kb_dir = DEEPTUTOR_HOME / "data" / "knowledge_bases" / kb_name
        if kb_dir.exists():
            shutil.rmtree(kb_dir)

    print(f"[同步] 正在构建知识库 {kb_name}（共 {len(files)} 份文档）...")
    res = run_dt_kb(["create", kb_name, "--docs-dir", str(docs_dir)])
    if res.returncode != 0:
        print(f"[错误] 构建 {kb_name} 失败:\n{res.stdout}\n{res.stderr}")
        raise SystemExit(1)
    print(f"[完成] 知识库 {kb_name} 已就绪。")
    if kb_name == "sz-g7-math-bsd":
        run_dt_kb(["set-default", "sz-g7-math-bsd"])
    sync_kb_to_partners(kb_name)


def sync_kb_to_partners(kb_name: str) -> None:
    """将更新后的知识库同步至所有已挂载同名知识库的伴学伙伴（Partner）工作区。"""
    src_kb_dir = DEEPTUTOR_HOME / "data" / "knowledge_bases" / kb_name
    main_cfg_file = DEEPTUTOR_HOME / "data" / "knowledge_bases" / "kb_config.json"
    partners_root = DEEPTUTOR_HOME / "data" / "partners"
    if not src_kb_dir.exists() or not partners_root.exists():
        return
    main_entry = None
    if main_cfg_file.exists():
        try:
            main_cfg = json.loads(main_cfg_file.read_text(encoding="utf-8"))
            main_entry = (main_cfg.get("knowledge_bases") or {}).get(kb_name)
        except Exception:
            pass
    for p_dir in sorted(partners_root.glob("partner-*")):
        p_kb_root = p_dir / "workspace" / "knowledge_bases"
        p_kb_dir = p_kb_root / kb_name
        if not p_kb_dir.exists():
            continue
        shutil.rmtree(p_kb_dir)
        shutil.copytree(src_kb_dir, p_kb_dir)
        p_cfg_file = p_kb_root / "kb_config.json"
        if main_entry and p_cfg_file.exists():
            try:
                p_cfg = json.loads(p_cfg_file.read_text(encoding="utf-8"))
                p_cfg.setdefault("knowledge_bases", {})[kb_name] = main_entry
                p_cfg_file.write_text(json.dumps(p_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        print(f"[伴学伙伴同步] 已刷新 {p_dir.name} 的知识库副本: {kb_name}")


def ingest_g7_textbooks_from_raw() -> None:
    """从 /Users/sambazhu/dshworkplace/初中 整理七年级上册 7 科 PDF 到 00_教材与参考书/ 并提取章节页码 Markdown。"""
    import pymupdf

    tb_root = LEDGER_ROOT / "00_教材与参考书"
    for b in G7_VOL1_TEXTBOOKS:
        sub_dir = tb_root / b["dir"]
        sub_dir.mkdir(parents=True, exist_ok=True)
        src_file = RAW_TEXTBOOK_ROOT / b["src_rel"]
        dst_pdf = sub_dir / b["dst_pdf"]
        if src_file.exists() and (not dst_pdf.exists() or dst_pdf.stat().st_size != src_file.stat().st_size):
            shutil.copy2(src_file, dst_pdf)

        if not dst_pdf.exists():
            print(f"[警告] 未找到教材 PDF: {dst_pdf}")
            continue

        doc = pymupdf.open(dst_pdf)
        toc = doc.get_toc()
        page_heading: dict[int, str] = {}
        current_h1 = ""
        current_h2 = ""
        toc_sorted = sorted(toc, key=lambda x: x[2])
        toc_idx = 0
        for pno in range(1, len(doc) + 1):
            while toc_idx < len(toc_sorted) and toc_sorted[toc_idx][2] <= pno:
                lvl, title, _ = toc_sorted[toc_idx]
                if lvl == 1:
                    current_h1 = title.strip()
                    current_h2 = ""
                else:
                    current_h2 = title.strip()
                toc_idx += 1
            label = " / ".join(x for x in [current_h1, current_h2] if x)
            page_heading[pno] = label or "前言与目录"

        subj = b["subject"]
        ed = b["edition"]
        kb = b["kb"]
        dst_name = b["dst_pdf"]
        dir_name = b["dir"]

        toc_lines = [
            f"# {subj} 七年级上册（{ed} · 2024新课标修订版）",
            "",
            f"- 对应知识库：`{kb}`",
            f"- PDF 总页数：{len(doc)} 页",
            f"- 原件路径：`00_教材与参考书/{dir_name}/{dst_name}`",
            "",
            "## 官方目录与页码索引（PDF 页码）",
            "",
        ]
        for lvl, title, pg in toc:
            indent = "  " * max(0, lvl - 1)
            toc_lines.append(f"{indent}- **{title.strip()}**（PDF 第 {pg} 页）")

        if b["is_scanned"]:
            out_md = sub_dir / "北师大版七年级上册数学_官方目录与页码表.md"
            toc_lines.extend([
                "",
                "> 注：本册 PDF 正文为扫描图片版。配置 MinerU 云端 API Token 后运行 `tools/sync_to_deeptutor.py --mineru-math` 即可将全书 209 页公式与图表解析入库。",
            ])
            out_md.write_text("\n".join(toc_lines) + "\n", encoding="utf-8")
            print(f"[归档+目录] {dir_name} -> {out_md.name} (TOC={len(toc)})")
        else:
            out_md = sub_dir / f"{subj}_七年级上册_教材全文与章节页码.md"
            body_lines = list(toc_lines)
            body_lines.extend(["", "---", "", "## 教材逐页全文（含章节与页码定位）", ""])
            extracted_pages = 0
            for pno in range(1, len(doc) + 1):
                txt = doc[pno - 1].get_text("text").strip()
                if not txt:
                    continue
                extracted_pages += 1
                body_lines.append(f"### 【{subj}七上 · PDF第{pno}页 · {page_heading[pno]}】")
                body_lines.append(txt)
                body_lines.append("")
            out_md.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
            print(f"[归档+全文] {dir_name} -> {out_md.name} (有效文字页={extracted_pages}/{len(doc)})")


def export_wrongbook() -> Path:
    out_dir = EXPORT_ROOT / "qiuyu-wrongbook"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    summary_lines = [
        "# 朱秋宇七年级错题总览（台账只读同步）",
        "",
        "> 学校：深圳市石厦中学 · 七年级",
        "",
        "| 题号 ID | 学科 | 日期 | 知识点 | 来源 | 状态 |",
        "|---|---|---|---|---|---|",
    ]

    for subject, folder_name in SUBJECT_FOLDERS.items():
        bank_path = LEDGER_ROOT / folder_name / "错题集" / "题库.json"
        if not bank_path.exists():
            continue
        data = json.loads(bank_path.read_text(encoding="utf-8"))
        questions = data.get("questions") or []
        for q in questions:
            qid = q.get("id") or f"{subject}-{total + 1}"
            date = q.get("date") or ""
            source = q.get("source") or ""
            qtype = q.get("type") or ""
            topic = q.get("topic") or ""
            question_text = q.get("question") or ""
            answer = q.get("answer") or "❓待确认"
            explanation = q.get("explanation") or "❓待确认"
            mistake_reason = q.get("mistake_reason") or ""
            variant = q.get("variant") or ""
            variant_answer = q.get("variant_answer") or ""
            status = q.get("status") or "待复习"
            verified = q.get("verified") or ""
            explanation_source = q.get("explanation_source") or "ledger"

            summary_lines.append(
                f"| `{qid}` | {subject} | {date} | {topic} | {source} | {status} |"
            )

            md = [
                f"# 错题档案：{qid}（{subject} · {topic}）",
                "",
                f"- **学科**：{subject}",
                f"- **题号 ID**：`{qid}`",
                f"- **日期**：{date}",
                f"- **来源**：{source}",
                f"- **题型**：{qtype}",
                f"- **知识点（Topic）**：{topic}",
                f"- **掌握状态**：{status}",
                f"- **解析来源**：{explanation_source}",
                f"- **复核记录**：{verified if verified else '待复核'}",
                "",
                "## 一、题目正文",
                "",
                question_text,
                "",
                "## 二、参考答案",
                "",
                str(answer),
                "",
                "## 三、详细解析",
                "",
                str(explanation),
                "",
            ]
            if mistake_reason:
                md.extend([
                    "## 四、错因提醒与复盘重点",
                    "",
                    str(mistake_reason),
                    "",
                ])
            if variant:
                md.extend([
                    "## 五、同类变式练习",
                    "",
                    str(variant),
                    "",
                ])
                if variant_answer:
                    md.extend([
                        f"**变式参考答案**：{variant_answer}",
                        "",
                    ])

            safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in qid)
            (out_dir / f"{safe_id}.md").write_text("\n".join(md), encoding="utf-8")
            total += 1

    (out_dir / "00_错题总览.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"[导出] 已从台账导出 {total} 道错题至 {out_dir}")
    return out_dir


def export_subject_textbook_kb(book_cfg: dict[str, Any], grade_keywords: list[str] | None = None) -> Path:
    kb_name = book_cfg["kb"]
    out_dir = EXPORT_ROOT / kb_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tb_dir = LEDGER_ROOT / "00_教材与参考书" / book_cfg["dir"]
    keywords = grade_keywords or book_cfg.get("keywords") or ["七年级上册"]
    if tb_dir.exists():
        for p in sorted(tb_dir.iterdir()):
            # 仅将匹配当前年级的结构化 Markdown 放入向量索引目录
            if (
                p.is_file()
                and p.suffix.lower() == ".md"
                and p.name != "README.md"
                and not p.name.startswith(".")
                and any(kw in p.name for kw in keywords)
            ):
                shutil.copy2(p, out_dir / p.name)

    return out_dir


def configure_mineru_cloud(token: str | None = None) -> dict[str, Any]:
    """配置 DeepTutor 的 document_parsing.json 为 MinerU Cloud v4 模式（开启公式、表格与全页 OCR）。"""
    os.environ["DEEPTUTOR_HOME"] = str(DEEPTUTOR_HOME)
    from deeptutor.services.config.runtime_settings import get_runtime_settings_service

    svc = get_runtime_settings_service()
    current_doc = svc.load_document_parsing(include_process_overrides=False)
    current_mineru = dict(current_doc.get("engines", {}).get("mineru", {}))

    existing_token = current_mineru.get("api_token") or ""
    effective_token = token.strip() if (token and token.strip()) else existing_token

    mineru_patch = {
        **current_mineru,
        "mode": "cloud",
        "api_base_url": "https://mineru.net",
        "api_token": effective_token,
        "model_version": "vlm",
        "language": "ch",
        "enable_formula": True,
        "enable_table": True,
        "is_ocr": True,
        "max_pages_per_part": 110,
    }
    svc.save_document_parsing({
        **current_doc,
        "version": 2,
        "engine": "mineru",
        "engines": {
            **current_doc.get("engines", {}),
            "mineru": mineru_patch,
        },
    })
    return svc.load_mineru(include_process_overrides=False)


def _build_page_heading_map(pdf_path: Path) -> dict[int, str]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    toc = sorted(doc.get_toc(), key=lambda x: x[2])
    page_heading: dict[int, str] = {}
    current_h1 = ""
    current_h2 = ""
    toc_idx = 0
    for pno in range(1, len(doc) + 1):
        while toc_idx < len(toc) and toc[toc_idx][2] <= pno:
            lvl, title, _ = toc[toc_idx]
            if lvl == 1:
                current_h1 = title.strip()
                current_h2 = ""
            else:
                current_h2 = title.strip()
            toc_idx += 1
        label = " / ".join(x for x in [current_h1, current_h2] if x)
        page_heading[pno] = label or "前言与目录"
    return page_heading


def parse_math_with_mineru_cloud() -> None:
    """使用 DeepTutor 内置的 MinerU Cloud v4 客户端解析《北师大版七年级上册数学》扫描版 PDF 并同步进 sz-g7-math-bsd。"""
    os.environ["DEEPTUTOR_HOME"] = str(DEEPTUTOR_HOME)

    import subprocess
    import time
    from urllib.parse import urlparse
    import deeptutor.services.parsing.engines.mineru.cloud as mineru_cloud
    from deeptutor.services.parsing.engines.mineru.cloud import parse_cloud, verify_credentials
    from deeptutor.services.parsing.engines.mineru.config import MinerUError, resolve_mineru_config

    def _resolve_real_ips_via_doh(host: str) -> list[str]:
        try:
            res = subprocess.run(
                ["/usr/bin/curl", "-fsSL", "--connect-timeout", "5", "--noproxy", "*", f"https://223.5.5.5/resolve?name={host}&type=A"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                payload = json.loads(res.stdout)
                return [
                    ans["data"]
                    for ans in payload.get("Answer", [])
                    if ans.get("type") == 1 and isinstance(ans.get("data"), str)
                ]
        except Exception:
            pass
        return []

    def _resilient_download(zip_url: str) -> bytes:
        host = urlparse(zip_url).netloc
        real_ips = _resolve_real_ips_via_doh(host)
        print(f"  [MinerU] 正在从 CDN ({host}, DoH真实IP={real_ips[:3]}) 下载解析结果包...", flush=True)
        cmds: list[list[str]] = []
        for ip in real_ips[:4]:
            cmds.append([
                "/usr/bin/curl", "-fsSL", "--retry", "2", "--connect-timeout", "20", "--max-time", "300",
                "--noproxy", "*", "--resolve", f"{host}:443:{ip}", zip_url,
            ])
        cmds.append(["/usr/bin/curl", "-fsSL", "--retry", "2", "--connect-timeout", "20", "--max-time", "300", zip_url])
        last_err = ""
        for idx, cmd in enumerate(cmds, start=1):
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and len(res.stdout) > 100:
                print(f"  [MinerU] 下载成功 ({len(res.stdout) / 1024:.1f} KB, 策略 #{idx})", flush=True)
                return res.stdout
            last_err = res.stderr.decode("utf-8", errors="ignore").strip()
            print(f"  [MinerU] 下载策略 #{idx} 未成功 ({last_err})，尝试下一策略...", flush=True)
            time.sleep(1)
        raise MinerUError(f"Failed to download MinerU result archive from {host}: {last_err}")

    mineru_cloud._download = _resilient_download

    cfg = resolve_mineru_config()
    if not cfg.api_keys:
        print(
            "[提示] 尚未配置 MinerU 云端 API Token。\n"
            "请先执行：\n"
            "  ~/.deeptutor-venv/bin/python tools/sync_to_deeptutor.py --set-mineru-token '<您的Token>'\n"
            "或在 DeepTutor Web (http://127.0.0.1:3782/settings -> 文档解析 -> MinerU) 中填入 API Token，然后再运行 --mineru-math。"
        )
        raise SystemExit(1)

    print("[MinerU Cloud] 正在验证 API Token 连通性 (https://mineru.net/api/v4/file-urls/batch)...")
    verify_credentials(cfg)
    print("[MinerU Cloud] API Token 验证通过！")

    math_dir = LEDGER_ROOT / "00_教材与参考书" / "02_数学"
    pdf_path = math_dir / "义务教育教科书·数学七年级上册（北师大版）.pdf"
    if not pdf_path.exists():
        ingest_g7_textbooks_from_raw()

    workdir = DEEPTUTOR_HOME / "data" / "mineru_workdir" / "sz-g7-math-bsd"
    workdir.mkdir(parents=True, exist_ok=True)

    print(
        f"[MinerU Cloud] 开始上传并解析 {pdf_path.name}"
        f"（共 209 页，自动按 {cfg.max_pages_per_part} 页/批分段上传，支持断点续传，model_version={cfg.model_version}）..."
    )
    out_dir = parse_cloud(
        pdf_path,
        workdir,
        cfg,
        timeout=900.0,
        on_progress=lambda msg: print(f"  [MinerU] {msg.strip()}", flush=True),
    )

    page_heading = _build_page_heading_map(pdf_path)
    content_lists = sorted(out_dir.glob("*_content_list.json"))
    md_files = sorted(out_dir.rglob("*.md"))

    merged_parts = [
        "# 义务教育教科书·数学七年级上册（北师大版 · MinerU 云端高精度公式与章节页码全文）",
        "",
        "- 教材版本：北师大版（2024新课标修订）",
        "- 对应知识库：`sz-g7-math-bsd`",
        "- 解析引擎：MinerU Cloud v4 API（含 LaTeX 公式、表格与扫描页 OCR）",
        "",
    ]

    if content_lists:
        items = json.loads(content_lists[0].read_text(encoding="utf-8"))
        by_page: dict[int, list[str]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            pno = int(item.get("page_idx", 0)) + 1
            btype = item.get("type", "")
            text = (item.get("text") or "").strip()
            if btype == "equation" and text:
                clean_eq = text.strip().removeprefix("$$").removesuffix("$$").strip()
                by_page.setdefault(pno, []).append(f"\n$$\n{clean_eq}\n$$\n")
            elif btype == "table":
                tbl = (item.get("table_body") or item.get("html") or text).strip()
                caption = " ".join(item.get("table_caption") or [])
                if caption:
                    by_page.setdefault(pno, []).append(f"**{caption}**")
                if tbl:
                    by_page.setdefault(pno, []).append(tbl)
            elif btype == "image":
                caption = " ".join(item.get("img_caption") or item.get("image_caption") or [])
                if caption:
                    by_page.setdefault(pno, []).append(f"*[教材配图：{caption}]*")
            elif text:
                lvl = item.get("text_level")
                if lvl == 1:
                    by_page.setdefault(pno, []).append(f"#### {text}")
                else:
                    by_page.setdefault(pno, []).append(text)

        if by_page:
            merged_parts.append("## 按页码与章节对齐全文（PDF 第 1–209 页）")
            merged_parts.append("")
            for pno in sorted(by_page.keys()):
                heading = page_heading.get(pno, "")
                merged_parts.append(f"### 【数学七上 · PDF第{pno}页 · {heading}】")
                merged_parts.extend(by_page[pno])
                merged_parts.append("")

    if md_files and not content_lists:
        for mf in md_files:
            merged_parts.append(mf.read_text(encoding="utf-8"))

    target_md = math_dir / "北师大版七年级上册数学_MinerU全文解析.md"
    target_md.write_text("\n\n".join(merged_parts) + "\n", encoding="utf-8")
    print(f"[完成] MinerU 解析全文已保存至: {target_md}")

    math_cfg = next(b for b in G7_VOL1_TEXTBOOKS if b["subject"] == "数学")
    tb_dir = export_subject_textbook_kb(math_cfg, ["七年级"])
    rebuild_kb_from_dir("sz-g7-math-bsd", tb_dir)


MINERU_SCANNED_BOOKS: list[dict[str, Any]] = [
    {
        "key": "sz-g7-math-vol1",
        "subject": "数学",
        "term_short": "七上",
        "term_full": "七年级上册",
        "edition": "北师大版",
        "dir": "02_数学",
        "kb": "sz-g7-math-bsd",
        "src_rel": "数学/北师大版/（根据2022年版课程标准修订）义务教育教科书•数学七年级上册.pdf",
        "out_md": "北师大版七年级上册数学_MinerU全文解析.md",
        "toc_md": "北师大版七年级上册数学_官方目录与页码表.md",
    },
    {
        "key": "sz-g7-math-vol2",
        "subject": "数学",
        "term_short": "七下",
        "term_full": "七年级下册",
        "edition": "北师大版",
        "dir": "02_数学",
        "kb": "sz-g7-math-bsd",
        "src_rel": "数学/北师大版/（根据2022年版课程标准修订）义务教育教科书·数学七年级下册.pdf",
        "out_md": "北师大版七年级下册数学_MinerU全文解析.md",
        "toc_md": "北师大版七年级下册数学_官方目录与页码表.md",
    },
    {
        "key": "sz-g8-math-vol1",
        "subject": "数学",
        "term_short": "八上",
        "term_full": "八年级上册",
        "edition": "北师大版",
        "dir": "02_数学",
        "kb": "sz-g8-math-bsd",
        "src_rel": "数学/北师大版/（根据2022年版课程标准修订）义务教育教科书•数学八年级上册.pdf",
        "out_md": "北师大版八年级上册数学_MinerU全文解析.md",
        "toc_md": "北师大版八年级上册数学_官方目录与页码表.md",
    },
    {
        "key": "sz-g8-math-vol2",
        "subject": "数学",
        "term_short": "八下",
        "term_full": "八年级下册",
        "edition": "北师大版",
        "dir": "02_数学",
        "kb": "sz-g8-math-bsd",
        "src_rel": "数学/北师大版/（根据2022年版课程标准修订）义务教育教科书·数学八年级下册.pdf",
        "out_md": "北师大版八年级下册数学_MinerU全文解析.md",
        "toc_md": "北师大版八年级下册数学_官方目录与页码表.md",
    },
    {
        "key": "sz-g9-math-vol1",
        "subject": "数学",
        "term_short": "九上",
        "term_full": "九年级上册",
        "edition": "北师大版",
        "dir": "02_数学",
        "kb": "sz-g9-math-bsd",
        "src_rel": "数学/北师大版/（根据2022年版课程标准修订）义务教育教科书·数学九年级上册.pdf",
        "out_md": "北师大版九年级上册数学_MinerU全文解析.md",
        "toc_md": "北师大版九年级上册数学_官方目录与页码表.md",
    },
    {
        "key": "sz-g9-math-vol2",
        "subject": "数学",
        "term_short": "九下",
        "term_full": "九年级下册",
        "edition": "北师大版",
        "dir": "02_数学",
        "kb": "sz-g9-math-bsd",
        "src_rel": "数学/北师大版/义务教育教科书·数学九年级下册.pdf",
        "out_md": "北师大版九年级下册数学_MinerU全文解析.md",
        "toc_md": "北师大版九年级下册数学_官方目录与页码表.md",
    },
    {
        "key": "sz-g9-english-vol1",
        "subject": "英语",
        "term_short": "九上",
        "term_full": "九年级上册",
        "edition": "沪教版",
        "dir": "03_英语",
        "kb": "sz-g9-english-hj",
        "src_rel": "英语/沪教版/（根据2022年版课程标准修订）义务教育教科书·英语九年级上册.pdf",
        "out_md": "英语_九年级上册_MinerU全文解析.md",
        "toc_md": "英语_九年级上册_官方目录与页码表.md",
    },
]

ALL_GRADE_KBS: list[dict[str, Any]] = [
    # 七年级 (7科，含上下册)
    {"kb": "sz-g7-chinese-tb", "subject": "语文", "dir": "01_语文", "keywords": ["七年级"]},
    {"kb": "sz-g7-math-bsd", "subject": "数学", "dir": "02_数学", "keywords": ["七年级"]},
    {"kb": "sz-g7-english-hj", "subject": "英语", "dir": "03_英语", "keywords": ["七年级"]},
    {"kb": "sz-g7-geography-xj", "subject": "地理", "dir": "04_地理", "keywords": ["七年级"]},
    {"kb": "sz-g7-history-tb", "subject": "历史", "dir": "05_历史", "keywords": ["七年级"]},
    {"kb": "sz-g7-biology-rj", "subject": "生物", "dir": "06_生物", "keywords": ["七年级"]},
    {"kb": "sz-g7-morality-tb", "subject": "道法", "dir": "07_道法", "keywords": ["七年级"]},
    # 八年级 (8科，含上下册)
    {"kb": "sz-g8-chinese-tb", "subject": "语文", "dir": "01_语文", "keywords": ["八年级"]},
    {"kb": "sz-g8-math-bsd", "subject": "数学", "dir": "02_数学", "keywords": ["八年级"]},
    {"kb": "sz-g8-english-hj", "subject": "英语", "dir": "03_英语", "keywords": ["八年级"]},
    {"kb": "sz-g8-geography-xj", "subject": "地理", "dir": "04_地理", "keywords": ["八年级"]},
    {"kb": "sz-g8-history-tb", "subject": "历史", "dir": "05_历史", "keywords": ["八年级"]},
    {"kb": "sz-g8-biology-rj", "subject": "生物", "dir": "06_生物", "keywords": ["八年级"]},
    {"kb": "sz-g8-morality-tb", "subject": "道法", "dir": "07_道法", "keywords": ["八年级"]},
    {"kb": "sz-g8-physics-rj", "subject": "物理", "dir": "08_物理", "keywords": ["八年级"]},
    # 九年级 (7科，含上下册/全一册/初中读本)
    {"kb": "sz-g9-chinese-tb", "subject": "语文", "dir": "01_语文", "keywords": ["九年级"]},
    {"kb": "sz-g9-math-bsd", "subject": "数学", "dir": "02_数学", "keywords": ["九年级"]},
    {"kb": "sz-g9-english-hj", "subject": "英语", "dir": "03_英语", "keywords": ["九年级"]},
    {"kb": "sz-g9-history-tb", "subject": "历史", "dir": "05_历史", "keywords": ["九年级"]},
    {"kb": "sz-g9-morality-tb", "subject": "道法", "dir": "07_道法", "keywords": ["九年级", "初中学生读本"]},
    {"kb": "sz-g9-physics-rj", "subject": "物理", "dir": "08_物理", "keywords": ["九年级"]},
    {"kb": "sz-g9-chemistry-rj", "subject": "化学", "dir": "09_化学", "keywords": ["九年级"]},
]


def parse_one_scanned_book_mineru(book: dict[str, Any]) -> Path:
    os.environ["DEEPTUTOR_HOME"] = str(DEEPTUTOR_HOME)
    import pymupdf
    from deeptutor.services.parsing.engines.mineru.cloud import parse_cloud
    from deeptutor.services.parsing.engines.mineru.config import resolve_mineru_config

    sub_dir = LEDGER_ROOT / "00_教材与参考书" / book["dir"]
    sub_dir.mkdir(parents=True, exist_ok=True)
    target_md = sub_dir / book["out_md"]
    toc_md = sub_dir / book["toc_md"]
    pdf_path = RAW_TEXTBOOK_ROOT / book["src_rel"]

    doc = pymupdf.open(pdf_path)
    toc = sorted(doc.get_toc(), key=lambda x: x[2])
    if not toc_md.exists() and toc:
        toc_lines = [
            f"# 义务教育教科书·{book['subject']}{book['term_full']}（{book['edition']} · 深圳初中教材）",
            "",
            f"- 学科：{book['subject']}（{book['term_full']}）",
            f"- 教材版本：{book['edition']}",
            f"- 对应知识库：`{book['kb']}`",
            f"- 总页数：{len(doc)} 页",
            "",
            "## 官方目录与页码索引（PDF 页码）",
            "",
        ]
        for lvl, title, pg in toc:
            indent = "  " * max(0, lvl - 1)
            toc_lines.append(f"{indent}- **{title.strip()}**（PDF 第 {pg} 页）")
        toc_md.write_text("\n".join(toc_lines) + "\n", encoding="utf-8")

    if target_md.exists() and target_md.stat().st_size > 20000:
        print(f"[跳过已解析] {target_md.name} ({target_md.stat().st_size} bytes)", flush=True)
        return target_md

    cfg = resolve_mineru_config()
    workdir = DEEPTUTOR_HOME / "data" / "mineru_workdir" / book["key"]
    workdir.mkdir(parents=True, exist_ok=True)

    print(f"[MinerU Cloud] 开始解析 {book['subject']}{book['term_full']}（共 {len(doc)} 页）...", flush=True)
    out_dir = parse_cloud(
        pdf_path,
        workdir,
        cfg,
        timeout=1200.0,
        on_progress=lambda msg: print(f"  [{book['key']}] {msg.strip()}", flush=True),
    )

    page_heading = _build_page_heading_map(pdf_path)
    content_lists = sorted(out_dir.glob("*_content_list.json"))
    md_files = sorted(out_dir.rglob("*.md"))

    merged_parts = [
        f"# 义务教育教科书·{book['subject']}{book['term_full']}（{book['edition']} · MinerU 云端高精度公式与章节页码全文）",
        "",
        f"- 教材版本：{book['edition']}（2022年版新课标）",
        f"- 对应知识库：`{book['kb']}`",
        "- 解析引擎：MinerU Cloud v4 API（含 LaTeX 公式、表格与扫描页 VLM OCR）",
        "",
    ]

    if content_lists:
        items = json.loads(content_lists[0].read_text(encoding="utf-8"))
        by_page: dict[int, list[str]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            pno = int(item.get("page_idx", 0)) + 1
            btype = item.get("type", "")
            text = (item.get("text") or "").strip()
            if btype == "equation" and text:
                clean_eq = text.strip().removeprefix("$$").removesuffix("$$").strip()
                by_page.setdefault(pno, []).append(f"\n$$\n{clean_eq}\n$$\n")
            elif btype == "table":
                tbl = (item.get("table_body") or item.get("html") or text).strip()
                caption = " ".join(item.get("table_caption") or [])
                if caption:
                    by_page.setdefault(pno, []).append(f"**{caption}**")
                if tbl:
                    by_page.setdefault(pno, []).append(tbl)
            elif btype == "image":
                caption = " ".join(item.get("img_caption") or item.get("image_caption") or [])
                if caption:
                    by_page.setdefault(pno, []).append(f"*[教材配图：{caption}]*")
            elif text:
                lvl = item.get("text_level")
                if lvl == 1:
                    by_page.setdefault(pno, []).append(f"#### {text}")
                else:
                    by_page.setdefault(pno, []).append(text)

        if by_page:
            merged_parts.append(f"## 按页码与章节对齐全文（PDF 第 1–{len(doc)} 页）")
            merged_parts.append("")
            for pno in sorted(by_page.keys()):
                heading = page_heading.get(pno, "")
                merged_parts.append(f"### 【{book['subject']}{book['term_short']} · PDF第{pno}页 · {heading}】")
                merged_parts.extend(by_page[pno])
                merged_parts.append("")

    if md_files and not content_lists:
        for mf in md_files:
            merged_parts.append(mf.read_text(encoding="utf-8"))

    target_md.write_text("\n\n".join(merged_parts) + "\n", encoding="utf-8")
    print(f"[完成] {book['subject']}{book['term_full']} MinerU 全文已保存至: {target_md}", flush=True)
    return target_md


def _install_mineru_doh_patch() -> None:
    import time
    from urllib.parse import urlparse
    import deeptutor.services.parsing.engines.mineru.cloud as mineru_cloud
    from deeptutor.services.parsing.engines.mineru.config import MinerUError

    orig_upload = mineru_cloud._upload_file

    def _resolve_real_ips_via_doh(host: str) -> list[str]:
        try:
            res = subprocess.run(
                ["/usr/bin/curl", "-fsSL", "--connect-timeout", "5", "--noproxy", "*", f"https://223.5.5.5/resolve?name={host}&type=A"],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                payload = json.loads(res.stdout)
                return [
                    ans["data"]
                    for ans in payload.get("Answer", [])
                    if ans.get("type") == 1 and isinstance(ans.get("data"), str)
                ]
        except Exception:
            pass
        return []

    def _resilient_upload(file_path: Path, upload_url: str) -> None:
        try:
            orig_upload(file_path, upload_url)
            return
        except Exception as exc:
            host = urlparse(upload_url).netloc
            real_ips = _resolve_real_ips_via_doh(host)
            print(f"  [MinerU] 默认上传遇阻 ({exc})，切换 DoH 真实 IP ({real_ips[:2]}) 重试上传 {file_path.name}...", flush=True)
            for ip in real_ips[:3]:
                cmd = [
                    "/usr/bin/curl", "-fsSL", "-X", "PUT",
                    "--connect-timeout", "20", "--max-time", "300",
                    "--noproxy", "*", "--resolve", f"{host}:443:{ip}",
                    "-T", str(file_path), upload_url,
                ]
                res = subprocess.run(cmd, capture_output=True)
                if res.returncode == 0:
                    return
            raise

    def _resilient_download(zip_url: str) -> bytes:
        host = urlparse(zip_url).netloc
        real_ips = _resolve_real_ips_via_doh(host)
        print(f"  [MinerU] 正在从 CDN ({host}, DoH真实IP={real_ips[:3]}) 下载解析结果包...", flush=True)
        cmds: list[list[str]] = []
        for ip in real_ips[:4]:
            cmds.append([
                "/usr/bin/curl", "-fsSL", "--retry", "2", "--connect-timeout", "20", "--max-time", "300",
                "--noproxy", "*", "--resolve", f"{host}:443:{ip}", zip_url,
            ])
        cmds.append(["/usr/bin/curl", "-fsSL", "--retry", "2", "--connect-timeout", "20", "--max-time", "300", zip_url])
        last_err = ""
        for idx, cmd in enumerate(cmds, start=1):
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and len(res.stdout) > 100:
                print(f"  [MinerU] 下载成功 ({len(res.stdout) / 1024:.1f} KB, 策略 #{idx})", flush=True)
                return res.stdout
            last_err = res.stderr.decode("utf-8", errors="ignore").strip()
            print(f"  [MinerU] 下载策略 #{idx} 未成功 ({last_err})，尝试下一策略...", flush=True)
            time.sleep(1)
        raise MinerUError(f"Failed to download MinerU result archive from {host}: {last_err}")

    mineru_cloud._upload_file = _resilient_upload
    mineru_cloud._download = _resilient_download


def parse_all_scanned_with_mineru_cloud(max_workers: int = 2) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _install_mineru_doh_patch()
    pending = [b for b in MINERU_SCANNED_BOOKS]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(parse_one_scanned_book_mineru, b): b for b in pending}
        for fut in as_completed(futs):
            b = futs[fut]
            res_path = fut.result()
            print(f"[MinerU汇总] {b['key']} -> {res_path.name}", flush=True)


def sync_all_grade_kbs() -> None:
    for kb_cfg in ALL_GRADE_KBS:
        tb_dir = export_subject_textbook_kb(kb_cfg, kb_cfg["keywords"])
        rebuild_kb_from_dir(kb_cfg["kb"], tb_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="将学习台账错题与初中三年全科教材单向同步至 DeepTutor 知识库")
    parser.add_argument("--wrongbook", action="store_true", help="仅同步 qiuyu-wrongbook 错题知识库")
    parser.add_argument("--textbooks", action="store_true", help="归档并同步七年级教材知识库")
    parser.add_argument("--all-grades", action="store_true", help="构建初一、初二、初三全套 22 个学科知识库")
    parser.add_argument("--subject", type=str, default="", help="仅同步指定学科教材（如：语文、数学、英语、地理、历史、生物、道法、物理、化学）")
    parser.add_argument("--set-mineru-token", type=str, default="", help="设置 MinerU 云端 API Token（写入 document_parsing.json）")
    parser.add_argument("--mineru-math", action="store_true", help="使用 MinerU 云端 API 解析北师大七上数学扫描版 PDF 并重建 sz-g7-math-bsd")
    parser.add_argument("--mineru-all", action="store_true", help="使用 MinerU 云端 API 解析初中三年全部 7 本扫描教材（数学6册+英语九上）")
    args = parser.parse_args()

    # 始终确保 MinerU 默认预置为 cloud + OCR + 公式模式
    configure_mineru_cloud(args.set_mineru_token if args.set_mineru_token else None)
    if args.set_mineru_token:
        print("[完成] 已将 MinerU 云端 API Token 写入 ~/.deeptutor/data/user/settings/document_parsing.json。")
        if not (args.mineru_math or args.mineru_all or args.all_grades or args.textbooks or args.wrongbook):
            return

    if args.mineru_all:
        parse_all_scanned_with_mineru_cloud(max_workers=2)
        if args.all_grades:
            sync_all_grade_kbs()
        return

    if args.all_grades:
        sync_all_grade_kbs()
        return

    if args.mineru_math:
        parse_math_with_mineru_cloud()
        return

    do_all = not (args.wrongbook or args.textbooks or args.subject)

    if do_all or args.wrongbook:
        wb_dir = export_wrongbook()
        rebuild_kb_from_dir("qiuyu-wrongbook", wb_dir)

    if do_all or args.textbooks or args.subject:
        ingest_g7_textbooks_from_raw()
        for b in G7_VOL1_TEXTBOOKS:
            if args.subject and b["subject"] != args.subject.strip():
                continue
            tb_dir = export_subject_textbook_kb(b, ["七年级"])
            rebuild_kb_from_dir(b["kb"], tb_dir)


if __name__ == "__main__":
    main()
