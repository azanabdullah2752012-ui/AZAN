#!/bin/bash

# Replace this with your new OpenRouter key
OPENROUTER_KEY="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"

# Create Continue folder if it doesn't exist
mkdir -p ~/.continue

# Write the config.yaml
cat > ~/.continue/config.yaml <<EOL
name: OpenRouter Setup
version: 1.0.0
schema: v1

models:
  - name: OpenRouter DeepSeek
    provider: openai
    model: deepseek/deepseek-coder
    apiBase: https://openrouter.ai/api/v1
    apiKey: $OPENROUTER_KEY
EOL

echo "✅ Continue config created successfully! Now reload VS Code and select OpenRouter DeepSeek in Continue."