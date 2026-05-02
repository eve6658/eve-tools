"""demo.py — Eve 工具统一框架演示"""
import os, sys, json, math, asyncio, time
from demo_tools import HelloTool, ReadFileTool as FileReaderTool, CalculatorTool, WriteFileTool
from tool_framework import ToolResult, ToolContext, ValidationResult, PermissionResult
from tool_registry import ToolRegistry
from skill_discovery import SkillDiscoverer
from memory_layered import LayeredMemory, MemoryLayer, LAYER_TTL, LAYER_PATHS
from history_compress import HistoryCompressor, Message
from session_persist import SessionManager


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_tool_result(result):
    status = "✅ 成功" if result.success else "❌ 失败"
    print(f"    状态: {status}")
    print(f"    摘要: {result.summary}")
    if result.error:
        print(f"    错误: {result.error}")
    if result.data:
        data_str = json.dumps(result.data, ensure_ascii=False, indent=6)
        if len(data_str) > 200:
            data_str = data_str[:200] + "..."
        print(f"    数据: {data_str}")

def print_tool_search_result(result):
    if result:
        print(f"    发现工具: {result}")
    else:
        print(f"    无新发现")

async def main():
    """主演示流程"""
    
    workspace = os.path.dirname(os.path.abspath(__file__))
    context = ToolContext(workspace=workspace, session_id="demo_session_001")
    
    # ==========================================
    # 第一部分：工具注册
    # ==========================================
    print_section("📦 第一部分：工具注册与注册表")
    
    registry = ToolRegistry()
    
    # 创建工具实例并注册
    hello = HelloTool()
    reader = FileReaderTool()
    calculator = CalculatorTool()
    writer = WriteFileTool()
    
    registry.register(hello)
    registry.register(reader)
    registry.register(calculator)
    registry.register(writer)
    
    print(f"  注册了 {len(registry)} 个工具")
    print(f"\n  工具列表:")
    for tool_info in registry.list_tools():
        readonly = "📖" if tool_info["is_read_only"] else "✏️"
        destructive = " 💥" if tool_info["is_destructive"] else ""
        print(f"    {readonly} {tool_info['name']}{destructive}: {tool_info['description']}")
    
    # ==========================================
    # 第二部分：工具查找
    # ==========================================
    print_section("🔍 第二部分：工具查找")
    
    # 按名称查找
    tool = registry.get("hello")
    print(f"  按名称查找 'hello': {tool.name if tool else '未找到'}")
    
    # 按别名查找
    tool = registry.get("cat")
    print(f"  按别名查找 'cat': {tool.name if tool else '未找到'}")
    
    # 关键词搜索
    tools = registry.search("file")
    print(f"  关键词搜索 'file': {[t.name for t in tools]}")
    
    # ==========================================
    # 第三部分：工具执行
    # ==========================================
    print_section("⚡ 第三部分：工具执行")
    
    # 1. Hello 工具
    print("\n  --- HelloTool ---")
    result = hello.execute({"name": "Adam"}, context)
    print_tool_result(result)
    
    # 2. 计算器工具
    print("\n  --- CalculatorTool ---")
    result = calculator.execute({"expression": "2 + 3 * 4 ^ 2"}, context)
    print_tool_result(result)
    
    # 3. 参数验证
    print("\n  --- 验证演示 ---")
    validation = calculator.validate({"expression": ""})
    print(f"  空表达式验证: {'通过' if validation else '失败 - ' + ', '.join(validation.errors)}")
    
    validation = calculator.validate({"expression": "1+1"})
    print(f"  有效表达式验证: {'通过' if validation else '失败'}")
    
    # 4. 权限检查
    print("\n  --- 权限检查 ---")
    perm = hello.check_permissions({}, context)
    print(f"  HelloTool 权限: {perm.value}")
    
    perm = writer.check_permissions({}, context)
    print(f"  WriteFileTool 权限: {perm.value} (破坏性操作，需用户确认)")
    
    # ==========================================
    # 第四部分：技能自动发现
    # ==========================================
    print_section("🔎 第四部分：技能自动发现")
    
    discoverer = SkillDiscoverer(registry)
    
    test_inputs = [
        "帮我读取一个文件",
        "今天天气怎么样",
        "计算 15 * 8",
        "写入一个新的文件",
        "再来一个问候",
    ]
    
    for user_input in test_inputs:
        found = discoverer.discover_sync(user_input)
        found_names = [t.name for t in found]
        print(f"\n  输入: \"{user_input}\"")
        print(f"  关键词: {discoverer._extract_keywords(user_input)}")
        print(f"  发现工具: {found_names if found_names else '无新发现'}")
    
    print(f"\n  累计已发现: {discoverer.get_discovered()}")
    
    # 重复查询（应该跳过）
    print("\n  --- 去重测试 ---")
    again = discoverer.discover_sync("帮我读取文件内容")
    print(f"  重复查询发现: {[t.name for t in again] if again else '已发现过，跳过'}")
    
    # ==========================================
    # 第五部分：分层记忆（演示）
    # ==========================================
    print_section("🧠 第五部分：分层记忆系统")
    
    memory = LayeredMemory(workspace)
    
    print("  记忆层级:")
    for layer in MemoryLayer:
        ttl_val = LAYER_TTL[layer]
        ttl_str = "∞" if ttl_val == float('inf') else f"{ttl_val}s"
        paths = LAYER_PATHS[layer]
        print(f"    {layer.name:12s} (TTL={ttl_str:5s}): {paths}")
    
    # 保存记忆
    print("\n  保存记忆到 DAILY 层...")
    today = time.strftime("%Y-%m-%d")
    ok = await memory.save("Eve 框架演示完成！", MemoryLayer.DAILY, today)
    print(f"  保存结果: {'✅ 成功' if ok else '❌ 失败'}")
    
    # 追加记忆
    print("\n  追加记忆...")
    ok = await memory.append("验证了工具注册、发现、执行等模块", MemoryLayer.DAILY, today)
    print(f"  追加结果: {'✅ 成功' if ok else '❌ 失败'}")
    
    stats = memory.get_stats()
    print(f"\n  记忆统计: {stats}")
    
    # ==========================================
    # 第六部分：历史压缩
    # ==========================================
    print_section("🗜️ 第六部分：历史压缩")
    
    compressor = HistoryCompressor()
    
    # 构造模拟对话历史
    history = [
        Message.system("你是 Eve，一个 AI 助手。"),
        Message.user("帮我分析一下这份报告"),
        Message.assistant("好的，让我先读取文件"),
        Message.tool("文件内容：这是一份2024年Q1的销售报告...", name="read_file"),
        Message.user("总结一下要点"),
        Message.assistant("根据报告，主要要点是..."),
        Message.user("画个图表"),
        Message.assistant("好的，让我生成图表"),
        Message.tool("图表已生成", name="chart"),
        Message.user("把结果保存下来"),
        Message.assistant("好的，我来保存"),
        Message.tool("已保存到 report_summary.md", name="write_file"),
        Message.user("谢谢！"),
    ]
    
    print(f"\n  原始消息数: {len(history)}")
    
    # 估算 token
    tokens = compressor.estimate_tokens(history)
    print(f"  估算 token: {tokens}")
    
    # 是否需要压缩
    need_compress = compressor.should_compress(history, threshold=100)
    print(f"  需要压缩 (阈值=100): {'是' if need_compress else '否'}")
    
    # microcompact 演示
    print("\n  --- microcompact 演示 ---")
    long_text = "这是一段很长的工具结果。\n" * 100
    compressed = compressor.microcompact(long_text, max_chars=100)
    print(f"  原始长度: {len(long_text)} 字符")
    print(f"  压缩后: {len(compressed)} 字符")
    print(f"  压缩结果:\n{compressed}")
    
    # snip 演示
    print("\n  --- snip 演示 ---")
    snipped = compressor.snip(history, keep_last_n=3)
    print(f"  裁剪后消息数: {len(snipped)}")
    for i, msg in enumerate(snipped):
        content_preview = msg.content[:60].replace("\n", " ")
        print(f"    [{i}] {msg.role}: {content_preview}")
    
    # ==========================================
    # 第七部分：会话持久化
    # ==========================================
    print_section("💾 第七部分：会话持久化")
    
    sessions_dir = os.path.join(workspace, ".demo_sessions")
    session_mgr = SessionManager(sessions_dir)
    
    # 保存会话
    demo_messages = [
        {"role": "system", "content": "你是 Eve"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！我是 Eve 🐾"},
    ]
    
    print("\n  保存演示会话...")
    ok = session_mgr.save("demo_session", demo_messages, {"model": "demo", "version": "1.0"})
    print(f"  保存结果: {'✅ 成功' if ok else '❌ 失败'}")
    
    # 加载会话
    loaded = session_mgr.load("demo_session")
    if loaded:
        print(f"\n  加载会话: {loaded.session_id}")
        print(f"  消息数: {len(loaded.messages)}")
        print(f"  元数据: {loaded.metadata}")
    
    # 列出会话
    sessions = session_mgr.list_sessions()
    print(f"\n  会话列表 ({len(sessions)} 个):")
    for s in sessions:
        print(f"    - {s['session_id']}: {s['message_count']} 条消息")
    
    # 统计
    stats = session_mgr.get_stats()
    print(f"\n  存储统计: {stats}")
    
    # ==========================================
    # 总结
    # ==========================================
    print_section("🎉 演示完成！")
    
    print("""
  ✅ 工具注册表 — 4 个工具注册，支持名称/别名/关键词查找
  ✅ 工具执行 — 支持参数验证、权限检查、结果摘要
  ✅ 技能发现 — 基于关键词的自动技能匹配，支持去重
  ✅ 分层记忆 — CORE/LONG_TERM/DAILY/PROJECT/SKILL 五层
  ✅ 历史压缩 — microcompact + snip + compact 三级压缩
  ✅ 会话持久化 — 保存/加载/列表/清理
  
  所有模块均基于 Claude Code 架构设计，包含详细中文注释。
  文件位置: /home/adam/.openclaw/workspace/eve-evolution/
    """)


if __name__ == "__main__":
    asyncio.run(main())
