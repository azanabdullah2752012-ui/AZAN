"""
AZAN AI Backend Server
Flask server connected to Ollama via the RL-enhanced inference engine.
Serves the frontend and provides chat + knowledge APIs.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path so we can import src modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Import inference engine ──────────────────────────────────────────────────
rl_inference_available = False
try:
    from src.rl_inference import predict as rl_predict, get_inference_engine, initialize_inference
    initialize_inference()
    rl_inference_available = True
    logger.info("✅ RL Inference engine loaded (Ollama + Knowledge Base)")
except Exception as e:
    logger.warning(f"⚠️ RL Inference not available: {e}")

# ── Autonomous Learning Systems ──────────────────────────────────────────────
training_systems_available = False
try:
    from src.inshorts_trainer import get_inshorts_trainer
    from src.auto_training_scheduler import get_scheduler as get_political_scheduler
    training_systems_available = True
    logger.info("✅ Autonomous learning modules imported")
except Exception as e:
    logger.warning(f"⚠️ Could not import training systems: {e}")


def start_autolearning():
    """Start all background autonomous learning loops."""
    if not training_systems_available:
        return
    
    try:
        # 1. Start Inshorts News trainer (scrape every 5m, train every 10m)
        trainer = get_inshorts_trainer()
        trainer.start_continuous_training(scrape_interval=300, training_interval=600)
        logger.info("🚀 Inshorts autonomous training started")
        
        # 2. Start Political Topic scheduler (train every 30m)
        p_scheduler = get_political_scheduler()
        p_scheduler.start()
        logger.info("🚀 Political topic autonomous scheduler started")
    except Exception as e:
        logger.error(f"Failed to start autolearning systems: {e}")


# ── Direct Ollama fallback via httpx ─────────────────────────────────────────
import httpx

OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_CLIENT = httpx.Client(timeout=60.0)


def ollama_direct_chat(prompt: str, model: str = "llama3") -> str:
    """Direct Ollama API call as fallback when RL inference is unavailable."""
    try:
        response = OLLAMA_CLIENT.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are AZAN, an advanced AI assistant. Be helpful, accurate, and concise."
                    },
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {"num_predict": 1024, "temperature": 0.5, "top_p": 0.9}
            }
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "Unable to generate response.")
    except Exception as e:
        logger.error(f"Ollama direct call failed: {e}")
        return f"Error: Could not reach Ollama — {str(e)}"


def check_ollama_status() -> dict:
    """Check if Ollama is running and which models are available."""
    try:
        resp = OLLAMA_CLIENT.get(f"{OLLAMA_HOST}/api/tags")
        resp.raise_for_status()
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return {"online": True, "models": models}
    except Exception:
        return {"online": False, "models": []}


# ── Flask App ────────────────────────────────────────────────────────────────

app = Flask(__name__,
            static_folder='../frontend',
            static_url_path='')
CORS(app)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def serve_index():
    """Serve the main AI chat page."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS)."""
    return send_from_directory(app.static_folder, path)


@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint — routes to RL inference (Ollama + knowledge) or direct Ollama."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body'}), 400

        query = (data.get('query') or data.get('prompt', '')).strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400

        # Try RL-enhanced inference first (Ollama + training data knowledge base)
        if rl_inference_available:
            try:
                response_text = rl_predict(query)
                return jsonify({
                    'response': response_text,
                    'source': 'rl_inference',
                    'model': 'llama3'
                })
            except Exception as e:
                logger.warning(f"RL inference failed, falling back to direct Ollama: {e}")

        # Fallback: direct Ollama call
        response_text = ollama_direct_chat(query)
        return jsonify({
            'response': response_text,
            'source': 'ollama_direct',
            'model': 'llama3'
        })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """Health check — Ollama connectivity + inference engine status."""
    ollama = check_ollama_status()
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ollama': ollama,
        'rl_inference': rl_inference_available,
        'version': '2.1.0'
    })


@app.route('/api/knowledge')
def api_knowledge():
    """Get training data / knowledge base statistics."""
    stats = {
        'total_articles': 0,
        'total_training_pairs': 0,
        'categories': [],
        'articles_per_category': {}
    }

    if rl_inference_available:
        try:
            engine = get_inference_engine()
            stats = engine.get_knowledge_summary()
        except Exception as e:
            logger.warning(f"Could not get knowledge summary: {e}")

    # Also try to get raw data stats
    data_dir = Path(PROJECT_ROOT) / "data"
    data_files = {}
    for f in ["rl_training_data.json", "inshorts_articles.json", "inshorts_training_data.json"]:
        fp = data_dir / f
        if fp.exists():
            try:
                with open(fp) as fh:
                    content = json.load(fh)
                    count = len(content) if isinstance(content, (list, dict)) else 0
                    data_files[f] = count
            except Exception:
                data_files[f] = 0

    stats['data_files'] = data_files
    return jsonify(stats)


@app.route('/api/autolearn/status')
def autolearn_status():
    """Get status of background autonomous learning systems."""
    status = {
        "inshorts": {"running": False},
        "political": {"running": False}
    }
    
    if training_systems_available:
        try:
            trainer = get_inshorts_trainer()
            status["inshorts"] = trainer.get_training_status()
            
            p_scheduler = get_political_scheduler()
            status["political"] = p_scheduler.get_status()
        except Exception as e:
            logger.error(f"Error fetching autolearn status: {e}")
            
    return jsonify(status)


# ── Evaluation Prompt Template ───────────────────────────────────────────────
EVAL_PROMPT_TEMPLATE = """You are the Knowledge Evaluation Core for AZAN AI.

Evaluate whether the AI-generated response below contains durable, reusable, high-value knowledge worth storing in the long-term knowledge base.

Evaluation Criteria:
1. Accuracy (factual reliability)
2. Depth (non-superficial explanation)
3. Clarity (well-structured and understandable)
4. Reusability (useful for future similar queries)
5. Non-triviality (not small talk or generic filler)
6. No hallucination signals
7. Not a refusal or system error message

Scoring Rules:
- Score from 1 to 10.
- 7 or higher qualifies for storage.
- If the response is empty, missing, trivial, or conversational only, set store = false.

Knowledge Types:
- "conceptual"
- "procedural"
- "strategic"
- "factual"

Return STRICT JSON only in this format:
{{
  "store": true or false,
  "score": number,
  "type": "conceptual|procedural|strategic|factual",
  "confidence": number_between_0_and_1,
  "reason": "concise explanation"
}}

Do not include commentary.
Do not include markdown.
Only output valid JSON.

AI RESPONSE TO EVALUATE:
------------------------
{ai_response}
------------------------"""


@app.route('/api/evaluate', methods=['POST'])
def evaluate_response():
    """
    Knowledge Evaluation endpoint.
    Accepts {{\"response\": \"<ai text>\"}} and returns a JSON evaluation
    indicating whether the knowledge is worth storing in the long-term knowledge base.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body'}), 400

        ai_response = (data.get('response') or data.get('ai_response') or '').strip()
        if not ai_response or ai_response in ('{{AI_RESPONSE}}', '{AI_RESPONSE}'):
            return jsonify({
                'store': False,
                'score': 1,
                'type': 'factual',
                'confidence': 0.99,
                'reason': 'Empty or unfilled template placeholder — no content to evaluate.'
            }), 200

        # Build the properly substituted evaluation prompt
        eval_prompt = EVAL_PROMPT_TEMPLATE.format(ai_response=ai_response)

        # Use Ollama with JSON mode for a clean structured output
        try:
            resp = OLLAMA_CLIENT.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": "llama3",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a strict JSON-only evaluator. Only output valid JSON, never commentary."
                        },
                        {"role": "user", "content": eval_prompt}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {"num_predict": 256, "temperature": 0.1}
                },
                timeout=30.0
            )
            resp.raise_for_status()
            raw = resp.json().get("message", {}).get("content", "").strip()

            # Parse the JSON output
            try:
                result = json.loads(raw)
                # Ensure required fields
                result.setdefault("store", False)
                result.setdefault("score", 0)
                result.setdefault("type", "factual")
                result.setdefault("confidence", 0.5)
                result.setdefault("reason", "No reason provided.")
                return jsonify(result)
            except json.JSONDecodeError:
                logger.error(f"Evaluator returned invalid JSON: {raw}")
                return jsonify({
                    'store': False,
                    'score': 0,
                    'type': 'factual',
                    'confidence': 0.0,
                    'reason': f'Evaluator model returned invalid JSON: {raw[:100]}'
                }), 200

        except Exception as e:
            logger.error(f"Evaluation Ollama call failed: {e}")
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Evaluate endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


# ── Claim Extraction Prompt Template ───────────────────────────────────────
CLAIM_EXTRACTION_PROMPT = """You are AZAN’s Deterministic Claim Extraction Engine.

Your task is to extract atomic, independently verifiable factual claims from the provided text.

You must operate with strict precision, zero hallucination, and zero narrative interpretation.

A VALID CLAIM is defined as:
A single, standalone factual statement that:
- Contains one primary fact only
- Can be independently verified
- Preserves exact numbers, dates, and named entities
- Does not rely on surrounding context for clarity

STRICT EXTRACTION RULES:
1. DO NOT include: Opinions, Interpretations, Emotional language, Speculation, Background filler.
2. CLAIM STRUCTURE REQUIREMENTS: Rewrite each claim as a clean, standalone sentence. Preserve numeric values and entity names exactly.
3. TIME HANDLING: Extract YYYY-MM-DD or YYYY if present, else null. Do not infer dates.
4. ENTITY EXTRACTION: Extract named entities (people, organizations, countries, institutions, programs, laws).
5. CONFIDENCE SCORING: 0.9–1.0 (Explicit), 0.7–0.89 (Clear event), 0.5–0.69 (Contextual). Discard below 0.5.
6. DISCARD CONDITIONS: Uncertain, ambiguous, or unverifiable → discard. Split compound facts.

Return STRICT JSON only. No markdown. No explanations.

JSON SCHEMA:
{{
  "claims": [
    {{
      "text": "Standalone factual sentence.",
      "type": "statistic | event | policy | statement | background",
      "entities": ["Entity1", "Entity2"],
      "time_reference": "YYYY-MM-DD | YYYY | null",
      "confidence": 0.0
    }}
  ]
}}

TEXT:
{text}"""


@app.route('/api/extract-claims', methods=['POST'])
def extract_claims():
    """
    Deterministic Claim Extraction endpoint.
    Extracts atomic factual claims from provided text.
    Uses temperature 0 and strict JSON mode.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON body'}), 400

        text = (data.get('text') or data.get('content') or data.get('body', '')).strip()
        if not text or text in ('{{ARTICLE_BODY}}', '{ARTICLE_BODY}'):
            return jsonify({"claims": []}), 200

        # Build prompt
        prompt = CLAIM_EXTRACTION_PROMPT.format(text=text)

        # Call Ollama in JSON mode with Temperature 0
        try:
            resp = OLLAMA_CLIENT.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": "llama3",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a deterministic factual claim extractor. Output only valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 2048
                    }
                },
                timeout=60.0
            )
            resp.raise_for_status()
            raw_response = resp.json().get("message", {}).get("content", "{}")
            
            try:
                claims_data = json.loads(raw_response)
                # Ensure it matches schema
                if "claims" not in claims_data:
                    claims_data = {"claims": []}
                return jsonify(claims_data)
            except json.JSONDecodeError:
                logger.error(f"Claims extractor returned invalid JSON: {raw_response}")
                return jsonify({"claims": [], "error": "Invalid JSON from model"}), 200

        except Exception as e:
            logger.error(f"Claims extraction Ollama call failed: {e}")
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logger.error(f"Extract-claims endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("  AZAN AI Autonomous Backend Server")
    print("  Frontend: http://localhost:8000")
    print("  Chat API: POST http://localhost:8000/chat")
    print("  Autolearn: GET http://localhost:8000/api/autolearn/status")
    print("=" * 60)
    
    # Start autolearning in background
    start_autolearning()
    
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)
