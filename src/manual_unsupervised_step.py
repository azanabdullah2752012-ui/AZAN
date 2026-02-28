import sys
import os
import json
import logging
import time

# Add src to path
sys.path.append(os.path.abspath("."))

from src.inshorts_trainer import InShortsTrainer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_unsupervised_cycle():
    print("="*60)
    print("  AZAN Atomic Claim Extraction - Unsupervised Cycle")
    print("="*60)
    
    trainer = InShortsTrainer()
    
    # 1. Scrape latest factual news
    print("\n🌐 SCRAPING LATEST NEWS FEEDS...")
    new_count = trainer.manual_scrape()
    print(f"✅ Scraped {new_count} new articles.")
    
    # 2. Extract claims and train (the Trainer calls dashboard.train_single_example)
    print("\n🧬 EXTRACTING CLAIMS & COMMITTING TO KNOWLEDGE BASE...")
    trained_count = trainer.train_on_latest_news(max_articles=2)
    print(f"✅ Successfully processed {trained_count} training units.")
    
    # 3. Verify results in the training data file
    print("\n📊 VERIFYING KNOWLEDGE DATA...")
    if os.path.exists("data/inshorts_training_data.json"):
        with open("data/inshorts_training_data.json", "r") as f:
            data = json.load(f)
            claims = [d for d in data if d.get("source") == "deterministic_claim"]
            print(f"✅ Found {len(claims)} atomic claims in the training dataset.")
            
            if claims:
                for i, c in enumerate(claims[-2:], 1):
                    print(f"\n   [RECENT CLAIM {i}]")
                    print(f"   Q: {c['question']}")
                    print(f"   A: {c['ideal_answer']}")
                    print(f"   Confidence: {c.get('metadata', {}).get('confidence')}")
    
    print("\n" + "="*60)
    print("  CYCLE COMPLETE.")

if __name__ == "__main__":
    run_unsupervised_cycle()
