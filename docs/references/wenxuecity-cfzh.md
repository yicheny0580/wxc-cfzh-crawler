# Wenxuecity CFZH Reference

This page records target-site references for the `财富智汇` crawler and inspector.
Use it for stable pointers and page-shape notes. Keep detailed parser behavior in
tests and crawler docs.

## Seed URLs

- Forum index: https://bbs.wenxuecity.com/cfzh/
- Sample root post: https://bbs.wenxuecity.com/cfzh/74980.html
- Sample reply: https://bbs.wenxuecity.com/cfzh/74981.html

## Observed Page Shapes

- The forum index lists root posts and replies together, with reply rows nested
  under root posts when the page exposes parentage.
- Listing rows can include title, author profile links, byte count, timestamp,
  and source URL. Current author links may appear as `a.nickname` elements
  pointing at `passport.wenxuecity.com/members/index.php?act=profile...`;
  older rows may use `a.username` or `passport.wenxuecity.com/profile.php`.
- Root post pages include post metadata, body content, and an "all replies"
  section with reply links.
- Reply pages may have their own URL and metadata even when the listing row shows
  `0 bytes`.

## Maintenance Notes

- Refresh these sample links if the target site removes or materially changes the
  referenced pages.
- When parser assumptions change, update
  [../design-docs/project-invariants.md](../design-docs/project-invariants.md),
  [../../crawler/docs/index.md](../../crawler/docs/index.md), and parser tests
  together.
