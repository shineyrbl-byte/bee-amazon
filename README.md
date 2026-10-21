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

Everything runs locally except the call to Amazon Bedrock, which receives only transcript text.
Only record yourself or people who have agreed to be recorded.

## Limitations

- Reads the last ~10 hours of Bee conversations (what `bee now` returns).
- Speech-to-text errors can still cause missed or wrong tasks; confidence scores help you spot them.
- Tasks are not saved or synced to a calendar yet.

## License

MIT, see `LICENSE`.