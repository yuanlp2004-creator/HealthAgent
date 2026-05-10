"""Verify citation distribution in thesis.tex"""
import re

with open(r'd:\HealthAgent\docs\thesis.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# Find references section
refs_start = content.find(r'\section*{参考文献}')
body = content[:refs_start]
refs_section = content[refs_start:]

# Count reference items (auto-numbered enumerate)
ref_items = len(re.findall(r'\\item\s', refs_section))
print(f'Reference items: {ref_items}')

# Count citations in body using string find
citations = []
pos = 0
prefix = r'\textsuperscript{'
while True:
    idx = body.find(prefix, pos)
    if idx < 0:
        break
    end = body.find('}', idx)
    if end < 0:
        break
    inner = body[idx + len(prefix):end]
    citations.append(inner)
    pos = end + 1

print(f'Citation markers: {len(citations)}')

# Extract all cited numbers
all_cited = set()
for c in citations:
    text = c.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]
    for part in text.split(','):
        part = part.strip()
        if '-' in part:
            a_str, b_str = part.split('-', 1)
            a = int(a_str.strip())
            b = int(b_str.strip())
            for i in range(a, b + 1):
                all_cited.add(i)
        elif part.lstrip('-').isdigit():
            all_cited.add(int(part))

print(f'Unique refs cited: {len(all_cited)}')
print(f'Cited refs: {sorted(all_cited)}')
print(f'Not cited: {sorted(set(range(1, 31)) - all_cited)}')

# Post-2020 count (refs published after 2020)
# From the reference list analysis:
pre2020_refs = {2, 3, 6, 10, 13}  # 2019, 2007, 2005, 2019, 2019
# Also check: ref 1(2024), 4(2020), 5(2025), 7(2024), 8(2025), 9(2025),
# 11(2024), 12(2025), 14(2023), 15(2023), 16(2023), 17(2023), 18(2024),
# 19(2020), 20(2024), 21(2026), 22(2026), 23(2025), 24(2024), 25(2025),
# 26(2025), 27(2025), 28(2025), 29(2025), 30(2025)
post2020_count = 30 - len(pre2020_refs)
print(f'\nPost-2020 references: {post2020_count}/30 (including 2020)')

# For "2020后" (after 2020, not including 2020):
post2020_strict = {1,5,7,8,9,11,12,14,15,16,17,18,20,21,22,23,24,25,26,27,28,29,30}
print(f'Post-2020 (strict, excluding 2020): {len(post2020_strict)}/30')

# Map chapters to find where refs first appear
# Split body by sections
chapters = {}
current_ch = 0
for line in body.split('\n'):
    if r'\section{' in line and '绪论' in line:
        current_ch = 1
    elif r'\section{' in line and '相关技术' in line:
        current_ch = 2
    elif r'\section{' in line and '需求分析' in line:
        current_ch = 3
    elif r'\section{' in line and '关键模块' in line:
        current_ch = 4
    elif r'\section{' in line and '系统测试' in line:
        current_ch = 5
    elif r'\section{' in line and '结论与展望' in line:
        current_ch = 6

    if current_ch > 0:
        if current_ch not in chapters:
            chapters[current_ch] = set()
        # Find citations in this line
        p = 0
        while True:
            idx = line.find(r'\textsuperscript{', p)
            if idx < 0:
                break
            end = line.find('}', idx)
            if end < 0:
                break
            inner = line[idx + len(r'\textsuperscript{'):end]
            text = inner.strip()
            if text.startswith('[') and text.endswith(']'):
                text = text[1:-1]
            for part in text.split(','):
                part = part.strip()
                if '-' in part:
                    a_str, b_str = part.split('-', 1)
                    a = int(a_str.strip())
                    b = int(b_str.strip())
                    for i in range(a, b + 1):
                        chapters[current_ch].add(i)
                elif part.lstrip('-').isdigit():
                    chapters[current_ch].add(int(part))
            p = end + 1

print('\n--- Citations by chapter ---')
for ch in sorted(chapters):
    print(f'  Ch{ch}: {sorted(chapters[ch])} ({len(chapters[ch])} unique)')

# First appearances by chapter
seen = set()
first_appearances = {}
for ch in sorted(chapters):
    new_in_ch = chapters[ch] - seen
    first_appearances[ch] = new_in_ch
    seen |= chapters[ch]

print('\n--- First appearances by chapter ---')
ch12_total = 0
for ch in sorted(first_appearances):
    print(f'  Ch{ch}: {sorted(first_appearances[ch])} ({len(first_appearances[ch])} new)')
    if ch <= 2:
        ch12_total += len(first_appearances[ch])
print(f'\nCh1+Ch2 first appearances: {ch12_total} (requirement: <= 20)')
