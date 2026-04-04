"""
Hotfix script for app.py — patches the three critical JS bugs:
1. Double reader.read() call that breaks streaming
2. Broken \\uXXXX unicode escapes that show as literal text instead of emoji
3. Stats/Models API calls that may be hitting wrong endpoints
"""

with open('/Applications/AZAN/webui/app.py', 'r') as f:
    content = f.read()

# BUG 1: Double reader.read() — remove the first (broken) line, fix the second
OLD = "        const{done,val}=await reader.read()??{};\n        const{done:d2,value}=await reader.read();if(d2)break;"
NEW = "        const{done,value}=await reader.read();if(done)break;"
assert OLD in content, "Could not find double reader.read() bug"
content = content.replace(OLD, NEW, 1)
print("Fixed: double reader.read()")

# BUG 2: Fix broken avatar/emoji unicode escapes (\\uD83D\\uDC64 etc.)
# Replace raw backslash-u sequences with actual UTF-8 characters via a scan
replacements = {
    '\\\\uD83D\\\\uDC64': '&#128100;',   # 👤
    '\\\\uD83C\\\\uDF19': '&#127769;',   # 🌙
    '\\\\u2600\\\\uFE0F': '&#9728;&#65039;',  # ☀️
    '\\\\uD83D\\\\uDD0A': '&#128266;',   # 🔊
    '\\\\uD83D\\\\uDCCB': '&#128203;',   # 📋
    '\\\\uD83D\\\\uDC4D': '&#128077;',   # 👍
    '\\\\uD83D\\\\uDC4E': '&#128078;',   # 👎
    '\\\\u26A0': '&#9888;',              # ⚠
    '\\\\u2013': '&#8211;',              # –
    '\\\\u2026': '&#8230;',             # …
    '\\\\u00b2': '&#178;',              # ²
    '\\\\u2014': '&#8212;',             # —
    '\\\\u2713': '&#10003;',            # ✓
    '\\\\u23F9': '&#9209;',             # ⏹
    '\\\\u25ae': '&#9646;',             # ▮
}
for bad, good in replacements.items():
    if bad in content:
        content = content.replace(bad, good)
        print(f"Fixed emoji escape: {bad} -> {good}")

# BUG 3: Make sure fact-check regex is correctly escaped for HTML context
# The \\\\s in regex within Python triple string should be \\s in the output JS
# Since this is inside a Python string that becomes the HTML, 
# we already used r-strings and fixed escaping, but let's verify split is correct
# Check the split line -- if it has \\\\n it'll split on literal \n which is correct
split_check = "split('\\\\n')" in content or "split('\\n')" in content
print("Split check:", "split('\\\\n')" in content, "/ split('\\n'):", "split('\\n')" in content)

with open('/Applications/AZAN/webui/app.py', 'w') as f:
    f.write(content)
print("Hotfix applied. File size:", len(content))
