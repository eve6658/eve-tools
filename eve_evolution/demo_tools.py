"""demo_tools.py — 演示用工具定义"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tool_framework import EveTool, ToolResult, ValidationResult

class HelloTool(EveTool):
    """打招呼工具"""
    def __init__(self):
        super().__init__(name="hello", description="向用户打招呼",
                        aliases=["hi", "greet"], search_hint="hello greeting",
                        category="demo")
    def execute(self, args, context):
        name = args.get("name", "世界")
        return ToolResult.ok(data={"greeting": f"你好，{name}！🐾"}, summary=f"生成问候")

class ReadFileTool(EveTool):
    """读取文件"""
    def __init__(self):
        super().__init__(name="read_file", description="读取文本文件内容",
                        aliases=["cat", "read"], category="demo")
    def execute(self, args, context):
        path = args.get("path", "")
        if not path: return ToolResult(False, error="path 不能为空")
        ws = getattr(context, "workspace", ".") if context else "."
        if not os.path.isabs(path): path = os.path.join(ws, path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return ToolResult(True, data={"content": content}, summary=f"读取 {path} ({len(content)} 字符)")
        except FileNotFoundError:
            return ToolResult(False, error=f"文件不存在: {path}")

class CalculatorTool(EveTool):
    """数学计算"""
    def __init__(self):
        super().__init__(name="calculator", description="执行数学计算",
                        aliases=["calc", "math"], category="demo")
    def execute(self, args, context):
        expr = args.get("expression", "")
        if not expr: return ToolResult(False, error="expression 不能为空")
        try:
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            allowed_names["abs"] = abs; allowed_names["round"] = round
            result = eval(expr, {"__builtins__": {}}, allowed_names)
            return ToolResult(True, data={"expression": expr, "result": result},
                            summary=f"{expr} = {result}")
        except Exception as e:
            return ToolResult(False, error=f"计算错误: {e}")

class WriteFileTool(EveTool):
    """写入文件"""
    def __init__(self):
        super().__init__(name="write_file", description="写入内容到文件",
                        aliases=["write", "save"], is_read_only=False,
                        is_destructive=True, permission_level="ask", category="demo")
    def execute(self, args, context):
        path = args.get("path", "")
        content = args.get("content", "")
        if not path: return ToolResult(False, error="path 不能为空")
        ws = getattr(context, "workspace", ".") if context else "."
        if not os.path.isabs(path): path = os.path.join(ws, path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(True, data={"path": path}, summary=f"写入 {path} ({len(content)} 字符)")

__all__ = ["HelloTool", "ReadFileTool", "CalculatorTool", "WriteFileTool"]
