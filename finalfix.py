"""
Final fix: Replace ALL broken JS inside app.py's HTML template.
Uses a surgical Python script to find and replace problematic functions.
"""

with open('/Applications/AZAN/webui/app.py', 'r') as f:
    content = f.read()

# Fix 1: greet() - replace the broken unicode paperclip emoji
OLD_GREET = "function greet(){addMsg('Hello! I\\'m **AZAN**, your intelligent AI assistant.\\\\n\\\\nI\\'m powered by Semantic RAG, RL-enhanced knowledge, and autonomous agents.\\\\n\\\\nTry:\\\\n- `solve x&#178;+5x+6` &#8212; Math engine with LaTeX output\\\\n- `fact-check the moon landing` &#8212; Verification agent\\\\n- `python: print(42)` &#8212; Code execution\\\\n- `physics v=20 u=0 t=5 find a` &#8212; Physics solver\\\\n- \\\\uD83D\\\\uDCCE Attach an image to analyze it visually','azan',false);}"

NEW_GREET = """function greet(){addMsg("Hello! I'm **AZAN**, your intelligent AI assistant.\\n\\nPowered by Semantic RAG, RL knowledge, and autonomous agents.\\n\\nTry:\\n- `solve x+5=10` \\u2014 Math engine\\n- `fact-check the moon landing` \\u2014 Verification agent\\n- `python: print(42)` \\u2014 Code runner\\n- `physics v=20 u=0 t=5 find a` \\u2014 Physics solver\\n- Attach an image to analyze it visually",'azan',false);}"""

if OLD_GREET in content:
    content = content.replace(OLD_GREET, NEW_GREET, 1)
    print("Fixed greet()")
else:
    # Try partial match
    if "\\\\uD83D\\\\uDCCE" in content:
        content = content.replace("\\\\uD83D\\\\uDCCE", "&#128206;", 1)
        print("Fixed paperclip emoji in greet()")
    print("Note: exact greet match not found, trying partial")

# Fix 2: Remove any remaining broken \\uXXXX sequences that slipped through
import re
def fix_js_unicode(m):
    codepoint = m.group(1)
    try:
        return chr(int(codepoint, 16))
    except:
        return m.group(0)
# Fix \\uXXXX patterns remaining (4 hex digits, backslash escaped in content)
# These appear as literal \\u in the output HTML which JS can't handle
broken = re.findall(r'\\\\u[0-9A-Fa-f]{4}', content)
if broken:
    print("Remaining broken unicode escapes:", set(broken[:10]))

# Fix 3: Ensure split is correct - should split on actual newline not literal \n
# The streaming split should be on '\n' - in a Python HTML string that should be \\n
if "split('\\\\n')" in content:
    print("Split is correctly escaping newline")
else:
    print("WARNING: split may be broken")

# Fix 4: Check for any other \\uD / surrogate pairs
surrogates = re.findall(r"\\\\uD[89A-F][0-9A-Fa-f]{2}", content, re.IGNORECASE)
if surrogates:
    print("Found surrogate pairs to fix:", set(surrogates))
    for s in set(surrogates):
        content = content.replace(s, "&#65039;")

with open('/Applications/AZAN/webui/app.py', 'w') as f:
    f.write(content)
print("Final fix applied. Size:", len(content))
