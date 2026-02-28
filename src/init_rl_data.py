"""
Initialize RL Training Data from Inshorts Articles
Converts verified articles into RL training pairs
"""

import json
import os
from pathlib import Path

def initialize_rl_training_data():
    """Convert Inshorts articles to RL training data"""
    
    articles_file = Path("data/inshorts_articles.json")
    rl_training_file = Path("data/rl_training_data.json")
    
    if not articles_file.exists():
        print("❌ inshorts_articles.json not found")
        return
    
    # Load articles
    with open(articles_file, 'r') as f:
        articles_dict = json.load(f)
    
    print(f"📚 Found {len(articles_dict)} articles")
    
    # Convert to training pairs
    training_pairs = []
    
    for article_hash, article in articles_dict.items():
        headline = article.get('headline', '')
        body = article.get('body', '')
        category = article.get('category', 'unknown')
        
        if not headline or not body:
            continue
        
        # Generate Q&A pairs from article
        qa_pairs = [
            {
                "timestamp": article.get('timestamp', ''),
                "question": f"What's the latest news in {category}?",
                "answer": f"{headline}: {body}",
                "category": category,
                "reward": 3.5
            },
            {
                "timestamp": article.get('timestamp', ''),
                "question": f"Tell me about: {headline[:40]}...",
                "answer": body,
                "category": category,
                "reward": 3.7
            },
            {
                "timestamp": article.get('timestamp', ''),
                "question": f"What is significant about {headline[:30]}...?",
                "answer": f"This story is significant because: {body[:150]}...",
                "category": category,
                "reward": 3.3
            }
        ]
        
        training_pairs.extend(qa_pairs)
    
    # Save training pairs
    with open(rl_training_file, 'w') as f:
        json.dump(training_pairs, f, indent=2)
    
    print(f"✅ Created {len(training_pairs)} RL training pairs")
    print(f"📁 Saved to: {rl_training_file}")
    
    # Also create initial rewards file
    rewards_file = Path("data/rl_rewards.json")
    rewards = []
    for pair in training_pairs:
        rewards.append({
            "timestamp": pair.get('timestamp', ''),
            "reward": pair.get('reward', 3.5),
            "category": pair.get('category', 'unknown')
        })
    
    with open(rewards_file, 'w') as f:
        json.dump(rewards, f, indent=2)
    
    print(f"✅ Created {len(rewards)} reward records")
    print(f"📁 Saved to: {rewards_file}")


if __name__ == "__main__":
    initialize_rl_training_data()
