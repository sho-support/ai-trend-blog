# Commercial portal migration

Release remains on hold until the permanent host and each advertising media
registration are verified. Do not merge seasonal content into the old hosting
merely to get a public URL.

## Cloudflare Pages

- Build: `python3 portal-tools/build_commercial_site.py`
- Output directory: `dist`
- `COMMERCIAL_SITE_URL`: the verified permanent HTTPS origin, without a path.
  Do not use `CF_PAGES_URL`, which can be a temporary deployment URL.
- `CF_PAGES=1`: supplied by Pages; strips `.html` from canonical and sitemap
  URLs to match Pages redirects. A real `404.html` avoids the SPA fallback.
- New origins default to a preview. Photos and short descriptions remain,
  advertising navigation and executable scripts are removed, affiliate feeds
  are omitted, analytics are off, and indexing is blocked.
- After verifying Rakuten registration for the new media, set
  `COMMERCIAL_MEDIA_APPROVED=1` for production only. Keep
  `COMMERCIAL_PREVIEW=1` on preview branches. A8 also needs its own fresh
  program, material, destination, image and media review; the existing old
  media registration must never be rewritten as approval for the new host.

Prefer Git integration so the existing daily product updates reach Pages.
If the Cloudflare GitHub app is not already authorized for this repository,
request only `sho-support/ai-trend-blog` access at the authorization step.
Do not grant all repositories or reuse a token scoped to another project.
Do not create a paid subscription or change the HP project's R2 resources.

Before enabling production, run `python3 portal-tools/test_portals.py`, check
mobile and desktop in the actual host, and verify search, product links,
canonical URLs, feeds, ad disclosure and GA4. Search Console registration and
sitemaps must use the actual permanent origin.
