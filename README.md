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
