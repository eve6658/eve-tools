import os
import time
import subprocess

# 监控目录
WATCH_DIR = os.path.expanduser("~/data/raw_screenshots/")
# 识别后的文本存放在此，供 OpenClaw 读取
OUTPUT_FILE = os.path.expanduser("~/data/ocr_result.txt")

def process_latest_image():
    files = [os.path.join(WATCH_DIR, f) for f in os.listdir(WATCH_DIR) if f.endswith(('.jpg', '.png'))]
    if not files:
        return
    
    # 获取最新的一张图
    latest_img = max(files, key=os.path.getmtime)
    
    # 调用你写好的精简版 OCR
    print(f"🚀 正在识别最新截图: {latest_img}")
    cmd = f"python3 ~/skills/local-ocr/ocr_logic.py {latest_img}"
    result = subprocess.check_output(cmd, shell=True).decode('utf-8')
    
    # 将识别出的纯文本写入文件，供模型分析
    with open(OUTPUT_FILE, "w") as f:
        f.write(result)
    print(f"✅ 识别完成，结果已同步至 {OUTPUT_FILE}")

if __name__ == "__main__":
    # 简单的轮询监听，也可以集成进 OpenClaw 的 API
    last_mtime = 0
    while True:
        current_mtime = os.path.getmtime(WATCH_DIR)
        if current_mtime > last_mtime:
            process_latest_image()
            last_mtime = current_mtime
        time.sleep(1)

