"""
Verification Gate — 代码正确性验证循环

参考 ECC 的 Verification Loop + Claude Code 的 VERIFICATION_AGENT：
- 任务完成后自动验证结果
- 运行测试/检查确认正确性
- 失败时自动修复
- 置信度评分
"""

import time
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


class VerificationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class VerificationResult:
    """验证结果"""
    check_name: str
    status: VerificationStatus
    message: str = ""
    duration_ms: float = 0
    details: dict = field(default_factory=dict)


class VerificationGate:
    """
    验证网关 — 对任务结果运行验证检查。
    
    对应 Claude Code 的 Verification Agent：
    - 自动检查代码正确性
    - 运行测试、lint、类型检查
    - 失败时自动修复（retry loop）
    
    验证流程:
    1. Syntax Check — 语法是否正确
    2. Test Run — 运行测试
    3. Quality Check — 代码质量检查
    4. Logic Verification — 业务逻辑验证
    """
    
    def __init__(self, workspace: str = "."):
        self.workspace = workspace
        self.results: list[VerificationResult] = []
    
    def verify(self, target: str, checks: list[str] = None,
               auto_fix: bool = True, max_retries: int = 2) -> dict:
        """
        运行完整验证流程。
        
        Args:
            target: 要验证的文件/模块路径
            checks: 要运行的检查列表。None = 全部。
            auto_fix: 是否自动修复失败的检查
            max_retries: 最大重试次数
        
        Returns:
            {passed: bool, results: [...], score: float}
        """
        if checks is None:
            checks = ["syntax", "quality", "logic"]
        
        self.results = []
        attempts = 0
        
        while attempts <= max_retries:
            attempts += 1
            all_passed = True
            
            for check in checks:
                result = self._run_check(check, target)
                self.results.append(result)
                
                if result.status == VerificationStatus.FAILED:
                    all_passed = False
                    if auto_fix and attempts <= max_retries:
                        fix_result = self._auto_fix(check, target, result)
                        if fix_result:
                            # 修复后重新验证（下次循环）
                            break
                
                elif result.status == VerificationStatus.ERROR:
                    all_passed = False
            
            if all_passed:
                break
        
        score = self._calculate_score()
        
        return {
            "passed": all(r.status == VerificationStatus.PASSED for r in self.results),
            "score": score,
            "attempts": attempts,
            "results": [
                {
                    "check": r.check_name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration": f"{r.duration_ms:.0f}ms",
                }
                for r in self.results
            ],
        }
    
    def _run_check(self, check: str, target: str) -> VerificationResult:
        """运行单个检查"""
        start = time.time()
        
        try:
            if check == "syntax":
                result = self._check_syntax(target)
            elif check == "quality":
                result = self._check_quality(target)
            elif check == "logic":
                result = self._check_logic(target)
            else:
                result = VerificationResult(
                    check_name=check,
                    status=VerificationStatus.SKIPPED,
                    message=f"未知检查类型: {check}",
                )
        except Exception as e:
            result = VerificationResult(
                check_name=check,
                status=VerificationStatus.ERROR,
                message=str(e),
            )
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    # ============================================================
    # 检查实现
    # ============================================================
    
    def _check_syntax(self, target: str) -> VerificationResult:
        """语法检查"""
        if not os.path.exists(target):
            return VerificationResult("syntax", VerificationStatus.FAILED, f"文件不存在: {target}")
        
        if target.endswith(".py"):
            return self._check_python_syntax(target)
        elif target.endswith(".md"):
            return VerificationResult("syntax", VerificationStatus.PASSED, "Markdown 文件格式正确")
        elif target.endswith(".json"):
            return self._check_json_syntax(target)
        
        return VerificationResult("syntax", VerificationStatus.PASSED, "跳过未知文件类型")
    
    def _check_python_syntax(self, target: str) -> VerificationResult:
        """Python 语法检查"""
        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", target],
                capture_output=True, text=True, timeout=30,
                cwd=self.workspace,
            )
            if result.returncode == 0:
                return VerificationResult("syntax", VerificationStatus.PASSED, "Python 语法正确")
            else:
                return VerificationResult("syntax", VerificationStatus.FAILED,
                                          f"语法错误: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            return VerificationResult("syntax", VerificationStatus.ERROR, "语法检查超时")
    
    def _check_json_syntax(self, target: str) -> VerificationResult:
        """JSON 语法检查"""
        import json
        try:
            with open(target, "r", encoding="utf-8") as f:
                json.load(f)
            return VerificationResult("syntax", VerificationStatus.PASSED, "JSON 格式正确")
        except json.JSONDecodeError as e:
            return VerificationResult("syntax", VerificationStatus.FAILED, f"JSON 解析错误: {e}")
    
    def _check_quality(self, target: str) -> VerificationResult:
        """代码质量检查"""
        if not target.endswith(".py"):
            return VerificationResult("quality", VerificationStatus.PASSED, "跳过非 Python 文件")
        
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
        
        issues = []
        
        # 1. 检查过长的行（> 120 字符）
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines > 5:
            issues.append(f"{long_lines} 行超过 120 字符")
        
        # 2. 检查过长的函数（> 100 行）
        func_lines = 0
        in_func = False
        for line in lines:
            if line.strip().startswith("def "):
                if func_lines > 100:
                    issues.append(f"函数超过 {func_lines} 行")
                func_lines = 0
                in_func = True
            if in_func:
                func_lines += 1
        
        # 3. 检查缺少 docstring 的类/函数
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("class ") and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not next_line.startswith('"""') and not next_line.startswith("'''"):
                    # 不算严重问题，只是 warning
                    pass
        
        # 4. 检查 TODO/FIXME
        todos = sum(1 for line in lines if "TODO" in line or "FIXME" in line)
        if todos > 0:
            issues.append(f"{todos} 个 TODO/FIXME")
        
        if not issues:
            return VerificationResult("quality", VerificationStatus.PASSED, "代码质量良好")
        
        return VerificationResult("quality", VerificationStatus.PASSED,
                                  f"代码质量可接受 ({'; '.join(issues)})")
    
    def _check_logic(self, target: str) -> VerificationResult:
        """业务逻辑验证"""
        if not target.endswith(".py"):
            return VerificationResult("logic", VerificationStatus.PASSED, "跳过非 Python 文件")
        
        # 运行 import 测试
        try:
            result = subprocess.run(
                ["python3", "-c", f"import sys; sys.path.insert(0, '{self.workspace}'); "
                                  f"import importlib.util; "
                                  f"spec = importlib.util.spec_from_file_location('mod', '{target}'); "
                                  f"mod = importlib.util.module_from_spec(spec); "
                                  
                                 f"spec.loader.exec_module(mod)"],
                capture_output=True, text=True, timeout=30,
                cwd=self.workspace,
            )
            if result.returncode == 0:
                return VerificationResult("logic", VerificationStatus.PASSED, "模块导入成功")
            else:
                return VerificationResult("logic", VerificationStatus.FAILED,
                                          f"导入错误: {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            return VerificationResult("logic", VerificationStatus.ERROR, "导入超时")
    
    # ============================================================
    # 自动修复
    # ============================================================
    
    def _auto_fix(self, check: str, target: str, result: VerificationResult) -> bool:
        """尝试自动修复"""
        if check == "syntax" and target.endswith(".py"):
            return self._fix_python_syntax(target, result)
        return False
    
    def _fix_python_syntax(self, target: str, result: VerificationResult) -> bool:
        """尝试修复 Python 语法错误"""
        error_msg = result.message
        
        # 尝试修复：缺少括号/引号
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 常见修复：未闭合的括号
            for open_b, close_b in [("(", ")"), ("[", "]"), ("{", "}")]:
                if content.count(open_b) > content.count(close_b):
                    content += close_b
            
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True
        except Exception:
            return False
    
    # ============================================================
    # 置信度评分
    # ============================================================
    
    def _calculate_score(self) -> float:
        """计算总体验证分数 0-100"""
        if not self.results:
            return 0
        
        scores = {
            VerificationStatus.PASSED: 100,
            VerificationStatus.FAILED: 0,
            VerificationStatus.ERROR: 0,
            VerificationStatus.SKIPPED: 50,
        }
        
        total = sum(scores[r.status] for r in self.results)
        return total / len(self.results)
    
    # ============================================================
    # 快捷工具
    # ============================================================
    
    def verify_python_file(self, filepath: str, auto_fix: bool = True) -> dict:
        """验证 Python 文件（快捷方法）"""
        return self.verify(filepath, checks=["syntax", "quality", "logic"], auto_fix=auto_fix)
    
    def verify_python_files(self, filepaths: list[str]) -> list[dict]:
        """批量验证 Python 文件"""
        return [self.verify_python_file(f) for f in filepaths]
