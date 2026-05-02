#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 迁移工具 (migrate.py)
===============================
备份、恢复、检查 OpenClaw 配置和工作空间。

用法：
    python3 migrate.py backup [output_dir]     # 备份到指定目录
    python3 migrate.py restore <backup.tar.gz> # 从备份恢复
    python3 migrate.py check                   # 检查当前环境完整性
    python3 migrate.py info <backup.tar.gz>    # 查看备份信息

技术要求：纯 Python 3 标准库，无需安装任何第三方包。
"""

import os
import sys
import tarfile
import json
import hashlib
import platform
import shutil
import subprocess
import time
import fnmatch
from datetime import datetime
from pathlib import Path

# ============================================================
# ANSI 颜色常量
# ============================================================
class C:
    """ANSI 终端颜色码"""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"

# ============================================================
# 全局常量
# ============================================================
# OpenClaw 根目录
OPENCLAW_HOME = os.path.expanduser("~/.openclaw")
WORKSPACE     = os.path.join(OPENCLAW_HOME, "workspace")

# 备份时排除的模式
EXCLUDE_PATTERNS = [
    "node_modules/",
    "__pycache__/",
    ".git/",
    "*.pyc",
    ".env",
    "*.egg-info/",
    ".DS_Store",
]

# 检查时需要的关键文件（相对于 workspace/）
KEY_FILES = [
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "TOOLS.md",
    "AGENTS.md",
]

# ============================================================
# 辅助函数
# ============================================================

def ok(msg):
    """绿色 OK 标记"""
    print(f"  {C.GREEN}✔{C.RESET} {msg}")

def warn(msg):
    """黄色警告标记"""
    print(f"  {C.YELLOW}⚠{C.RESET} {msg}")

def fail(msg):
    """红色错误标记"""
    print(f"  {C.RED}✘{C.RESET} {msg}")

def info(msg):
    """蓝色信息"""
    print(f"  {C.BLUE}ℹ{C.RESET} {msg}")

def header(title):
    """分区标题"""
    print(f"\n{C.BOLD}{C.CYAN}{'═'*50}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'═'*50}{C.RESET}")

def md5sum(filepath, chunk_size=65536):
    """计算文件的 MD5 校验值"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def human_size(num_bytes):
    """将字节数转换为人类可读的大小"""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

def should_exclude(path, exclude_patterns):
    """
    判断路径是否匹配排除模式。
    path 应为相对路径（相对于 openclaw 根目录），末尾带 '/' 表示目录。
    """
    # 逐段检查路径中的每一部分
    parts = Path(path).parts
    for pattern in exclude_patterns:
        pattern = pattern.rstrip("/")
        # 对路径的每一级目录名做匹配
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
        # 也对完整路径做匹配
        if fnmatch.fnmatch(path, pattern):
            return True
        if fnmatch.fnmatch(path, pattern + "/"):
            return True
    return False

def get_openclaw_version():
    """尝试获取 OpenClaw 版本号"""
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # 备用：读取 package.json
    try:
        pkg_path = os.path.join(
            os.path.dirname(os.path.dirname(shutil.which("openclaw") or "")),
            "package.json"
        )
        if os.path.exists(pkg_path):
            with open(pkg_path, "r") as f:
                data = json.load(f)
                return data.get("version", "unknown")
    except Exception:
        pass
    return "unknown"

def progress_bar(current, total, width=40, prefix=""):
    """在终端绘制进度条"""
    if total == 0:
        pct = 100
    else:
        pct = int(current / total * 100)
    filled = int(width * current / total) if total > 0 else width
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r  {prefix}[{bar}] {pct:3d}% ({current}/{total})")
    sys.stdout.flush()

# ============================================================
# exclude_filter — 传给 tarfile 的 filter 函数
# ============================================================
def make_exclude_filter(exclude_patterns):
    """
    创建一个 tarfile 的 filter 函数，排除匹配的文件/目录。
    返回一个可调用的函数：filter(tarinfo, path) -> tarinfo 或 None。
    """
    def exclude_filter(tarinfo, path):
        # 计算相对于 OPENCLAW_HOME 的路径
        relpath = os.path.relpath(path, OPENCLAW_HOME)
        if relpath == ".":
            relpath = tarinfo.name
        if should_exclude(relpath, exclude_patterns) or should_exclude(tarinfo.name, exclude_patterns):
            return None
        return tarinfo
    return exclude_filter

# ============================================================
# backup 命令
# ============================================================
def cmd_backup(output_dir=None):
    """
    备份 ~/.openclaw 目录。
    生成 timestamped tar.gz + manifest.json + .md5 校验文件。
    """
    header("OpenClaw 备份工具")

    # 检查源目录
    if not os.path.isdir(OPENCLAW_HOME):
        fail(f"OpenClaw 目录不存在: {OPENCLAW_HOME}")
        sys.exit(1)

    # 准备输出目录
    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "openclaw-backups")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hostname = platform.node()
    archive_name = f"openclaw-backup_{hostname}_{timestamp}.tar.gz"
    archive_path = os.path.join(output_dir, archive_name)

    print(f"\n  源目录:  {OPENCLAW_HOME}")
    print(f"  输出文件: {archive_path}")
    print(f"  主机名:  {hostname}")
    print(f"  排除:    {', '.join(EXCLUDE_PATTERNS)}")
    print()

    # 收集文件信息
    print(f"  {C.DIM}正在扫描文件...{C.RESET}")
    file_list = []
    total_size = 0
    file_count = 0

    for root, dirs, files in os.walk(OPENCLAW_HOME):
        # 预先过滤目录以加速遍历
        dirs[:] = [
            d for d in dirs
            if not should_exclude(os.path.relpath(os.path.join(root, d), OPENCLAW_HOME) + "/", EXCLUDE_PATTERNS)
        ]
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, OPENCLAW_HOME)
            if should_exclude(rel_path, EXCLUDE_PATTERNS):
                continue
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            file_list.append({
                "path": rel_path,
                "size": size,
            })
            total_size += size
            file_count += 1

    print(f"  找到 {C.BOLD}{file_count}{C.RESET} 个文件，总计 {C.BOLD}{human_size(total_size)}{C.RESET}")

    # 创建 manifest
    manifest = {
        "backup_time": datetime.now().isoformat(),
        "hostname": hostname,
        "openclaw_version": get_openclaw_version(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "file_count": file_count,
        "total_size": total_size,
        "total_size_human": human_size(total_size),
        "excluded_patterns": EXCLUDE_PATTERNS,
        "files": file_list,
    }

    # 打包
    print(f"\n  {C.DIM}正在打包...{C.RESET}")
    exclude_fn = make_exclude_filter(EXCLUDE_PATTERNS)

    with tarfile.open(archive_path, "w:gz") as tar:
        # 先添加 manifest
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        manifest_info = tarfile.TarInfo(name="manifest.json")
        manifest_info.size = len(manifest_bytes)
        manifest_info.mtime = time.time()
        tar.addfile(manifest_info, fileobj=__import__("io").BytesIO(manifest_bytes))

        # 逐个添加文件
        added = 0
        for entry in file_list:
            full_path = os.path.join(OPENCLAW_HOME, entry["path"])
            try:
                tar.add(full_path, arcname=entry["path"], filter=exclude_fn)
            except Exception as e:
                warn(f"跳过 {entry['path']}: {e}")
            added += 1
            if added % 100 == 0 or added == file_count:
                progress_bar(added, file_count, prefix="打包进度")

    print()  # 换行
    print(f"  打包完成: {C.BOLD}{human_size(os.path.getsize(archive_path))}{C.RESET}")

    # 计算 MD5
    print(f"  {C.DIM}正在计算 MD5...{C.RESET}")
    md5_value = md5sum(archive_path)
    md5_path = archive_path + ".md5"
    with open(md5_path, "w") as f:
        f.write(f"{md5_value}  {archive_name}\n")
    print(f"  MD5: {C.BOLD}{md5_value}{C.RESET}")

    print(f"\n  {C.GREEN}{C.BOLD}✔ 备份完成！{C.RESET}")
    print(f"  归档文件: {archive_path}")
    print(f"  校验文件: {md5_path}")

    return archive_path

# ============================================================
# restore 命令
# ============================================================
def cmd_restore(archive_path):
    """
    从备份恢复到 ~/.openclaw。
    智能合并：新文件直接复制，已有文件提示。
    """
    header("OpenClaw 恢复工具")

    if not os.path.isfile(archive_path):
        fail(f"备份文件不存在: {archive_path}")
        sys.exit(1)

    # 验证 MD5（如果有 .md5 文件）
    md5_path = archive_path + ".md5"
    if os.path.isfile(md5_path):
        print(f"\n  {C.DIM}正在验证 MD5 校验...{C.RESET}")
        with open(md5_path, "r") as f:
            expected_md5 = f.read().split()[0]
        actual_md5 = md5sum(archive_path)
        if expected_md5 == actual_md5:
            ok(f"MD5 校验通过: {actual_md5}")
        else:
            fail(f"MD5 校验失败！期望 {expected_md5}，实际 {actual_md5}")
            ans = input(f"\n  {C.YELLOW}继续恢复？(y/N): {C.RESET}").strip().lower()
            if ans != "y":
                print("  已取消恢复。")
                sys.exit(1)
    else:
        warn("未找到 .md5 校验文件，跳过 MD5 验证")

    # 解压 manifest
    print(f"\n  {C.DIM}正在读取备份信息...{C.RESET}")
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            manifest_member = tar.extractfile("manifest.json")
            if manifest_member is None:
                fail("备份中未找到 manifest.json")
                sys.exit(1)
            manifest = json.loads(manifest_member.read().decode("utf-8"))
    except Exception as e:
        fail(f"读取备份失败: {e}")
        sys.exit(1)

    # 显示备份信息
    print(f"\n  {C.BOLD}备份信息:{C.RESET}")
    print(f"  ├─ 备份时间:    {manifest.get('backup_time', '未知')}")
    print(f"  ├─ 源主机:      {manifest.get('hostname', '未知')}")
    print(f"  ├─ OpenClaw:    {manifest.get('openclaw_version', '未知')}")
    print(f"  ├─ 文件总数:    {manifest.get('file_count', '?')}")
    print(f"  └─ 总大小:      {manifest.get('total_size_human', '?')}")

    # 列出包含的 skills
    files = manifest.get("files", [])
    skills = set()
    for f in files:
        parts = Path(f["path"]).parts
        if "skills" in parts:
            idx = parts.index("skills")
            if idx + 1 < len(parts):
                skills.add(parts[idx + 1])
    if skills:
        print(f"\n  {C.BOLD}包含的 Skills:{C.RESET} {', '.join(sorted(skills))}")

    # 检测文件冲突
    target_dir = OPENCLAW_HOME
    conflicts = []
    new_files = []
    for entry in files:
        rel_path = entry["path"]
        target_path = os.path.join(target_dir, rel_path)
        if os.path.exists(target_path):
            conflicts.append(rel_path)
        else:
            new_files.append(rel_path)

    print(f"\n  {C.BOLD}恢复摘要:{C.RESET}")
    print(f"  ├─ 新文件（直接复制）: {C.GREEN}{len(new_files)}{C.RESET}")
    print(f"  ├─ 已存在文件（需要合并）: {C.YELLOW}{len(conflicts)}{C.RESET}")
    print(f"  └─ 总文件数: {len(files)}")

    if conflicts:
        print(f"\n  {C.DIM}存在冲突的文件（前 20 个）:{C.RESET}")
        for c in conflicts[:20]:
            print(f"    {C.YELLOW}•{C.RESET} {c}")
        if len(conflicts) > 20:
            print(f"    ... 还有 {len(conflicts) - 20} 个文件")

    # 交互确认
    print()
    ans = input(f"  {C.BOLD}确认恢复？(y/N): {C.RESET}").strip().lower()
    if ans != "y":
        print("  已取消恢复。")
        sys.exit(0)

    # 开始恢复
    print(f"\n  {C.DIM}正在恢复...{C.RESET}")
    restored = 0
    skipped = 0
    errors = 0

    # 处理已有文件的 diff 提示目录
    diff_dir = os.path.join(target_dir, "_merge_conflicts_" + datetime.now().strftime("%Y%m%d_%H%M%S"))

    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        total = len([m for m in members if m.name != "manifest.json"])
        count = 0

        for member in members:
            if member.name == "manifest.json":
                continue

            target_path = os.path.join(target_dir, member.name)
            rel_path = member.name

            if os.path.exists(target_path):
                # 已有文件：备份旧版本，提取新版本到临时位置
                os.makedirs(diff_dir, exist_ok=True)
                backup_old = os.path.join(diff_dir, "old_" + os.path.basename(member.name))
                try:
                    shutil.copy2(target_path, backup_old)
                    info(f"冲突: {rel_path} → 备份到 {diff_dir}")
                    # 仍然解压覆盖（智能合并）
                    tar.extract(member, target_dir)
                except Exception as e:
                    fail(f"恢复失败 {rel_path}: {e}")
                    errors += 1
                skipped += 1
            else:
                # 新文件：直接提取
                try:
                    tar.extract(member, target_dir)
                except Exception as e:
                    fail(f"恢复失败 {rel_path}: {e}")
                    errors += 1

            restored += 1
            count += 1
            if count % 50 == 0 or count == total:
                progress_bar(count, total, prefix="恢复进度")

    print()  # 换行

    if errors > 0:
        fail(f"恢复完成，有 {errors} 个错误")
    else:
        ok(f"恢复完成！")

    print(f"  处理文件: {restored} | 已有文件（冲突）: {skipped}")

    if conflicts:
        print(f"\n  {C.YELLOW}提示:{C.RESET} 已有文件的旧版本已备份到:")
        print(f"    {diff_dir}")
        print(f"  你可以手动 diff 比较差异。")

    # 自动运行 check
    print(f"\n  {C.DIM}正在运行完整性检查...{C.RESET}")
    cmd_check()

# ============================================================
# check 命令
# ============================================================
def cmd_check():
    """检查当前 OpenClaw 环境完整性"""
    header("OpenClaw 环境检查")

    total_checks = 0
    passed = 0
    warnings = 0
    errors = 0

    def do_ok(msg):
        nonlocal total_checks, passed
        total_checks += 1
        passed += 1
        ok(msg)

    def do_warn(msg):
        nonlocal total_checks, warnings
        total_checks += 1
        warnings += 1
        warn(msg)

    def do_fail(msg):
        nonlocal total_checks, errors
        total_checks += 1
        errors += 1
        fail(msg)

    # ---- 1. 目录结构 ----
    print(f"\n  {C.BOLD}1. 目录结构{C.RESET}")

    if os.path.isdir(OPENCLAW_HOME):
        do_ok(f"OpenClaw 目录存在: {OPENCLAW_HOME}")
    else:
        do_fail(f"OpenClaw 目录不存在: {OPENCLAW_HOME}")
        print(f"\n  {C.RED}{C.BOLD}无法继续检查，基础目录缺失。{C.RESET}")
        _print_summary(total_checks, passed, warnings, errors)
        return

    # 子目录
    for subdir in ["workspace", "extensions"]:
        path = os.path.join(OPENCLAW_HOME, subdir)
        if os.path.isdir(path):
            do_ok(f"子目录存在: {subdir}/")
        else:
            do_warn(f"子目录不存在: {subdir}/（可选）")

    # ---- 2. 关键文件 ----
    print(f"\n  {C.BOLD}2. 关键文件{C.RESET}")

    for fname in KEY_FILES:
        fpath = os.path.join(WORKSPACE, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            do_ok(f"{fname} ({human_size(size)})")
        else:
            do_fail(f"{fname} 不存在")

    # ---- 3. Skills 目录 ----
    print(f"\n  {C.BOLD}3. Skills{C.RESET}")

    skills_dir = os.path.join(WORKSPACE, "skills")
    if os.path.isdir(skills_dir):
        skills = []
        broken_skills = []
        for name in sorted(os.listdir(skills_dir)):
            skill_md = os.path.join(skills_dir, name, "SKILL.md")
            if os.path.isfile(skill_md):
                skills.append(name)
            else:
                broken_skills.append(name)

        if skills:
            do_ok(f"找到 {len(skills)} 个 skill(s)")
            for s in skills:
                print(f"    {C.DIM}•{C.RESET} {s}")
        else:
            do_warn("skills/ 目录为空")

        if broken_skills:
            do_warn(f"{len(broken_skills)} 个 skill 缺少 SKILL.md")
            for s in broken_skills:
                print(f"    {C.YELLOW}•{C.RESET} {s}")
    else:
        do_warn("skills/ 目录不存在")

    # ---- 4. Python 环境 ----
    print(f"\n  {C.BOLD}4. Python 环境{C.RESET}")

    py_version = platform.python_version()
    py_ver_tuple = tuple(int(x) for x in py_version.split(".")[:2])
    if py_ver_tuple >= (3, 8):
        do_ok(f"Python {py_version}")
    elif py_ver_tuple >= (3, 6):
        do_warn(f"Python {py_version}（建议 3.8+）")
    else:
        do_fail(f"Python {py_version} 版本过低（需要 3.8+）")

    # 检查关键模块
    for module_name in ["json", "tarfile", "hashlib", "subprocess", "pathlib", "shutil"]:
        try:
            __import__(module_name)
            do_ok(f"模块可用: {module_name}")
        except ImportError:
            do_fail(f"模块缺失: {module_name}")

    # ---- 5. Node.js 环境 ----
    print(f"\n  {C.BOLD}5. Node.js 环境{C.RESET}")

    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            node_ver = result.stdout.strip()
            do_ok(f"Node.js {node_ver}")
        else:
            do_warn("Node.js 命令执行异常")
    except FileNotFoundError:
        do_warn("Node.js 未安装或不在 PATH 中")
    except subprocess.TimeoutExpired:
        do_warn("Node.js 命令超时")

    # 检查 openclaw 命令
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            oc_ver = result.stdout.strip()
            do_ok(f"OpenClaw CLI: {oc_ver}")
        else:
            do_warn("openclaw 命令执行异常")
    except FileNotFoundError:
        do_warn("openclaw CLI 未安装或不在 PATH 中")
    except subprocess.TimeoutExpired:
        do_warn("openclaw 命令超时")

    # ---- 6. 磁盘空间 ----
    print(f"\n  {C.BOLD}6. 磁盘空间{C.RESET}")

    try:
        usage = shutil.disk_usage(OPENCLAW_HOME)
        free_gb = usage.free / (1024**3)
        if free_gb >= 5:
            do_ok(f"可用空间: {human_size(usage.free)}")
        elif free_gb >= 1:
            do_warn(f"可用空间较少: {human_size(usage.free)}")
        else:
            do_fail(f"可用空间不足: {human_size(usage.free)}")
        print(f"    {C.DIM}总计: {human_size(usage.total)} | 已用: {human_size(usage.used)}{C.RESET}")
    except OSError as e:
        do_warn(f"无法检查磁盘空间: {e}")

    # ---- 汇总 ----
    _print_summary(total_checks, passed, warnings, errors)


def _print_summary(total, passed, warnings, errors):
    """打印检查汇总"""
    print(f"\n{'─'*50}")
    if errors == 0 and warnings == 0:
        print(f"  {C.GREEN}{C.BOLD}✔ 所有检查通过！({passed}/{total}){C.RESET}")
    elif errors == 0:
        print(f"  {C.YELLOW}{C.BOLD}⚠ 检查完成，有 {warnings} 个警告 ({passed} 通过 / {warnings} 警告){C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}✘ 检查完成，有 {errors} 个错误 ({passed} 通过 / {warnings} 警告 / {errors} 错误){C.RESET}")
    print()


# ============================================================
# info 命令
# ============================================================
def cmd_info(archive_path):
    """显示备份文件的 manifest 信息"""
    header("OpenClaw 备份信息")

    if not os.path.isfile(archive_path):
        fail(f"备份文件不存在: {archive_path}")
        sys.exit(1)

    # 验证 MD5
    md5_path = archive_path + ".md5"
    if os.path.isfile(md5_path):
        try:
            with open(md5_path, "r") as f:
                expected_md5 = f.read().split()[0]
            actual_md5 = md5sum(archive_path)
            if expected_md5 == actual_md5:
                ok(f"MD5 校验通过")
            else:
                fail(f"MD5 校验失败！期望 {expected_md5}，实际 {actual_md5}")
        except Exception as e:
            warn(f"MD5 校验出错: {e}")
    else:
        info("无 .md5 校验文件")

    # 读取 manifest
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            manifest_member = tar.extractfile("manifest.json")
            if manifest_member is None:
                fail("备份中未找到 manifest.json")
                sys.exit(1)
            manifest = json.loads(manifest_member.read().decode("utf-8"))
    except Exception as e:
        fail(f"读取备份失败: {e}")
        sys.exit(1)

    # 格式化输出
    print(f"\n  {C.BOLD}备份概要{C.RESET}")
    print(f"  {'─'*40}")
    print(f"  备份时间:      {manifest.get('backup_time', '未知')}")
    print(f"  源主机:        {manifest.get('hostname', '未知')}")
    print(f"  OpenClaw 版本: {manifest.get('openclaw_version', '未知')}")
    print(f"  文件总数:      {manifest.get('file_count', '?')}")
    print(f"  总大小:        {manifest.get('total_size_human', '?')}")

    # 平台信息
    plat = manifest.get("platform", {})
    if plat:
        print(f"\n  {C.BOLD}平台信息{C.RESET}")
        print(f"  {'─'*40}")
        print(f"  操作系统: {plat.get('system', '?')} {plat.get('release', '?')}")
        print(f"  架构:     {plat.get('machine', '?')}")
        print(f"  Python:   {plat.get('python', '?')}")

    # 排除模式
    excluded = manifest.get("excluded_patterns", [])
    if excluded:
        print(f"\n  {C.BOLD}排除模式{C.RESET}")
        print(f"  {'─'*40}")
        for pat in excluded:
            print(f"  • {pat}")

    # 文件分布
    files = manifest.get("files", [])
    if files:
        print(f"\n  {C.BOLD}文件分布{C.RESET}")
        print(f"  {'─'*40}")

        # 按顶级目录分组
        dirs = {}
        for f in files:
            top = Path(f["path"]).parts[0] if Path(f["path"]).parts else "other"
            if top not in dirs:
                dirs[top] = {"count": 0, "size": 0}
            dirs[top]["count"] += 1
            dirs[top]["size"] += f.get("size", 0)

        for d in sorted(dirs.keys()):
            info_item = dirs[d]
            print(f"  {d:25s} {info_item['count']:5d} 文件  {human_size(info_item['size']):>10s}")

        # 列出 skills
        skills = set()
        for f in files:
            parts = Path(f["path"]).parts
            if "skills" in parts:
                idx = parts.index("skills")
                if idx + 1 < len(parts):
                    skill_name = parts[idx + 1]
                    # 确保是 skill 目录名
                    if len(parts) > idx + 2:
                        skills.add(skill_name)

        if skills:
            print(f"\n  {C.BOLD}包含的 Skills ({len(skills)}){C.RESET}")
            print(f"  {'─'*40}")
            for s in sorted(skills):
                print(f"  • {s}")

    # 文件大小 Top 10
    if files:
        top_files = sorted(files, key=lambda x: x.get("size", 0), reverse=True)[:10]
        print(f"\n  {C.BOLD}最大文件 Top 10{C.RESET}")
        print(f"  {'─'*40}")
        for f in top_files:
            print(f"  {human_size(f.get('size', 0)):>10s}  {f['path']}")

    print()


# ============================================================
# 主入口
# ============================================================
def main():
    """主函数：解析命令行参数并路由到对应的命令"""
    if len(sys.argv) < 2:
        print(f"""
{C.BOLD}OpenClaw 迁移工具{C.RESET}

用法:
  python3 {sys.argv[0]} backup [output_dir]     备份 ~/.openclaw
  python3 {sys.argv[0]} restore <backup.tar.gz>  从备份恢复
  python3 {sys.argv[0]} check                    检查环境完整性
  python3 {sys.argv[0]} info <backup.tar.gz>     查看备份信息

示例:
  python3 {sys.argv[0]} backup
  python3 {sys.argv[0]} backup /tmp/backups
  python3 {sys.argv[0]} restore openclaw-backup_host_20260402_120000.tar.gz
  python3 {sys.argv[0]} check
  python3 {sys.argv[0]} info openclaw-backup_host_20260402_120000.tar.gz
""")
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "backup":
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_backup(output_dir)

    elif command == "restore":
        if len(sys.argv) < 3:
            fail("用法: python3 migrate.py restore <backup.tar.gz>")
            sys.exit(1)
        cmd_restore(sys.argv[2])

    elif command == "check":
        cmd_check()

    elif command == "info":
        if len(sys.argv) < 3:
            fail("用法: python3 migrate.py info <backup.tar.gz>")
            sys.exit(1)
        cmd_info(sys.argv[2])

    else:
        fail(f"未知命令: {command}")
        print(f"  支持的命令: backup, restore, check, info")
        sys.exit(1)


if __name__ == "__main__":
    main()
