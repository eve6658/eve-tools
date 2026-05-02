# 翻译优化脚本使用说明

本目录提供两个并行优化脚本，用于批量优化章节翻译。

## 脚本对比

| 脚本 | 语言 | 依赖 | 特点 |
|------|------|------|------|
| `optimize_translations.py` | Python | Python 3.6+ | 推荐使用，无需额外依赖 |
| `optimize_translations.sh` | Bash | GNU Parallel, coreutils | 需要安装额外工具 |

## 推荐使用: Python 版本

### 快速开始

```bash
# 直接运行
./optimize_translations.py
```

### 功能特点

- 自动跳过索引、术语表等非章节文件
- 可配置的并行数 (默认 4)
- 可配置的超时时间 (默认 10 分钟)
- 实时显示处理进度
- 完成后显示成功/失败统计

### 配置修改

编辑脚本开头的配置部分:

```python
MAX_WORKERS = 4      # 最大并行任务数
TIMEOUT = 600         # 超时时间(秒)
```

### 跳过的文件

脚本默认跳过以下文件:
- Index of Terms.md
- Glossary.md
- README.md
- Agentic Design Patterns.md
- Frequently Asked Questions_ Agentic Design Patterns.md
- Conclusion.md

## Bash 版本 (备选)

### 依赖安装

```bash
# macOS
brew install parallel coreutils

# Ubuntu/Debian
sudo apt install parallel
```

### 运行

```bash
./optimize_translations.sh
```

## 使用流程

1. **确认环境**
   - 确保 `opencode` 命令可用
   - 确保在项目根目录下运行

2. **运行脚本**
   ```bash
   ./optimize_translations.py
   ```

3. **确认执行**
   - 脚本会显示将要处理的章节列表
   - 输入 `y` 确认开始

4. **等待完成**
   - 脚本会并行处理多个章节
   - 实时显示处理状态

5. **查看结果**
   - 完成后显示成功/失败统计
   - 失败的章节会列出

## 注意事项

- 每个任务默认超时时间为 10 分钟
- 建议先从较小的并行数开始测试 (2-4)
- 如遇问题，可以单独运行失败的章节
- 脚本不会修改原文件，而是通过 opencode 进行修改

## 单独处理某个章节

如果需要单独处理某个章节，可以直接运行:

```bash
opencode run "ulw 优化下 Chapter 1_ Prompt Chaining.md 章节的翻译，尤其是一些晦涩、表述不畅的部分，但不要改变原意"
```
