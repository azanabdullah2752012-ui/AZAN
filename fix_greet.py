import re
import codecs

with open("/Applications/AZAN/webui/app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the greet function which has literal newlines inside JS double quotes
safe_greet = r"""function greet(){addMsg(["Hello! I'm **AZAN**, your intelligent AI assistant.","","Powered by Semantic RAG, RL knowledge, and autonomous agents.","","Try:","- `solve x+5=10` — Math engine","- `fact-check the moon landing` — Verification agent","- `python: print(42)` — Code runner","- `physics v=20 u=0 t=5 find a` — Physics solver","- 📎 Attach an image to analyze it visually"].join("\n"),'azan',false);}"""

# Use regex to find and replace the block
new_text = re.sub(r'function greet\(\)\{addMsg\("Hello!(.*?)(visually)",\'azan\',false\);\}', safe_greet, text, flags=re.DOTALL)

with open("/Applications/AZAN/webui/app.py", "w", encoding="utf-8") as f:
    f.write(new_text)

print("Greet function patched safely.")
