# Friction log: Talk-to-Task (Bee + Amazon Bedrock)

Each entry lists the task I attempted, the steps, what I expected versus what happened, a severity rating,
my workaround, and an actionable suggestion. Tools used: Bee app (iPhone and Apple Watch), Bee CLI, Amazon Bedrock.

## 1. Finding the Bee app
- **Task:** install Bee on my iPhone.
- **Steps:** searched the App Store.
- **Expected:** an obvious listing.
- **Actual:** I could not find it at first. It is listed as "Bee: Your Personal AI".
- **Severity:** low
- **Workaround:** searched by the full name.
- **Suggestion:** link the App Store page directly from the developer docs and hackathon resources.

## 2. Turning on Developer Mode
- **Task:** enable Developer Mode so the CLI can connect.
- **Steps:** opened Settings in the Bee app.
- **Expected:** a clear way to turn it on.
- **Actual:** the app showed "Developer mode disabled" without saying what to do next.
- **Severity:** low-medium
- **Workaround:** followed the Developer Mode guide in the docs (tap the app version five times).
- **Suggestion:** add an in-app hint or a link to the guide next to the "disabled" message.

## 3. Installing the CLI
- **Task:** `npm install -g @beeai/cli`.
- **Expected:** a clean install.
- **Actual:** npm warned that the package's postinstall script was blocked (not covered by allowScripts). The CLI still worked.
- **Severity:** low
- **Workaround:** ignored the warning.
- **Suggestion:** document the warning, or avoid needing the postinstall script.

## 4. Reading conversation data
- **Task:** read my transcript with `bee now --json`.
- **Expected:** clean utterances in time order, attributed to me.
- **Actual:**
  - utterances were not in chronological order
  - the same sentence appeared twice, once labeled "Unknown" and once with my name
  - a clear solo recording was labeled "Unknown"
  - one sentence ended mid-word ("...call the landl")
- **Severity:** medium
- **Workaround:** sorted by `spoken_at`, treated solo "Unknown" speech as the user, and let the language model use context.
- **Suggestion:** return utterances in order, merge duplicates, and let users set their own speaker identity.

## 5. Names in transcripts
- **Task:** extract who I promised things to.
- **Expected:** the names I said (Priya, Rahul).
- **Actual:** speech-to-text produced "Bria", "Tria" and "Raoul".
- **Severity:** medium
- **Workaround:** a known-contacts list passed to the model to correct names.
- **Suggestion:** let the CLI or API accept a contacts list to bias transcription.

## 6. Calling a Claude model on Amazon Bedrock
- **Task:** call Claude Sonnet 5.5 after submitting the Anthropic use case form.
- **Expected:** access to the model.
- **Actual:** AccessDeniedException saying the model was not available for this account, with no hint about which models were.
- **Severity:** medium
- **Workaround:** used Claude Sonnet 4.6.
- **Suggestion:** list the models the account can use in the error message.

## 7. Choosing a Bedrock inference profile
- **Task:** find the model ID for Sonnet 4.6.
- **Expected:** one obvious ID.
- **Actual:** the model page showed a plain ID, but the model needed an inference profile, and the console offered separate AU and Global profiles with little explanation.
- **Severity:** low-medium
- **Workaround:** chose the Global profile and matched the region in the console.
- **Suggestion:** show the usable ID on the model page and explain when to pick each profile.

## 8. Creating a todo from the CLI
- **Task:** write a task back into Bee todos.
- **Expected:** one documented command, with a way to set the alarm time.
- **Actual:** the sources I found showed two forms (`bee todos create --text` and `bee todos add`), and I found no documented way to set an alarm time even though todos have an `alarm_at` field.
- **Severity:** low-medium
- **Workaround:** the app tries `create --text` first and falls back to `add`, and puts the due date in the todo text.
- **Suggestion:** make one form canonical in the docs and `--help`, and document how to set an alarm.