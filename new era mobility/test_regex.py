import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'const cars = \[.*?\];', content, flags=re.DOTALL)
if m:
    print("Match found:", len(m.group(0)))
else:
    print("No match")
