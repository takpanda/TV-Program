You are a repository automation assistant.

Goal:
Update `kuchikomi.json` in place based on:
- `.github/skills/update-kuchikomi/SKILL.md`
- `programs.json`
- the current `kuchikomi.json`

Requirements:
- Modify only `kuchikomi.json`
- Produce a valid JSON array
- Each object must contain exactly:
  - `title`
  - `sentiment`
  - `text`
- `sentiment` must be one of:
  - `positive`
  - `negative`
  - `mixed`
- `text` must:
  - start with a sentiment emoji
  - be concise
  - feel like a short social-media post
- Prefer 10–15 entries
- Preserve existing titles when possible
- Keep titles aligned with `programs.json`

Validation:
After editing the file, run:
`python scripts/update_kuchikomi.py --validate`

If validation fails, fix the file and rerun validation until it passes.
