# Editorial Scripts: Helping Editors Focus on Scholarship

## Why This Project Exists
Academic journals depend on online submission systems to manage manuscripts, referee reports, and decision letters. Each platform--ScholarOne, Editorial Manager, SIAM portals, and shared Gmail inboxes--has its own layout, login steps, and download rules. Collecting information across them is routinely manual work: editors sign in repeatedly, download files one at a time, and copy status updates into spreadsheets. It is slow, prone to mistakes, and leaves little space for the thoughtful work of steering a journal.

Editorial Scripts is Dylan Possamai's effort to change that. It is an automation toolkit that signs in securely, navigates those editorial systems as a human would, and assembles the documents and data that journal teams need. The goal is simple: give editors their time back and deliver a complete picture of each manuscript without the tedious clicks.

## What the System Does
- **Automated Sign-In**: Launches a browser, enters credentials stored safely in macOS Keychain, and handles two-factor codes from Gmail without human intervention.
- **Platform Navigation**: Mimics the steps editors take--opening submissions, following links, and capturing referee reports, manuscripts, timelines, and decision metadata.
- **Organized Outputs**: Saves PDFs, reviewer comments, and status data into clear folders and structured files, making handoffs and analysis straightforward.
- **Consistency Across Journals**: Works with a range of editorial portals, so information from ScholarOne, Editorial Manager, SIAM, and Gmail lands in the same standardized format.

## Who Benefits
- **Editorial Staff**: Hours of repetitive downloading and copying drop to minutes, freeing time for strategic decisions and author communication.
- **Faculty Editors and Research Leads**: Receive current, reliable summaries of submission pipelines and reviewer activity without digging through multiple systems.
- **Partner Journals**: Experience faster, more consistent follow-up and fewer delays caused by missing documents.
- **Authors and Referees**: Indirectly benefit from a smoother editorial process that keeps them informed and respected.

## Safeguards and Trust
Security is non-negotiable. Credentials are encrypted in the macOS Keychain, sensitive files are ignored by Git, and automated checks prevent tokens from slipping back into history. Recent maintenance removed legacy archives that once contained outdated tokens, and `SECURITY.md` outlines how the team keeps the project locked down.

## Current Progress
- **Financial Studies (FS)**: Fully verified extractor that reliably gathers Gmail-based submission materials.
- **Manufacturing & Service Operations (MF)** and **Management Science (MOR)**: Logged-in automation confirmed; extraction flow is being modernized in a cleaner, modular architecture.
- **Other Journals (JOTA, MAFE, SICON, SIFIN, NACO)**: Legacy extractors exist and are being brought forward into the new framework with more robust authentication and data handling.

## What Comes Next
1. Finish migrating each journal extractor into the streamlined architecture inside `src/`, reducing maintenance and accelerating new features.
2. Expand reporting so output is not just folders of PDFs but dashboards that highlight reviewer workload, turnaround times, and emerging trends.
3. Continue hardening two-factor authentication flows and credential management so long-term maintenance stays easy and safe.

## How to Explore Further
- Skim the project `README.md` for setup instructions and a tour of the codebase.
- Visit the `docs/` folder for technical deep dives, status updates, and governance notes.
- Reach out to the project owner if you have ideas for pilots, enhancements, or collaborations.

Editorial Scripts shows what careful automation can do inside scholarly publishing. By reducing repetitive effort, it lets editors focus on the work that truly matters: nurturing world-class research and supporting the people who create it.
