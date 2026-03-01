#!/usr/bin/env python3
"""
AZAN RL System Verification Script
Verifies all components are working correctly
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def verify_files():
    """Verify all required files exist"""
    logger.info("\n📁 Checking File Structure...")
    
    required_files = [
        'src/azan_rl_pipeline.py',
        'src/azan_rl_inference.py',
        'src/azan_dashboard.py',
        'src/math_engine.py',
        'src/physics_engine.py',
        'src/task_executor.py',
        'webui/app.py',
        'data/azan_knowledge_base.json'
    ]
    
    all_exist = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            logger.info(f"  ✅ {file} ({size:.1f}KB)")
        else:
            logger.error(f"  ❌ {file} MISSING")
            all_exist = False
    
    return all_exist


def verify_imports():
    """Verify all imports work"""
    logger.info("\n📦 Verifying Imports...")
    
    imports = [
        ('src.azan_rl_pipeline', ['RLTrainingEngine', 'AutomatedRLTrainer', 'CuratedKnowledgeBase']),
        ('src.azan_rl_inference', ['DataOnlyInferenceEngine']),
        ('src.azan_dashboard', ['get_dashboard']),
        ('src.math_engine', ['MathEngine', 'get_math_engine']),
        ('src.physics_engine', ['PhysicsEngine', 'get_physics_engine']),
        ('src.task_executor', ['execute_task']),
    ]
    
    all_ok = True
    for module_name, classes in imports:
        try:
            module = __import__(module_name, fromlist=classes)
            for class_name in classes:
                if hasattr(module, class_name):
                    logger.info(f"  ✅ {module_name}.{class_name}")
                else:
                    logger.error(f"  ❌ {module_name}.{class_name} NOT FOUND")
                    all_ok = False
        except Exception as e:
            logger.error(f"  ❌ {module_name}: {e}")
            all_ok = False
    
    return all_ok


def verify_knowledge_base():
    """Verify knowledge base is valid"""
    logger.info("\n📚 Verifying Knowledge Base...")
    
    try:
        with open('data/azan_knowledge_base.json', 'r') as f:
            kb = json.load(f)
        
        logger.info(f"  ✅ Knowledge base loaded: {len(kb)} items")
        
        # Check structure
        required_fields = ['id', 'source', 'category', 'title', 'content', 'key_terms']
        
        for i, item in enumerate(kb[:3]):  # Check first 3
            missing = [f for f in required_fields if f not in item]
            if missing:
                logger.error(f"  ❌ Item {i} missing fields: {missing}")
                return False
            logger.info(f"  ✅ Item {i}: {item['source']} - {item['title']}")
        
        if len(kb) > 3:
            logger.info(f"  ✅ ... and {len(kb)-3} more items")
        
        # Check sources and categories
        sources = set(item.get('source') for item in kb)
        categories = set(item.get('category') for item in kb)
        
        logger.info(f"  ✅ Sources: {', '.join(sources)}")
        logger.info(f"  ✅ Categories: {', '.join(categories)}")
        
        return True
    except Exception as e:
        logger.error(f"  ❌ Error loading knowledge base: {e}")
        return False


def verify_rl_engine():
    """Verify RL training engine"""
    logger.info("\n🎓 Verifying RL Training Engine...")
    
    try:
        from src.azan_rl_pipeline import RLTrainingEngine, CuratedKnowledgeBase
        
        # Initialize engine
        engine = RLTrainingEngine()
        logger.info(f"  ✅ RLTrainingEngine initialized")
        
        # Check knowledge base
        if len(engine.kb.knowledge_items) > 0:
            logger.info(f"  ✅ Knowledge base: {len(engine.kb.knowledge_items)} items")
        else:
            logger.error(f"  ❌ Knowledge base is empty")
            return False
        
        # Check metrics
        metrics = engine.get_metrics()
        logger.info(f"  ✅ Iteration: {metrics['iteration']}")
        logger.info(f"  ✅ Total Reward: {metrics['total_reward']:.2f}")
        logger.info(f"  ✅ Avg Reward: {metrics['avg_reward']:.2f}")
        logger.info(f"  ✅ Total Learned: {metrics['total_learned']}")
        
        # Try one training iteration
        result = engine.train_iteration()
        if 'reward' in result:
            logger.info(f"  ✅ Training iteration successful: reward={result['reward']}")
        else:
            logger.error(f"  ❌ Training iteration failed")
            return False
        
        return True
    except Exception as e:
        logger.error(f"  ❌ Error with RL engine: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_inference_engine():
    """Verify inference engine"""
    logger.info("\n🔍 Verifying Inference Engine...")
    
    try:
        from src.azan_rl_inference import DataOnlyInferenceEngine
        
        # Initialize
        engine = DataOnlyInferenceEngine()
        logger.info(f"  ✅ DataOnlyInferenceEngine initialized")
        
        # Check data
        if len(engine.knowledge_items) > 0:
            logger.info(f"  ✅ Knowledge items: {len(engine.knowledge_items)}")
        else:
            logger.error(f"  ❌ No knowledge items loaded")
            return False
        
        # Test search
        results = engine.search_knowledge("constitution")
        logger.info(f"  ✅ Search test: found {len(results)} results")
        
        # Test categories
        categories = engine.get_categories()
        logger.info(f"  ✅ Categories: {len(categories)} categories")
        
        # Test sources
        sources = engine.get_sources()
        logger.info(f"  ✅ Sources: {len(sources)} sources")
        
        # Test stats
        stats = engine.get_stats()
        logger.info(f"  ✅ Stats: {stats['total_knowledge_items']} items, {stats['total_qa_pairs']} Q&A pairs")
        
        return True
    except Exception as e:
        logger.error(f"  ❌ Error with inference engine: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_dashboard():
    """Verify dashboard HTML"""
    logger.info("\n🎨 Verifying Dashboard...")
    
    try:
        from src.azan_dashboard import get_dashboard
        
        html = get_dashboard()
        
        if len(html) > 1000:
            logger.info(f"  ✅ Dashboard HTML: {len(html)} bytes")
        else:
            logger.error(f"  ❌ Dashboard HTML too small")
            return False
        
        if 'AZAN RL Training Dashboard' in html:
            logger.info(f"  ✅ Dashboard title found")
        else:
            logger.error(f"  ❌ Dashboard title not found")
            return False
        
        if 'api/azan/rl/status' in html:
            logger.info(f"  ✅ API endpoints configured")
        else:
            logger.error(f"  ❌ API endpoints not found")
            return False
        
        return True
    except Exception as e:
        logger.error(f"  ❌ Error with dashboard: {e}")
        return False


def verify_math_engine():
    """Verify symbolic math engine"""
    logger.info("\n📐 Verifying Math Engine...")
    try:
        from src.math_engine import get_math_engine
        engine = get_math_engine()
        
        # Test 1: Simplify
        res = engine.solve("x^2 + 2x + 1", task="simplify")
        if "(x + 1)**2" in res['result'] or "x**2 + 2*x + 1" in res['result']:
            logger.info(f"  ✅ Simplify test passed: {res['result']}")
        else:
            logger.warning(f"  ⚠️ Simplify test returned unexpected result: {res['result']}")

        # Test 2: Differentiate
        res = engine.solve("diff x^3", task="auto")
        if "3*x**2" in res['result']:
            logger.info("  ✅ Differentiate test passed")
        else:
            logger.error(f"  ❌ Differentiate test failed: {res['result']}")
            return False

        # Test 3: Solve Equation
        res = engine.solve("solve x^2 - 4 = 0", task="auto")
        if "-2" in res['result'] and "2" in res['result']:
            logger.info("  ✅ Equation solver test passed")
        else:
            logger.error(f"  ❌ Equation solver test failed: {res['result']}")
            return False

        return True
    except Exception as e:
        logger.error(f"  ❌ Math engine error: {e}")
        return False


def verify_physics_engine():
    """Verify symbolic physics engine"""
    logger.info("\n🔬 Verifying Physics Engine...")
    try:
        from src.physics_engine import get_physics_engine
        engine = get_physics_engine()
        
        # Test 1: Kinematics
        res = engine.solve("v=20 u=0 t=5 find a", domain="kinematics")
        if "4.0" in res['result']:
            logger.info(f"  ✅ Kinematics test passed: {res['result']}")
        else:
            logger.error(f"  ❌ Kinematics test failed: {res['result']}")
            return False

        # Test 2: Unit Conversion
        res = engine.solve("convert 100 celsius to fahrenheit", domain="unit_convert")
        if "212" in res['result']:
            logger.info(f"  ✅ Unit conversion test passed: {res['result']}")
        else:
            logger.error(f"  ❌ Unit conversion test failed: {res['result']}")
            return False

        return True
    except Exception as e:
        logger.error(f"  ❌ Physics engine error: {e}")
        return False


def verify_app_integration():
    """Verify FastAPI app integration"""
    logger.info("\n🌐 Verifying FastAPI Integration...")
    
    try:
        # Check if app.py imports are correct
        with open('webui/app.py', 'r') as f:
            app_content = f.read()
        
        required_imports = [
            'from src.azan_rl_pipeline import',
            'from src.azan_rl_inference import',
            '@app.get("/azan-dashboard"',
            '@app.get("/api/azan/rl/status")',
            '@app.post("/api/azan/rl/start")',
            '@app.post("/api/azan/rl/stop")',
            '@app.get("/api/azan/search")',
            '@app.post("/api/azan/infer")',
        ]
        
        all_found = True
        for import_str in required_imports:
            if import_str in app_content:
                logger.info(f"  ✅ Found: {import_str[:50]}...")
            else:
                logger.error(f"  ❌ Missing: {import_str}")
                all_found = False
        
        return all_found
    except Exception as e:
        logger.error(f"  ❌ Error checking app.py: {e}")
        return False


def run_all_checks():
    """Run all verification checks"""
    logger.info("=" * 60)
    logger.info("AZAN RL System Verification")
    logger.info("=" * 60)
    
    checks = [
        ("File Structure", verify_files),
        ("Import System", verify_imports),
        ("Knowledge Base", verify_knowledge_base),
        ("RL Engine", verify_rl_engine),
        ("Inference Engine", verify_inference_engine),
        ("Math Engine", verify_math_engine),
        ("Physics Engine", verify_physics_engine),
        ("Dashboard", verify_dashboard),
        ("App Integration", verify_app_integration),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            logger.error(f"\n❌ {name} check failed with exception: {e}")
            results[name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_check in results.items():
        status = "✅ PASS" if passed_check else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 60)
    logger.info(f"Result: {passed}/{total} checks passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("\n✅ ALL CHECKS PASSED! AZAN RL System is ready to use.\n")
        logger.info("Next steps:")
        logger.info("1. Start server: python -m uvicorn webui.app:app --reload --port 8000")
        logger.info("2. Open dashboard: http://localhost:8000/azan-dashboard")
        logger.info("3. Read guides: AZAN_QUICKSTART.md or AZAN_RL_GUIDE.md")
        return True
    else:
        logger.error("\n❌ Some checks failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    import sys
    success = run_all_checks()
    sys.exit(0 if success else 1)
