"""One-shot backfill: add "author" field to existing song JSONs. Safe to re-run."""
import re
from pathlib import Path

MAPPING = {
    'v0_original': 'Claude',
    'v1_gemini_fix': 'Claude',
    'v2_broken_beat': 'Claude',
    'v3_bass_fix': 'Claude',
    'v4_gemini_compose': 'Gemini',
    'v5_codex_compose': 'Codex',
    'v6_claude_struct': 'Claude',
    'v6_proper_breakbeat': 'Gemini',
    'v7_ethereal_tofu': 'Gemini',
    'v8_cyber_tofu_overdrive': 'Gemini',
    'v9_tofu_legacy': 'Gemini',
    'v10_legacy_reborn': 'Gemini',
    'v11_claude_motif': 'Claude',
    'v11_staccato_strike': 'Gemini',
    'v12_codex_compose2': 'Codex',
    'v12_tears_of_the_tofu': 'Gemini',
    'v13_zenith': 'Gemini',
    'v14_overdrive_tofu': 'Gemini',
}

for p in sorted(Path('songs').glob('*.json')):
    stem = p.stem
    if stem not in MAPPING:
        print(f'  skip {stem}: no mapping')
        continue
    content = p.read_text(encoding='utf-8')
    if '"author"' in content:
        print(f'  skip {stem}: already has author')
        continue
    author = MAPPING[stem]
    new_content = re.sub(
        r'("name":\s*"[^"]*",)',
        lambda m: f'{m.group(1)}\n  "author": "{author}",',
        content,
        count=1,
    )
    if new_content == content:
        print(f'  WARN {stem}: no name field matched, skipped')
        continue
    p.write_text(new_content, encoding='utf-8')
    print(f'  wrote {stem}: author={author}')
