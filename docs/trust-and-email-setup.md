# Trust pages & contact email setup

DraftLens publishes public **Privacy**, **Terms**, **Data security**, and **Contact** routes for user trust and for **Google OAuth branding** fields. This file is operational guidance—not legal advice.

## Public URLs (production)

After deploy, confirm over HTTPS (no login required):

| Page | URL |
|------|-----|
| Home | `https://www.draftlensai.com` |
| Privacy | `https://www.draftlensai.com/privacy` |
| Terms | `https://www.draftlensai.com/terms` |
| Data security | `https://www.draftlensai.com/data-security` |
| Contact | `https://www.draftlensai.com/contact` |

Set **`NEXT_PUBLIC_SITE_URL=https://www.draftlensai.com`** on the Next.js (Vercel) project so `metadataBase`, canonical tags, and `sitemap.xml` use the `www` host consistently.

## Email addresses shown on the site

The marketing and legal pages display:

- `support@draftlensai.com` — product, billing, general help  
- `privacy@draftlensai.com` — privacy and data requests  
- `security@draftlensai.com` — security reports  

**TODO before launch:** Create these mailboxes (or aliases/forwarders to your operational inbox) so users and Google reviewers do not hit dead addresses. Optionally set **`NEXT_PUBLIC_CONTACT_EMAIL`** to the address you want in JSON-LD organization metadata (often the same as support).

There is **no** automated “delete all my data” API documented here; privacy requests are handled manually via `privacy@…` until a self-service flow exists.

## Attorney review

The shipped copy is written to be **accurate and conservative** about AI, subprocessors, retention, and certifications. Before relying on it for regulated customers or OAuth production verification, have **qualified counsel** review:

- Privacy Policy (`/privacy`)  
- Terms of Service (`/terms`)  
- Data security page (`/data-security`)  
- Alignment with your actual hosting region, DPA stack, Stripe configuration, and analytics (if any)

## Google OAuth branding

See **`docs/google-drive-setup.md` §3b** for the exact strings to paste (home page, privacy URL, terms URL, authorized domain).
