#!/usr/bin/env python3
"""Morning notification: summarizes saved promises that are overdue, due today or due tomorrow.

python notify.py               # show a desktop notification (macOS) and print it
python notify.py --print-only  # just print
"""

import sys

import talk_to_task as t

if __name__ == "__main__":
    title, body = t.morning_message(t.load_store())
    print(f"{title}\n{body}")
    if "--print-only" not in sys.argv and not t.send_notification(title, body):
        print("(Could not show a desktop notification; this works on macOS only.)")
