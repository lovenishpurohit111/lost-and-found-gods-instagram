# Lost & Found Gods — Instagram publisher

This repository is separate from the TaxBuilder Instagram automation. It hosts the carousel images publicly so Meta can fetch them and contains a manual GitHub Actions workflow to publish them to the `lost_and_found_gods` Instagram professional account through Meta's Instagram Graph API.

## Configure once

In this repository's **Settings → Secrets and variables → Actions**, add these repository secrets for the Lost & Found Gods account only:

- `INSTAGRAM_USER_ID` — Instagram professional account ID
- `INSTAGRAM_ACCESS_TOKEN` — access token authorized for Instagram content publishing on that account

Do not reuse the TaxBuilder account's token or paste either value into chat. The Meta app/user must grant the content-publishing permission for this account.

## Publish this carousel

After adding both secrets, go to **Actions → Publish Thursday Letter Carousel → Run workflow**. The workflow publishes the eight slide JPEGs in filename order and uses `caption.txt`.

The images are public under `media/the-thursday-letter/` because Meta's API fetches each carousel image from a public URL. Posts are created only by manual `workflow_dispatch`; there is no scheduled trigger.

## Daily Bhagavad Gita shloka

The separate **Daily Shloka for Lost & Found Gods** workflow posts one Bhagavad Gita verse with its Sanskrit text, transliteration, plain-language meaning, and short reflection. The Bhagavad Gita is part of the Mahabharata. Verse text is source-linked to IIT Kanpur's Gita Supersite; English meanings are original plain-language paraphrases, not presented as a published translation.

- Schedule: daily at **9:17 AM India time** (03:47 UTC), starting **November 4, 2026**.
- The initial queue contains 31 distinct, source-cited verses. The workflow stops after the queue is used; it does not silently repeat a verse.
- The scheduled run renders a 1080 × 1350 card, commits that dated image so Meta can fetch its public URL, publishes it through the Instagram Graph API, and records a receipt to prevent duplicate posts.
- To check the account without publishing, use **Actions → Daily Shloka for Lost & Found Gods → Run workflow** and leave **Publish today's shloka now** unchecked. Selecting it publishes immediately.
- This workflow uses this repository's existing `INSTAGRAM_USER_ID` and `INSTAGRAM_ACCESS_TOKEN` secrets. It does not create or expose a new key. Meta access tokens are not permanent; if the saved token expires or is revoked, the workflow will fail safely until the account is reauthorized and the secret updated.
- It is independent of the TaxBuilder Instagram workflow. Do not copy TaxBuilder credentials into this repository.
