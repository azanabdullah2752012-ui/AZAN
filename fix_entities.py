"""
Root cause fix: Chrome decodes HTML entities inside <script> blocks,
breaking the JavaScript code.

This script replaces ALL HTML entities inside the <script> block
with their actual Unicode characters or safe JavaScript string escapes.

For example:
  &quot; -> \\" (escaped double quote in JS string)
  &#128100; -> actual emoji character (safe in JS string)
"""
import html, re

with open('/Applications/AZAN/webui/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the script block inside the HTML template
# The template is between 'return """' and the closing '"""'
ret_start = content.find('    return """')
ret_end = content.find('"""', ret_start + 14)
template = content[ret_start+14:ret_end]

# Find script start and end inside the template
script_start = template.rfind('<script>')
script_end = template.rfind('</script>')

if script_start == -1 or script_end == -1:
    print("ERROR: Could not find <script> block")
    exit(1)

js_block = template[script_start+8:script_end]
print("JS block length:", len(js_block))

# Find all HTML entities in the JS block
entities_found = set(re.findall(r'&(?:[a-z]+|#[0-9]+);', js_block))
print("Entities to fix:", entities_found)

# Replace HTML entities with actual characters
# Special case: &quot; -> escaped double quote (\") or single quote (')  
# In JS strings, &quot; would decode to " which breaks the string
# We need to be careful: if &quot; is used inside a JS string delimited by ',
# we can replace it with the actual " char safely as long as the string uses single quotes

# Strategy: use html.unescape() to convert all entities to real chars
# Then check if any introduced quotes break the JS
js_fixed = html.unescape(js_block)

# Verify no triple-backtick issues - template literals use backticks
# Verify structure is maintained
if '"""' in js_fixed:
    print("WARNING: triple-quote in JS after fix - escaping")
    js_fixed = js_fixed.replace('"""', '\\"\\"\\\"')

print("Fixed JS block length:", len(js_fixed))
print("Entities remaining:", set(re.findall(r'&(?:[a-z]+|#[0-9]+);', js_fixed)))

# Rebuild template with fixed JS
new_template = (
    template[:script_start+8] + 
    js_fixed + 
    template[script_end:]
)

# Rebuild full content
new_content = content[:ret_start+14] + new_template + content[ret_end:]

with open('/Applications/AZAN/webui/app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed! New file size:", len(new_content))

# Verify no syntax errors
import subprocess
result = subprocess.run(
    ['node', '-e', f'try{{new Function({repr(js_fixed)})}}catch(e){{process.stdout.write("ERROR:"+e.message)}}'],
    capture_output=True, text=True
)
if result.stdout.startswith('ERROR'):
    print("JS syntax error after fix:", result.stdout)
else:
    print("JS syntax check: PASSED")
