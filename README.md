# Delmarva Home Comfort Guide

Unpublished static draft. Every page is `noindex, nofollow`, and `robots.txt` disallows all crawlers. This repository does not launch the site or change DNS.

## Folder URLs

These paths are files under `public/`. They are not a live site.

| URL | File |
| --- | --- |
| `/` | `public/index.html` |
| `/ac/repair/` | `public/ac/repair/index.html` |
| `/heating/no-heat/` | `public/heating/no-heat/index.html` |
| `/heat-pumps/repair-or-replace/` | `public/heat-pumps/repair-or-replace/index.html` |
| `/maintenance/` | `public/maintenance/index.html` |
| `/areas/seaford-de/` | `public/areas/seaford-de/index.html` |
| `/about/` | `public/about/index.html` |
| `/how-referrals-work/` | `public/how-referrals-work/index.html` |
| `/privacy/` | `public/privacy/index.html` |

Unknown paths are served from `public/404.html`. There is no client-side router.

## Local check

From the repository root, with Python 3.11 or newer:

```bash
python3 validate.py
```

The script reads files on disk only. It does not start a server or make network requests. A pass is a filesystem check, not a hosting, accessibility, or search result.

## Publish directory

`netlify.toml` sets `publish = "public"`. Only that directory is the static site. `README.md`, `validate.py`, `draft-manifest.json`, and `validation-results.json` stay outside it. If a publish root is ever pointed at the repository root, those four URLs are forced to `404.html`.

## Staging protections that stay on

- Every HTML page includes `<meta name="robots" content="noindex,nofollow">`.
- `netlify.toml` sends `X-Robots-Tag: noindex, nofollow` for `/*`.
- `public/robots.txt` contains `Disallow: /`.
- Referral routing is inactive. The tracking number is the plain text `Tracking number pending — calls are not active` and is not a link.
- Pages have no forms and no `tel:` links. Request buttons are disabled.
- `ignore = "exit 0"` skips an ordinary automatic build. It is not a privacy control or a deploy lock.

Page metadata uses the base `https://delmarvahomecomfortguide.com`. That setting does not connect the domain.

## Remaining launch gates

Leave the noindex meta tags, `X-Robots-Tag`, and `Disallow: /` in place until an approved production release. Still required before any launch:

- Qualified review of the draft, including HVAC and fire/life-safety review of the safety passages
- Confirmation of any referral recipient, disclosure, and a real routing number
- Privacy and legal review
- A deliberate hosting setup and DNS change, done outside this repository
- Removal of the build-skip `ignore` only as part of that approved release

Passing `python3 validate.py` does not clear those gates.
