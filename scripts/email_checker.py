#!/usr/bin/env python3
"""
QQ邮箱检查器
用法: python3 scripts/email_checker.py [n]
  n: 检查最近n封邮件（默认5）
"""
import imaplib, email, json, sys
from email.header import decode_header
from datetime import datetime

IMAP_SERVER = 'imap.qq.com'
IMAP_PORT = 993
EMAIL = '16082177@qq.com'
AUTH_CODE = 'lyjnifzctfkzcaaf'
STATE_FILE = '/home/adam/.openclaw/workspace/scripts/email_state.json'

def get_last_read():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f).get('last_read_id', 0)
    except:
        return 0

def set_last_read(msg_id):
    with open(STATE_FILE, 'w') as f:
        json.dump({'last_read_id': msg_id, 'updated': datetime.now().isoformat()}, f)

def check_new_emails(count=10):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL, AUTH_CODE)
    mail.select('INBOX')
    
    status, messages = mail.search(None, 'ALL')
    all_nums = messages[0].split() if messages[0] else []
    total = len(all_nums)
    
    if total == 0:
        print("收件箱为空")
        return []
    
    last_read = get_last_read()
    # 取最近count封
    fetch_nums = all_nums[-count:]
    results = []
    
    for num in fetch_nums:
        num_int = int(num)
        if num_int <= last_read:
            continue
        
        status, data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        
        subject_parts = decode_header(msg['Subject'] or '(无主题)')
        subject = ''
        for part, enc in subject_parts:
            if isinstance(part, bytes):
                subject += part.decode(enc or 'utf-8', errors='replace')
            else:
                subject += part
        
        # 提取正文
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='replace')
                        break
                elif ct == 'text/html' and not body:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='replace')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='replace')
        
        results.append({
            'id': num_int,
            'from': msg['From'] or '',
            'subject': subject,
            'date': msg['Date'] or '',
            'body': body[:2000]  # 限制长度
        })
    
    # 更新已读状态
    if fetch_nums:
        set_last_read(int(fetch_nums[-1]))
    
    mail.logout()
    return results

if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    emails = check_new_emails(n)
    if not emails:
        print("没有新邮件")
    else:
        print(f"新邮件 ({len(emails)}封):")
        print("="*60)
        for e in emails:
            print(f"\n📧 [{e['id']}] {e['date'][:20]}")
            print(f"   From: {e['from'][:50]}")
            print(f"   Subject: {e['subject'][:80]}")
            if e['body']:
                body_preview = e['body'].replace('\n', ' ')[:200]
                print(f"   正文: {body_preview}...")
            print("-"*60)
