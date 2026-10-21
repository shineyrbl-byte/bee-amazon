# Bee Amazon
# 🐝 Talk-to-Task

Never forget a promise you made out loud.

Talk-to-Task reads your real conversations captured by a **Bee** wearable (or Bee on Apple Watch),
uses **Claude on Amazon Bedrock** to find the commitments *you* made, resolves them to real due dates,
and drafts a friendly follow-up message for each one. A small web page shows a morning summary.

Built for the Amazon Developer Hackathon (Bee track, plus the AWS Builder and Open Source mini challenges).

## How it works

1. `bee now --json` (Bee CLI) returns recent conversations with full, timestamped utterances.
2. `talk_to_task.py` flattens them into `Speaker: text` lines. Only transcript text is kept; location and other metadata are dropped.
3. The transcript goes to Claude on Amazon Bedrock (Converse API), which returns structured JSON:
   task, person, due date, confidence, and a draft message.
4. `app.py` (Streamlit) groups tasks by Overdue / Today / Tomorrow / Later and shows copyable drafts.
5. Each dated task can be exported to your calendar as an `.ics` file (one task, or all at once).

## Features

- Keeps only *your* commitments and ignores promises other people made.
- Resolves "Friday" or "tomorrow morning" to real dates.
- Treats unidentified ("Unknown") solo speech as the user.
- Optional known-contacts list (sidebar or `CONTACTS` env var) to fix names that speech-to-text mishears.
- Look-back slider to focus on recent conversations.
- Draft follow-up message per task, with one-click WhatsApp and email links.
- Calendar export (`.ics`) for one task or all open tasks.
- **Add to Bee**: writes a task back into your Bee todos with `bee todos`.
- Tasks are saved locally in `tasks_store.json` between runs, with a Done list and a "Carried over" count for promises from earlier days.
- Low-confidence tasks are flagged so you can double-check them.

## Setup

Requirements: Python 3.10+, Node.js, an AWS account with Amazon Bedrock access, the Bee app.

1. **Bee**: install the Bee app, enable Developer Mode (tap the app version 5 times in Settings), then:
   ```
   npm install -g @beeai/cli
   bee login
   bee status
   ```
2. **AWS**: enable a Claude model in Amazon Bedrock and configure credentials (`aws configure`).
   Never commit keys to this repo.
3. **Install and run**:
   ```
   pip install -r requirements.txt
   export BEDROCK_MODEL_ID="global.anthropic.claude-sonnet-4-6"   # your inference profile ID
   export AWS_REGION="ap-southeast-2"                              # your Bedrock region
   export USER_NAME="YourName"                                     # the speaker name Bee shows for you
   streamlit run app.py
   ```
   Click **Fetch & analyze**. Use the **Demo mode** toggle to try it without Bee data.

Command-line version: `python talk_to_task.py` (or `--demo`) writes `tasks.md`.

## Privacy

Everything runs locally except the call to Amazon Bedrock, which receives only transcript text. Saved tasks stay in `tasks_store.json` on your machine (it is git-ignored).
Only record yourself or people who have agreed to be recorded.

## Limitations

- Reads the last ~10 hours of Bee conversations (what `bee now` returns).
- Speech-to-text errors can still cause missed or wrong tasks; confidence scores help you spot them.
- Tasks with the same person and due date are treated as the same promise, so two different promises to one person on one day would merge.
- The Add to Bee button tries `bee todos create --text` and falls back to `bee todos add`, because the CLI docs I found differ; the due date goes in the todo text.
- Calendar export is a manual `.ics` download.

## License

MIT, see `LICENSE`.