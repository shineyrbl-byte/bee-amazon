#!/usr/bin/env python3
"""Talk-to-Task core: read Bee conversations, extract commitments with Claude on Amazon Bedrock.

CLI usage:
    python talk_to_task.py          # live Bee data (runs `bee now --json`)
    python talk_to_task.py --demo   # built-in sample data
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys

import boto3

# Set these in your terminal (see README): the Bedrock inference profile ID and region.
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
USER_NAME = os.environ.get("USER_NAME", "Avisha")  # the speaker name Bee shows for you
CONTACTS = os.environ.get(
    "CONTACTS", ""
)  # optional: "Priya, Rahul, Meera" to fix misheard names

DEMO_CONVERSATIONS = [
    {
        "id": "demo-1",
        "title": "Planning the weekend",
        "start": "2026-10-21 10:00",
        "text": (
            "Alex: Can you send me the project report?\n"
            f"{USER_NAME}: Sure, I'll send you the report by Friday.\n"
            f"{USER_NAME}: Also remind me to call Rahul about the venue tomorrow morning.\n"
            "Priya: We should book the venue soon.\n"
            f"{USER_NAME}: I'll check prices and message you on Monday."
        ),
    }
]

PROMPT = """Today is {today} ({weekday}). Below is a transcript of conversations the user ("{user}") had.
Speech-to-text may contain small errors; use context to fix obvious ones.
{contacts_line}Bee often cannot identify the user's voice and labels it "Unknown". Treat "Unknown" lines as the user speaking unless the context clearly shows it is someone else.
Find every commitment the USER ("{user}") made or was asked to do. Ignore things other people promised.
Return ONLY a JSON array (no markdown fences). Each item must have:
  "task": short action phrase,
  "person": who it involves (or null),
  "due": ISO date YYYY-MM-DD (resolve words like "Friday" using today's date) or null,
  "confidence": number 0-1,
  "draft_message": a short, friendly follow-up message to that person (or null if no person is named).
If there are no commitments, return [].

Transcript:
{transcript}
"""


def build_transcript(conversation: dict) -> str:
    """Flatten one conversation from `bee now --json` into 'Speaker: text' lines, in time order."""
    utterances = []
    for transcription in conversation.get("transcriptions", []):
        utterances.extend(transcription.get("utterances", []))
    utterances.sort(key=lambda u: u.get("spoken_at", 0))
    speakers = {u.get("speaker", "Unknown") for u in utterances}
    # If Bee could not identify anyone, assume it is the user talking (e.g. a solo recording).
    solo_unknown = speakers <= {"Unknown"}
    lines = []
    for u in utterances:
        speaker = USER_NAME if solo_unknown else u.get("speaker", "Unknown")
        lines.append(f"{speaker}: {u.get('text', '')}")
    return "\n".join(lines)


def fetch_conversations(demo: bool = False, hours: float | None = None) -> list[dict]:
    """Return [{'id', 'title', 'start', 'text'}, ...]. Only transcript text is kept (no location etc.)."""
    if demo:
        return DEMO_CONVERSATIONS
    result = subprocess.run(
        ["bee", "now", "--json"], capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    conversations = []
    cutoff_ms = (
        (datetime.datetime.now().timestamp() - hours * 3600) * 1000 if hours else None
    )
    for c in data.get("conversations", []):
        start_ms = c.get("start_time")
        if cutoff_ms and start_ms and start_ms < cutoff_ms:
            continue
        start = (
            datetime.datetime.fromtimestamp(start_ms / 1000).strftime("%Y-%m-%d %H:%M")
            if start_ms
            else ""
        )
        conversations.append(
            {
                "id": c.get("id"),
                "title": c.get("short_summary") or "Conversation",
                "start": start,
                "text": build_transcript(c),
            }
        )
    return conversations


def extract_tasks(conversations: list[dict], contacts: str = "") -> list[dict]:
    if not conversations:
        return []
    transcript = "\n\n".join(
        f"[{c['start']}] {c['title']}\n{c['text']}" for c in conversations
    )
    today = datetime.date.today()
    contacts = contacts or CONTACTS
    contacts_line = (
        f"Known contacts: {contacts}. Speech-to-text often mishears names; if a name sounds like "
        "a known contact, use the known contact's spelling.\n"
        if contacts.strip()
        else ""
    )
    prompt = PROMPT.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
        user=USER_NAME,
        contacts_line=contacts_line,
        transcript=transcript,
    )
    client = boto3.client("bedrock-runtime", region_name=REGION)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 2000, "temperature": 0},
    )
    text = response["output"]["message"]["content"][0]["text"]
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    return json.loads(text[start : end + 1])


def due_bucket(due: str | None) -> str:
    """Group a task by due date: Overdue / Today / Tomorrow / Later / No date."""
    if not due:
        return "No date"
    try:
        d = datetime.date.fromisoformat(due)
    except ValueError:
        return "No date"
    delta = (d - datetime.date.today()).days
    if delta < 0:
        return "Overdue"
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return "Later"


def _ics_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _ics_fold(line: str, width: int = 60) -> list[str]:
    """Fold long lines as the iCalendar spec requires (continuation lines start with a space)."""
    parts = [line[:width]]
    parts += [" " + line[i : i + width - 1] for i in range(width, len(line), width - 1)]
    return parts


def tasks_to_ics(tasks: list[dict]) -> str:
    """Build an .ics file with one all-day event per task that has a valid due date."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Talk-to-Task//EN",
        "CALSCALE:GREGORIAN",
    ]
    for t in tasks:
        try:
            due = datetime.date.fromisoformat(t.get("due") or "")
        except ValueError:
            continue
        summary = t["task"] + (f" ({t['person']})" if t.get("person") else "")
        uid = hashlib.md5(f"{t['task']}{due}".encode()).hexdigest() + "@talk-to-task"
        event = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(due + datetime.timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{_ics_escape(summary)}",
        ]
        if t.get("draft_message"):
            event.append(
                f"DESCRIPTION:{_ics_escape('Draft message: ' + t['draft_message'])}"
            )
        event.append("END:VEVENT")
        for line in event:
            lines.extend(_ics_fold(line))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def write_markdown(tasks: list[dict], path: str = "tasks.md") -> None:
    lines = [f"# What I promised ({datetime.date.today().isoformat()})", ""]
    for t in sorted(tasks, key=lambda x: x.get("due") or "9999"):
        lines.append(
            f"- [ ] **{t['task']}** (with {t.get('person') or 'n/a'}, due {t.get('due') or 'no date'})"
        )
        if t.get("draft_message"):
            lines.append(f"  - Draft: {t['draft_message']}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    convs = fetch_conversations(demo="--demo" in sys.argv)
    tasks = extract_tasks(convs)
    write_markdown(tasks)
    print(open("tasks.md").read())
