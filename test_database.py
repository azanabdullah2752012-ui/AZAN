"""
Test script for AZAN SQLite Database Layer.
Validates all CRUD operations for Phase 2 persistence.

Usage:
    cd /Applications/AZAN && python test_database.py
"""

import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import DatabaseManager

passed = 0
failed = 0


def test(name, condition):
    global passed, failed
    if condition:
        print(f"  ✅ PASS: {name}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name}")
        failed += 1


def run_tests():
    # Use a temporary database file
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    db = DatabaseManager(db_path=db_path)
    test("Database initializes", db.initialized)

    # === Sessions ===
    print("\n📂 Sessions")
    db.ensure_session("sess_1", "Hello, AZAN!")
    db.ensure_session("sess_2", "What is machine learning?")
    sessions = db.get_all_sessions()
    test("Two sessions created", len(sessions) == 2)
    test("Session title from first message", sessions[0]["title"] in ["Hello, AZAN!", "What is machine learning?"])

    # Ensure existing session updates last_activity (not duplicate)
    db.ensure_session("sess_1", "Ignored second title")
    sessions = db.get_all_sessions()
    test("Duplicate ensure_session does not create extra row", len(sessions) == 2)

    # === Chat History ===
    print("\n💬 Chat History")
    db.add_chat_message("sess_1", "user", "Hello!", "llama3")
    db.add_chat_message("sess_1", "azan", "Hi there!", "llama3")
    db.add_chat_message("sess_1", "user", "How are you?", "llama3")
    history = db.get_chat_history("sess_1")
    test("Three messages stored", len(history) == 3)
    test("First message is user", history[0]["role"] == "user")
    test("Second message is azan", history[1]["role"] == "azan")

    # Auto-creates session for unknown session_id
    db.add_chat_message("sess_auto", "user", "Auto-created session test", "llama3")
    sessions = db.get_all_sessions()
    test("Auto-created session via add_chat_message", len(sessions) == 3)

    # Session message count via get_all_sessions
    sess_1_row = [s for s in sessions if s["session_id"] == "sess_1"][0]
    test("Session message_count is correct", sess_1_row["message_count"] == 3)

    # === Delete Session (Cascade) ===
    print("\n🗑️  Delete Session")
    db.delete_session("sess_1")
    sessions = db.get_all_sessions()
    test("Session deleted", all(s["session_id"] != "sess_1" for s in sessions))
    history = db.get_chat_history("sess_1")
    test("Chat history cascade-deleted", len(history) == 0)

    # === Training Pairs ===
    print("\n📚 Training Pairs")
    pair_id = db.insert_training_pair("What is AI?", "Artificial Intelligence is...", "technology")
    test("Training pair inserted", pair_id is not None)
    updated = db.update_pair_reward(pair_id, 4.5, 10)
    test("Training pair reward updated", updated)
    pairs = db.get_training_pairs()
    test("Training pair retrievable", len(pairs) == 1 and pairs[0]["reward"] == 4.5)

    # === Articles ===
    print("\n📰 Articles")
    inserted = db.insert_article({
        "id": "art_1",
        "headline": "AI Breakthrough",
        "body": "Researchers have achieved...",
        "source": "TechCrunch",
        "category": "technology",
        "link": "https://example.com",
        "published_at": "2026-02-28",
    })
    test("Article inserted", inserted)
    articles = db.get_articles(category="technology")
    test("Article retrievable by category", len(articles) == 1)
    # Duplicate insert should be ignored
    db.insert_article({"id": "art_1", "headline": "Duplicate", "body": "", "source": "", "category": "", "link": "", "published_at": ""})
    articles = db.get_articles()
    test("Duplicate article ignored", len(articles) == 1)

    # === Feedback ===
    print("\n⭐ Feedback")
    fb_ok = db.insert_feedback("fb_1", "interaction_1", 5, "Great!", "user_1")
    test("Feedback inserted", fb_ok)
    db.insert_feedback("fb_2", "interaction_1", 4, "Good", "user_2")
    db.insert_feedback("fb_3", "interaction_2", 2, "Poor", "user_1")
    feedbacks = db.get_feedback_for_interaction("interaction_1")
    test("Feedback query by interaction", len(feedbacks) == 2)
    stats = db.get_feedback_stats()
    test("Feedback stats - total", stats["total_ratings"] == 3)
    test("Feedback stats - avg rating", 3.0 < stats["average_rating"] < 5.0)
    test("Feedback stats - by_rating keys", "5" in stats["by_rating"])

    # === Database Summary ===
    print("\n📊 Database Summary")
    summary = db.get_db_summary()
    test("Summary has all tables", "sessions" in summary and "chat_history" in summary)
    test("Summary db_path set", "db_path" in summary)
    test("Summary db_size_kb set", summary["db_size_kb"] > 0)

    # Cleanup
    os.unlink(db_path)

    # === Final Report ===
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed.")
    print(f"{'=' * 50}")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
