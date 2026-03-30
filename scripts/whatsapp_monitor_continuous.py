#!/usr/bin/env python3
"""Continuous monitor for incoming WhatsApp messages."""

import time
import json
import urllib.request
from pathlib import Path
from datetime import datetime

VAULT_PATH = Path("./AI_Employee_Vault/Needs_Action").resolve()

print("="*60)
print("📱 WHATSAPP MESSAGE MONITOR - CONTINUOUS")
print("="*60)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Webhook: http://localhost:8089")
print(f"Watching: {VAULT_PATH}")
print()
print("⏳ Waiting for incoming WhatsApp messages...")
print("   Send a message to: +1 (555) 137-8016")
print("="*60)
print()

# Track existing files
existing = set()
if VAULT_PATH.exists():
    existing = set(f.name for f in VAULT_PATH.glob("WHATSAPP_*.md"))

last_check = 0
try:
    check_num = 0
    while True:
        check_num += 1
        
        # Check webhook stats
        try:
            with urllib.request.urlopen("http://localhost:8089/stats", timeout=2) as r:
                data = json.loads(r.read().decode())
                received = data.get("messages_received_total", 0)
                processed = data.get("messages_processed_session", 0)
                
                if received > last_check:
                    print()
                    print("🎉 " + "="*50)
                    print(f"NEW MESSAGE RECEIVED at {datetime.now().strftime('%H:%M:%S')}")
                    print("="*50)
                    print(f"  Total messages: {received}")
                    print(f"  Session processed: {processed}")
                    print("="*50)
                    last_check = received
        except Exception as e:
            print(f"[Error checking stats: {e}]")
        
        # Check for new files
        if VAULT_PATH.exists():
            current = set(f.name for f in VAULT_PATH.glob("WHATSAPP_*.md"))
            new_files = current - existing
            
            if new_files:
                print()
                print("📩 " + "="*50)
                print(f"NEW TASK FILE CREATED at {datetime.now().strftime('%H:%M:%S')}")
                print("="*50)
                
                for filename in sorted(new_files):
                    print(f"\n📄 File: {filename}")
                    
                    filepath = VAULT_PATH / filename
                    content = filepath.read_text(encoding="utf-8")
                    
                    # Extract key info
                    for line in content.split("\n"):
                        if line.startswith("from_name:"):
                            print(f"   From: {line.split(':', 1)[1].strip()}")
                        elif line.startswith("from_number:"):
                            print(f"   Number: {line.split(':', 1)[1].strip()}")
                        elif line.startswith("priority:"):
                            print(f"   Priority: {line.split(':', 1)[1].strip()}")
                    
                    # Show message preview
                    if "**Message:**" in content:
                        msg_start = content.find("**Message:**") + len("**Message:**")
                        msg_end = content.find("##", msg_start)
                        if msg_end == -1:
                            msg_end = msg_start + 200
                        msg_text = content[msg_start:msg_end].strip()
                        print(f"   Text: {msg_text[:150]}...")
                
                print()
                print("="*50)
                existing = current
        
        # Status update every 10 checks
        if check_num % 10 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Still watching... (Check #{check_num})")
        
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\n\n⏹️  Monitor stopped by user.")
    print(f"Total checks: {check_num}")
