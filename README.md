# The Queen's Alchemist — private Telegram beta

This is an initial working prototype, not a production-ready subscription service.

## Setup
1. Create a **private GitHub repository** and upload these files. Never upload `.env` or API tokens.
2. Create a Railway project from the GitHub repository. Railway will build the included Dockerfile and run the bot as a worker; no domain or Web App needed.
3. In Railway's service **Variables**, add `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4.1-mini`, and `DATA_DIR=/app/data`.
4. To get your numeric Telegram user ID, open `@lovealchemist_bot` and send `/id` once the service is running.
5. Add `ALLOWED_USER_IDS=your_numeric_id` in Railway Variables. Redeploy/restart; send `/start` to test. Add beta testers' IDs later as comma-separated numbers. Do not use Telegram usernames in this field.
6. For durable chat history across deploys, mount a Railway persistent volume at `/app/data` **before inviting testers**. Otherwise SQLite records can be lost on redeploy.
7. Test `/start`, status buttons, a normal conversation, a practice link, `/feedback`, `/reset`.

## Important
- Telegram BotFather's secret bot token and OpenAI API key go **only** in Railway Variables, never GitHub or chat.
- This uses **long polling**. Do not run a second copy of the bot or configure a competing Telegram webhook.
- This prototype stores conversation text and ratings in a local SQLite database. The `/reset` command deletes the user's stored message history (not provider logs, backups, Telegram's copy, or feedback). Create a proper privacy notice, retention policy and consent before a public launch.
- Beta allowlist restricts usage to numeric Telegram IDs; users can discover their ID with `/id`.
- No payment or Telegram Stars implementation yet. Subscription access control can be added to this same bot after testing.
- You can adjust `knowledge.md` and `practices.json` without changing the Python logic. Review edits before deploying.
- Hosting and API calls can incur charges. Set provider budgets/alerts.
- Site practice links may require sign-in; test each as a non-member.
- This starter contains condensed knowledge rather than the full original source archive. Expand it after evaluating real responses.
