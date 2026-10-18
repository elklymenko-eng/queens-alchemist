# V2 Telegram Onboarding & Free Discovery Funnel — Draft
Status: design proposal; NOT implemented. Owner approval required for billing and deployment.

## Acquisition
Visitors arrive from reels, podcasts, webinars or other links promising one of: discover relationship pattern, explore feminine archetypes, Date Like a Queen, create a relationship like a Queen.

## Welcome
"Darling, your love life has a way of revealing the parts of you that are ready for a little alchemy. Let's discover what's been running the show—and how to let your Queen take the throne."

Include transparent AI disclosure, coaching-not-therapy scope, privacy/retention explanation and /reset. Do not require sensitive childhood details.

## Button onboarding (excluded from paid/free AI reply count)
1. Relationship status: single/dating; single taking a break; situationship/complicated; in relationship; breakup/healing.
2. Most recognizable pattern: unavailable partners; overgiving; overmanaging; chemistry vs compatibility; guardedness/receiving; unsure/explore.
3. Desired focus: discover pattern; explore archetypes; date like a Queen; create relationship like a Queen; heal/reconnect/radiance.
4. Optional free-text: "What's happening in your love life?" Include skip button.

Save responses as contextual hints, not diagnoses. Never assume selected pattern is confirmed.

## Free trial recommendation
10 free AI-generated assistant replies per user, not five calendar days. Welcome, onboarding button steps, safety responses, /help, /reset and purchase/account instructions should not consume trial replies. Count only successful substantive AI replies, atomically and persistently, including across reset and restarts. Avoid trial reset abuse. Explain counter clearly. At trial end, preserve ability to access account/privacy/safety help. No charging without affirmative purchase.

## Flexible coaching journey
Replies 1–3: attune, clarify, reflect possible pattern and archetypes.
Replies 4–7: support a real micro-shift; offer optional brief text-guided Inner Union, emotional witnessing or grounded discernment practice, depending on readiness and consent.
Replies 8–10: integrate one observable next action, reflect learning, introduce continuation paths.
These are guidance, not a rigid sequence. Answer direct practical questions first; avoid repetitive questions or practice pitching. No compulsory trauma excavation. Offer one practice at a time and do not imply video content was viewed.

## Continuation paths
- Paid ongoing Alchemist support (pricing and checkout TBD).
- Self-paced Queen's Alchemy course (link/pricing TBD).
- One-on-one coaching with owner (booking link TBD).
Show contextually after value has been delivered, and transparently at the trial limit. Avoid implying any offer is already live without configured links and billing.

## Implementation tasks
- Add Telegram callback flows and skip/edit choices.
- Persist onboarding and separate trial counter in SQLite; protect against race conditions and duplicate delivery.
- Connect modular V2 knowledge with token budget and evaluation tests.
- Provide a short written Inner Union guided practice; optional owner-recorded audio or wallpaper later.
- Add offer catalog with owner-supplied verified URLs.
- Add privacy notice, retention policy, error recovery, feedback, metrics and abuse prevention.
- Test onboarding paths, safety exceptions, trial limits and payment transitions before deployment.

## Metrics to watch
Start-to-completion rate, first free-text response rate, first practice uptake, number of replies used, helpfulness feedback, coaching click-through, self-study interest, paid AI conversion. Aggregate minimally and respect privacy.
