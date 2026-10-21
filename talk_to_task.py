#!/usr/bin/env python3
"""Talk-to-Task: turn spoken commitments captured by Bee into tasks + draft follow-ups."""
import datetime
import json
import os
import subprocess
import sys

import boto3

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "PASTE-MODEL-ID-HERE")
REGION = os.environ.get("AWS_REGION", "us-east-1")
USER_NAME = os.environ.get("USER_NAME", "Avisha")  # the speaker name Bee shows for you

DEMO_TEXT = """
Alex: Can you send me the project report?
Avisha: Sure, I'll send you the report by Friday.
Avisha: Also remind me to call the landlord about the leak tomorrow morning.
Priya: We should book the venue soon.
Avisha: I'll check prices and message you on Monday.
"""

PROMPT = """Today is {today}. Below is a transcript of conversations the user ("{user}") had.
Find every commitment the USER ("{user}") made or was asked to do. Ignore things other people promised.
Return ONLY a JSON array (no markdown fences). Each item must have:
  "task": short action phrase,
  "person": who it involves (or null),
  "due": ISO date YYYY-MM-DD (resolve words like "Friday" using today's date) or null,
  "confidence": number 0-1,
  "draft_message": a short, friendly follow-up message to that person (or null).

Transcript:
{transcript}
"""


def get_transcript(demo: bool) -> str:
    if demo:
        return DEMO_TEXT
    result = subprocess.run(["bee", "now"], capture_output=True, text=True, check=True)
    return result.stdout


def extract_tasks(transcript: str) -> list[dict]:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    prompt = PROMPT.format(today=datetime.date.today().isoformat(), user=USER_NAME, transcript=transcript)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 2000, "temperature": 0},
    )
    text = response["output"]["message"]["content"][0]["text"]
    start, end = text.find("["), text.rfind("]")
    return json.loads(text[start : end + 1])


def write_markdown(tasks: list[dict], path: str = "tasks.md") -> None:
    lines = [f"# What I promised ({datetime.date.today().isoformat()})", ""]
    for t in sorted(tasks, key=lambda x: x.get("due") or "9999"):
        lines.append(f"- [ ] **{t['task']}** (with {t.get('person') or 'n/a'}, due {t.get('due') or 'no date'})")
        if t.get("draft_message"):
            lines.append(f"  - Draft: {t['draft_message']}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    transcript = get_transcript(demo="--demo" in sys.argv)
    tasks = extract_tasks(transcript)
    write_markdown(tasks)
    print(open("tasks.md").read())
