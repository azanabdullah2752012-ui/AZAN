import sys
import os
import json
import logging

# Add src to path
sys.path.append(os.path.abspath("."))

from inshorts_scraper import InshortsScraper

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_scraper_with_claims():
    print("STARTING TEST...")
    scraper = InshortsScraper()
    print("SCRAPER INITIALIZED.")
    
    # Mock an article that would produce clear claims
    test_article = {
        "headline": "SpaceX successfully launched Starship SN30 from Texas on February 28, 2026",
        "body": "The massive rocket reached an altitude of 250km before returning. Elon Musk said this test was a major success for Mars missions.",
        "category": "science",
        "timestamp": "2026-02-28T17:00:00",
        "hash": "test_hash_unique_123"
    }
    
    print("🚀 Triggering Q&A generation with claim extraction...")
    try:
        qa_pairs = scraper._generate_qa_from_article(test_article)
        print(f"\n✅ Total Generated: {len(qa_pairs)} pairs.")
        
        claim_qas = [pa for pa in qa_pairs if pa['source'] == 'deterministic_claim']
        print(f"📊 Claims found: {len(claim_qas)}")
        
        for i, qa in enumerate(claim_qas, 1):
            print(f"\n[Claim {i}]")
            print(f"  Q: {qa['question']}")
            print(f"  A: {qa['ideal_answer']}")
            print(f"  Conf: {qa.get('metadata', {}).get('confidence')}")
            
    except Exception as e:
        print(f"FATAL ERROR in generation: {e}")
        import traceback
        traceback.print_exc()

    print("\nDONE.")

if __name__ == "__main__":
    test_scraper_with_claims()
