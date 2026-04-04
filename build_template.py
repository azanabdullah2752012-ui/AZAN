import sys
sys.path.insert(0, '/Applications/AZAN/webui')

# Execute just the variable definitions from template.py
with open('/Applications/AZAN/webui/template.py', 'r') as f:
    src = f.read()

# Only execute up to and not including any prior TEMPLATE= line
cut_at = src.find('\n\nTEMPLATE')
if cut_at == -1:
    cut_at = len(src)
code = src[:cut_at]

ns = {}
exec(code, ns)
CSS = ns['CSS']
BODY_HTML = ns['BODY_HTML']
JS = ns['JS']

# Build the TEMPLATE string
TEMPLATE = (
    "<!DOCTYPE html>\n"
    '<html lang="en" data-theme="dark">\n'
    "<head>\n"
    '<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    "<title>AZAN AI Chat</title>\n"
    '<meta name="description" content="AZAN — AI assistant powered by RL knowledge, semantic RAG, and autonomous agents.">\n'
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">\n'
    '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">\n'
    '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>\n'
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>\n'
    "<style>" + CSS + "</style>\n"
    "</head>\n"
    "<body>\n"
    + BODY_HTML +
    "\n<script>\n"
    + JS +
    "\n</script>\n"
    "</body>\n"
    "</html>"
)

# Append clean TEMPLATE to template.py (removing old attempt)
final = code + "\n\nTEMPLATE = " + repr(TEMPLATE) + "\n"
with open('/Applications/AZAN/webui/template.py', 'w') as f:
    f.write(final)

print("OK - TEMPLATE written. Size:", len(TEMPLATE))
