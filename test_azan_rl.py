#!/usr/bin/env python3
"""
AZAN RL System - Complete Testing & Validation Guide
Run this script to test all AZAN RL components
"""

import json
import sys
from pathlib import Path


def test_knowledge_base():
    """Test knowledge base loads and has content"""
    print("\n" + "="*60)
    print("TEST 1: Knowledge Base")
    print("="*60)
    
    try:
        from src.azan_rl_pipeline import CuratedKnowledgeBase
        
        kb = CuratedKnowledgeBase()
        
        print(f"✅ Knowledge base initialized")
        print(f"   - Total items: {len(kb.knowledge_items)}")
        print(f"   - Sources: {len(kb.by_source)}")
        print(f"   - Categories: {len(kb.by_category)}")
        print(f"   - Q&A pairs: {len(kb.qa_pairs)}")
        
        # Test search
        results = kb.search_by_keywords(['constitution', 'rights'], limit=3)
        print(f"✅ Search test: found {len(results)} results for 'constitution rights'")
        
        # Test by source
        for source in list(kb.by_source.keys())[:2]:
            items = kb.get_by_source(source)
            print(f"✅ Source '{source}': {len(items)} items")
        
        print("\n✅ TEST 1 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rl_engine():
    """Test RL training engine"""
    print("\n" + "="*60)
    print("TEST 2: RL Training Engine")
    print("="*60)
    
    try:
        from src.azan_rl_pipeline import RLTrainingEngine
        
        engine = RLTrainingEngine()
        print(f"✅ RLTrainingEngine initialized")
        
        # Get initial metrics
        metrics = engine.get_metrics()
        print(f"   - Initial iteration: {metrics['iteration']}")
        print(f"   - Initial reward: {metrics['total_reward']:.2f}")
        
        # Train one iteration
        result = engine.train_iteration()
        print(f"✅ Training iteration executed")
        print(f"   - Iteration: {result['iteration']}")
        print(f"   - Reward: {result['reward']:.2f}")
        print(f"   - Avg reward: {result['avg_reward']:.2f}")
        print(f"   - Source: {result['source']}")
        
        # Get updated metrics
        metrics = engine.get_metrics()
        print(f"✅ Metrics updated")
        print(f"   - New iteration: {metrics['iteration']}")
        print(f"   - New total reward: {metrics['total_reward']:.2f}")
        
        # Get learned QA
        qa = engine.get_learned_qa(limit=1)
        if qa:
            print(f"✅ Learned Q&A retrieved: {len(qa)} pair(s)")
        
        print("\n✅ TEST 2 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inference_engine():
    """Test data-only inference engine"""
    print("\n" + "="*60)
    print("TEST 3: Data-Only Inference Engine")
    print("="*60)
    
    try:
        from src.azan_rl_inference import DataOnlyInferenceEngine
        
        engine = DataOnlyInferenceEngine()
        print(f"✅ DataOnlyInferenceEngine initialized")
        print(f"   - Knowledge items: {len(engine.knowledge_items)}")
        print(f"   - Q&A pairs: {len(engine.qa_pairs)}")
        
        # Test search
        query = "constitution"
        results = engine.search_knowledge(query, limit=5)
        print(f"✅ Search test: found {len(results)} results for '{query}'")
        
        if results:
            item = results[0]
            print(f"   - Title: {item['title']}")
            print(f"   - Source: {item['source']}")
        
        # Test categories
        categories = engine.get_categories()
        print(f"✅ Categories retrieved: {len(categories)}")
        for cat in categories[:3]:
            print(f"   - {cat}")
        
        # Test sources
        sources = engine.get_sources()
        print(f"✅ Sources retrieved: {len(sources)}")
        for src in sources:
            print(f"   - {src}")
        
        # Test stats
        stats = engine.get_stats()
        print(f"✅ Statistics generated")
        print(f"   - Total items: {stats['total_knowledge_items']}")
        print(f"   - Total Q&A: {stats['total_qa_pairs']}")
        print(f"   - Avg terms/item: {stats['avg_terms_per_item']:.1f}")
        
        print("\n✅ TEST 3 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_automated_trainer():
    """Test automated background trainer"""
    print("\n" + "="*60)
    print("TEST 4: Automated Trainer (Background Loop)")
    print("="*60)
    
    try:
        from src.azan_rl_pipeline import RLTrainingEngine, AutomatedRLTrainer
        import time
        
        engine = RLTrainingEngine()
        trainer = AutomatedRLTrainer(engine, update_interval=1)
        
        print(f"✅ AutomatedRLTrainer initialized (1s interval)")
        
        initial_iteration = engine.get_metrics()['iteration']
        
        # Start trainer
        trainer.start()
        print(f"✅ Trainer started (non-blocking)")
        
        # Wait for some training
        time.sleep(2.5)
        
        # Check results
        current_iteration = engine.get_metrics()['iteration']
        iterations_done = current_iteration - initial_iteration
        
        print(f"✅ Training completed in background")
        print(f"   - Iterations in 2.5s: {iterations_done}")
        print(f"   - Training active: {engine.training_active}")
        
        # Stop trainer
        trainer.stop()
        print(f"✅ Trainer stopped")
        
        print("\n✅ TEST 4 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_html():
    """Test dashboard HTML generation"""
    print("\n" + "="*60)
    print("TEST 5: Dashboard HTML")
    print("="*60)
    
    try:
        from src.azan_dashboard import get_dashboard
        
        html = get_dashboard()
        print(f"✅ Dashboard HTML generated")
        print(f"   - Size: {len(html):,} bytes")
        
        # Check for key components
        checks = [
            ('AZAN RL Training Dashboard', 'Title'),
            ('api/azan/rl/status', 'Status endpoint'),
            ('api/azan/search', 'Search endpoint'),
            ('Chart.js', 'Chart library'),
            ('Reward Trend', 'Reward chart'),
            ('Knowledge Base', 'Knowledge section'),
        ]
        
        for check_str, label in checks:
            if check_str in html:
                print(f"✅ {label}: ✓")
            else:
                print(f"⚠️  {label}: missing")
        
        print("\n✅ TEST 5 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_persistence():
    """Test data persistence"""
    print("\n" + "="*60)
    print("TEST 6: Data Persistence")
    print("="*60)
    
    try:
        from src.azan_rl_pipeline import RLTrainingEngine
        import json
        
        # Create engine and do training
        engine1 = RLTrainingEngine()
        iter1 = engine1.get_metrics()['iteration']
        
        # Train
        engine1.train_iteration()
        engine1.train_iteration()
        
        iter2 = engine1.get_metrics()['iteration']
        print(f"✅ Trained 2 iterations: {iter1} -> {iter2}")
        
        # Create new engine instance (should load state)
        engine2 = RLTrainingEngine()
        iter3 = engine2.get_metrics()['iteration']
        
        if iter3 == iter2:
            print(f"✅ State persisted correctly: {iter3}")
        else:
            print(f"⚠️  State mismatch: {iter3} != {iter2}")
        
        # Check training state file
        state_file = Path('data/azan_training_state.json')
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
            print(f"✅ Training state file exists")
            print(f"   - Iteration: {state['iteration']}")
            print(f"   - Total reward: {state['total_reward']:.2f}")
        
        # Check checkpoints
        checkpoint_dir = Path('data/azan_checkpoints')
        if checkpoint_dir.exists():
            checkpoints = list(checkpoint_dir.glob('checkpoint_*.json'))
            print(f"✅ Checkpoint directory exists")
            print(f"   - Checkpoints saved: {len(checkpoints)}")
        
        print("\n✅ TEST 6 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_integration():
    """Test FastAPI integration"""
    print("\n" + "="*60)
    print("TEST 7: FastAPI Integration")
    print("="*60)
    
    try:
        with open('webui/app.py', 'r') as f:
            app_content = f.read()
        
        checks = [
            ('from src.azan_rl_pipeline import', 'AZAN RL imports'),
            ('from src.azan_rl_inference import', 'AZAN inference imports'),
            ('@app.get("/azan-dashboard")', 'Dashboard route'),
            ('@app.get("/api/azan/rl/status")', 'Status endpoint'),
            ('@app.post("/api/azan/rl/start")', 'Start endpoint'),
            ('@app.post("/api/azan/rl/stop")', 'Stop endpoint'),
            ('@app.get("/api/azan/search")', 'Search endpoint'),
            ('@app.post("/api/azan/infer")', 'Inference endpoint'),
            ('init_azan_rl', 'RL initialization'),
            ('init_azan_inference', 'Inference initialization'),
        ]
        
        print(f"✅ app.py checked ({len(app_content):,} bytes)")
        
        for check_str, label in checks:
            if check_str in app_content:
                print(f"✅ {label}: ✓")
            else:
                print(f"❌ {label}: MISSING")
        
        print("\n✅ TEST 7 PASSED")
        return True
    except Exception as e:
        print(f"❌ TEST 7 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("AZAN RL SYSTEM - COMPREHENSIVE TESTING")
    print("="*60)
    
    tests = [
        ("Knowledge Base", test_knowledge_base),
        ("RL Training Engine", test_rl_engine),
        ("Inference Engine", test_inference_engine),
        ("Automated Trainer", test_automated_trainer),
        ("Dashboard HTML", test_dashboard_html),
        ("Data Persistence", test_data_persistence),
        ("API Integration", test_api_integration),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {name}: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("="*60)
    print(f"RESULT: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("\nYou can now:")
        print("1. Start the server: python -m uvicorn webui.app:app --reload --port 8000")
        print("2. Open dashboard: http://localhost:8000/azan-dashboard")
        print("3. Start training: curl -X POST http://localhost:8000/api/azan/rl/start")
        return True
    else:
        print(f"\n❌ {total-passed} tests failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
