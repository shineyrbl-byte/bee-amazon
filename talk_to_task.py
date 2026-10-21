#!/usr/bin/env python3
"""Talk-to-Task core: read Bee conversations, extract commitments with Claude on Amazon Bedrock.

CLI usage:
    python talk_to_task.py          # live Bee data (runs `bee now --json`)
    python talk_to_task.py --demo   # built-in sample data
"""

import datetime
import json
import os
import subprocess
import sys

import boto3

# Set these in your terminal (see README): the Bedrock inference profile ID and region.
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
USER_NAME = os.environ.get("USER_NAME", "Avisha")  # the speaker name Bee shows for you

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
Bee often cannot identify the user's voice and labels it "Unknown". Treat "Unknown" lines as the user speaking unless the context clearly shows it is someone else.
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


def fetch_conversations(demo: bool = False) -> list[dict]:
    """Return [{'id', 'title', 'start', 'text'}, ...]. Only transcript text is kept (no location etc.)."""
    if demo:
        return DEMO_CONVERSATIONS
    result = subprocess.run(
        ["bee", "now", "--json"], capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    conversations = []
    for c in data.get("conversations", []):
        start_ms = c.get("start_time")
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


def extract_tasks(conversations: list[dict]) -> list[dict]:
    if not conversations:
        return []
    transcript = "\n\n".join(
        f"[{c['start']}] {c['title']}\n{c['text']}" for c in conversations
    )
    today = datetime.date.today()
    prompt = PROMPT.format(
        today=today.isoformat(),
        weekday=today.strftime("%A"),
        user=USER_NAME,
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
