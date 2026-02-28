#!/usr/bin/env python3
"""
AZAN RL System - Configuration Guide

This script helps you customize and configure the AZAN RL system
for your specific needs.
"""

import json
from pathlib import Path


def configure_training_interval():
    """Configure training interval"""
    print("\n" + "="*60)
    print("STEP 1: Configure Training Interval")
    print("="*60)
    
    print("""
The training interval determines how often AZAN trains (in seconds).

Default: 30 seconds
- Fast learning (1 iteration every 30 seconds)
- ~120 iterations per hour
- Good for development

Recommended for production: 60 seconds
- ~60 iterations per hour
- Lower CPU usage
- Smoother operation

You can change this in webui/app.py, startup event:
    engine, trainer = init_azan_rl(update_interval=30)  # Change this number

Options:
- 10 seconds: Very aggressive (for testing)
- 30 seconds: Default (recommended for development)
- 60 seconds: Balanced (recommended for production)
- 300 seconds: Conservative (1 iteration per 5 minutes)
""")
    
    interval = input("Enter desired interval (seconds) [default 30]: ").strip()
    if interval:
        return int(interval)
    return 30


def add_knowledge():
    """Add custom knowledge to knowledge base"""
    print("\n" + "="*60)
    print("STEP 2: Add Custom Knowledge")
    print("="*60)
    
    kb_file = Path('data/azan_knowledge_base.json')
    
    if not kb_file.exists():
        print("Knowledge base not found. Creating new one...")
        kb = []
    else:
        with open(kb_file, 'r') as f:
            kb = json.load(f)
    
    print(f"\nCurrent knowledge base has {len(kb)} items")
    
    add_more = input("\nAdd new knowledge items? (y/n) [default n]: ").strip().lower()
    if add_more != 'y':
        return
    
    print("\nEnter knowledge items (leave 'id' blank to auto-generate):")
    print("Format: id | source | category | title | content | keywords")
    print("Example: ic_004 | Indian Constitution | fundamental_rights | Right to Life | Article 21 states... | life, liberty, security")
    print("\nEnter 'done' when finished.\n")
    
    next_id = max([int(item.get('id', '0').split('_')[-1]) for item in kb if '_' in item.get('id', '0')], default=0) + 1
    
    while True:
        entry = input(f"[{next_id}] ").strip()
        
        if entry.lower() == 'done':
            break
        
        if not entry:
            continue
        
        parts = [p.strip() for p in entry.split('|')]
        
        if len(parts) < 5:
            print("❌ Need at least: source, category, title, content, keywords")
            continue
        
        item = {
            'id': parts[0] or f'custom_{next_id:03d}',
            'source': parts[1],
            'category': parts[2],
            'title': parts[3],
            'content': parts[4],
            'key_terms': [t.strip() for t in parts[5].split(',')]
        }
        
        kb.append(item)
        print(f"✅ Added: {item['title']}")
        next_id += 1
    
    # Save knowledge base
    with open(kb_file, 'w') as f:
        json.dump(kb, f, indent=2)
    
    print(f"\n✅ Knowledge base saved: {len(kb)} items")


def configure_inference():
    """Configure inference settings"""
    print("\n" + "="*60)
    print("STEP 3: Configure Inference Settings")
    print("="*60)
    
    print("""
Configure how AZAN responds to queries:

Similarity Threshold:
- Higher (>30%): More conservative, fewer but more relevant results
- Lower (<10%): More aggressive, returns more results

Default: >10% similarity
Recommended: Keep default for data-only mode

Source Citation:
- Always include source (recommended)
- Optional source

Confidence Scoring:
- High: When sources found (>2 matches)
- Medium: When some sources found (1-2 matches)
- Low: When no direct sources (using fallback)

These settings are in src/azan_rl_inference.py
""")
    
    config = {
        'similarity_threshold': 0.1,
        'require_sources': True,
        'confidence_mapping': {
            'high': 'sources_found',
            'medium': 'partial_match',
            'low': 'fallback'
        }
    }
    
    return config


def configure_knowledge_sources():
    """Configure knowledge sources"""
    print("\n" + "="*60)
    print("STEP 4: Select Knowledge Sources")
    print("="*60)
    
    sources = [
        ('Indian Constitution', 'constitutional_framework'),
        ('UN Charter', 'international_law'),
        ('UN Declaration of Human Rights', 'international_law'),
        ('Military Strategy', 'military_doctrine'),
        ('Modern Military Doctrine', 'military_doctrine'),
        ('Political Definitions', 'political_economy'),
    ]
    
    print("\nAvailable knowledge sources:")
    for i, (source, category) in enumerate(sources, 1):
        print(f"{i}. {source} ({category})")
    
    print("\nDefault: All sources are enabled")
    print("To disable a source, edit data/azan_knowledge_base.json")
    print("and remove items with that source.")


def show_knowledge_stats():
    """Show current knowledge statistics"""
    print("\n" + "="*60)
    print("STEP 5: Knowledge Base Statistics")
    print("="*60)
    
    kb_file = Path('data/azan_knowledge_base.json')
    
    if not kb_file.exists():
        print("Knowledge base not found")
        return
    
    with open(kb_file, 'r') as f:
        kb = json.load(f)
    
    # Count by source
    by_source = {}
    by_category = {}
    
    for item in kb:
        source = item.get('source', 'unknown')
        category = item.get('category', 'unknown')
        
        by_source[source] = by_source.get(source, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1
    
    print(f"\nTotal knowledge items: {len(kb)}")
    print(f"\nBy Source:")
    for source, count in sorted(by_source.items()):
        print(f"  - {source}: {count} items")
    
    print(f"\nBy Category:")
    for category, count in sorted(by_category.items()):
        print(f"  - {category}: {count} items")
    
    # Check quality
    quality_issues = []
    for item in kb:
        if not item.get('content'):
            quality_issues.append(f"Item {item['id']}: Missing content")
        if not item.get('key_terms'):
            quality_issues.append(f"Item {item['id']}: Missing key terms")
    
    if quality_issues:
        print(f"\n⚠️  Quality issues found:")
        for issue in quality_issues[:5]:
            print(f"  - {issue}")
    else:
        print(f"\n✅ No quality issues found")


def configure_api_parameters():
    """Configure API parameters"""
    print("\n" + "="*60)
    print("STEP 6: API Configuration")
    print("="*60)
    
    print("""
Configure FastAPI settings:

Server Settings (in webui/app.py):
- Host: 0.0.0.0 (listen on all interfaces)
- Port: 8000 (default)
- Reload: True for development, False for production

CORS Settings:
- Allow Origins: * (all origins)
- Allow Methods: * (all methods)
- Allow Headers: * (all headers)

Default settings allow full development access.
For production, restrict CORS origins.

Rate Limiting:
- Currently: No rate limiting
- Can add: Use FastAPI middleware

Default configuration is in webui/app.py startup
""")


def generate_config_file():
    """Generate configuration file"""
    print("\n" + "="*60)
    print("STEP 7: Save Configuration")
    print("="*60)
    
    config = {
        'azan_rl_system': {
            'training_interval': 30,
            'checkpoint_interval': 10,
            'knowledge_source': 'data/azan_knowledge_base.json',
            'training_state_file': 'data/azan_training_state.json',
            'checkpoint_directory': 'data/azan_checkpoints/'
        },
        'inference': {
            'similarity_threshold': 0.1,
            'max_results': 5,
            'source_attribution': True,
            'confidence_scoring': True
        },
        'api': {
            'host': '0.0.0.0',
            'port': 8000,
            'reload': True,
            'cors_origins': ['*']
        },
        'knowledge_sources': [
            'Indian Constitution',
            'UN Charter',
            'UN Declaration of Human Rights',
            'Military Strategy',
            'Modern Military Doctrine',
            'Political Definitions'
        ],
        'categories': [
            'fundamental_rights',
            'international_law',
            'military_doctrine',
            'political_economy',
            'governance'
        ]
    }
    
    config_file = Path('azan_rl_config.json')
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to: {config_file}")
    print("\nYou can now:")
    print("1. Edit azan_rl_config.json for custom settings")
    print("2. Use verify_azan_rl.py to verify setup")
    print("3. Use test_azan_rl.py to test all components")
    print("4. Start server: python -m uvicorn webui.app:app --reload --port 8000")
    print("5. Open dashboard: http://localhost:8000/azan-dashboard")


def main():
    """Main configuration wizard"""
    print("\n" + "="*60)
    print("🎓 AZAN RL SYSTEM - CONFIGURATION WIZARD")
    print("="*60)
    
    print("""
This wizard will help you configure the AZAN RL system for your needs.

You can:
1. Set training interval
2. Add custom knowledge
3. Configure inference
4. View knowledge statistics
5. Configure API
6. Generate configuration file

Let's get started!
""")
    
    # Step by step
    while True:
        print("\n" + "-"*60)
        print("Configuration Menu:")
        print("-"*60)
        print("1. Set training interval")
        print("2. Add custom knowledge")
        print("3. Configure inference")
        print("4. View knowledge statistics")
        print("5. Configure API")
        print("6. Generate configuration file")
        print("7. Exit wizard")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == '1':
            interval = configure_training_interval()
            print(f"✅ Training interval set to {interval} seconds")
        elif choice == '2':
            add_knowledge()
        elif choice == '3':
            config = configure_inference()
            print("✅ Inference configured")
        elif choice == '4':
            show_knowledge_stats()
        elif choice == '5':
            configure_api_parameters()
        elif choice == '6':
            generate_config_file()
        elif choice == '7':
            print("\n✅ Configuration wizard complete!")
            print("\nNext steps:")
            print("1. Verify: python verify_azan_rl.py")
            print("2. Test: python test_azan_rl.py")
            print("3. Start: python -m uvicorn webui.app:app --reload --port 8000")
            break
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()
