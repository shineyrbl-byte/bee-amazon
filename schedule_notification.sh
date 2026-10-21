#!/bin/bash
# Schedule a daily morning notification on macOS.
#   bash schedule_notification.sh        -> every day at 9:00
#   bash schedule_notification.sh 8      -> every day at 8:00
#   bash schedule_notification.sh --remove
PLIST="$HOME/Library/LaunchAgents/com.talktotask.morning.plist"

if [ "$1" = "--remove" ]; then
  launchctl unload "$PLIST" 2>/dev/null
  rm -f "$PLIST"
  echo "Removed the morning notification."
  exit 0
fi

HOUR=${1:-9}
DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON=$(command -v python3)
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.talktotask.morning</string>
  <key>ProgramArguments</key>
  <array><string>$PYTHON</string><string>$DIR/notify.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/talk_to_task.log</string>
  <key>StandardErrorPath</key><string>/tmp/talk_to_task.log</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST"
echo "Scheduled: every day at $HOUR:00 using $PYTHON"
echo "Test it now with:  python3 notify.py"