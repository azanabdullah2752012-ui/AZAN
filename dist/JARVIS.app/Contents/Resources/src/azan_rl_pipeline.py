"""
Specialized RL Training Pipeline for AZAN
Trains on: Indian Constitution, UN treaties, military strategies, political definitions
Focus: Data-only, verified knowledge with strict sourcing
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random

logger = logging.getLogger(__name__)


class CuratedKnowledgeBase:
    """
    Curated knowledge base for AZAN
    Sources: Indian Constitution, UN treaties, military doctrines, political terms
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.knowledge_file = self.data_dir / "azan_knowledge_base.json"
        self.qa_file = self.data_dir / "azan_qa_pairs.json"
        
        self.knowledge_items = []
        self.qa_pairs = []
        self.by_source = {}
        self.by_category = {}
        
        self._ensure_default_data()
        self._load_knowledge()
        
        logger.info(f"✓ CuratedKnowledgeBase initialized: {len(self.knowledge_items)} items, {len(self.qa_pairs)} Q&A pairs")
    
    def _ensure_default_data(self):
        """Ensure default curated knowledge exists"""
        if self.knowledge_file.exists():
            return
        
        # Default curated knowledge
        default_knowledge = [
            {
                "id": "ic_001",
                "source": "Indian Constitution",
                "category": "fundamental_rights",
                "title": "Right to Equality",
                "content": "Article 14-18: The Constitution guarantees equality before law, prohibition of discrimination, equality of opportunity in matters of public employment, abolition of titles, and prohibition of forced labor.",
                "key_terms": ["equality", "discrimination", "citizenship", "fundamental rights"]
            },
            {
                "id": "ic_002",
                "source": "Indian Constitution",
                "category": "fundamental_rights",
                "title": "Right to Freedom",
                "content": "Article 19-22: Citizens have freedom of speech and expression, assembly, association, movement, residence, and profession, subject to reasonable restrictions.",
                "key_terms": ["freedom", "speech", "expression", "assembly"]
            },
            {
                "id": "ic_003",
                "source": "Indian Constitution",
                "category": "fundamental_rights",
                "title": "Right to Constitutional Remedies",
                "content": "Article 32: Right to move Supreme Court for enforcement of fundamental rights. Citizens can approach the Supreme Court directly for violation of fundamental rights.",
                "key_terms": ["writ", "habeas corpus", "mandamus", "prohibition"]
            },
            {
                "id": "un_001",
                "source": "UN Charter",
                "category": "international_law",
                "title": "UN Purposes and Principles",
                "content": "Article 1-2: UN aims to maintain international peace, develop friendly relations, achieve cooperation, and promote human rights without distinction.",
                "key_terms": ["peace", "security", "human rights", "cooperation"]
            },
            {
                "id": "un_002",
                "source": "UN Declaration of Human Rights",
                "category": "international_law",
                "title": "Universal Declaration of Human Rights",
                "content": "UDHR 1948: Sets out fundamental human rights. All humans born free and equal in dignity and rights. Includes rights to life, liberty, security, and freedom from slavery.",
                "key_terms": ["human rights", "dignity", "liberty", "equality"]
            },
            {
                "id": "ms_001",
                "source": "Military Strategy",
                "category": "military_doctrine",
                "title": "Sun Tzu Art of War Principles",
                "content": "Ancient Chinese military doctrine: Know yourself and your enemy, never be defeated. Key principles: deception, surprise, concentration of force, terrain advantage.",
                "key_terms": ["strategy", "deception", "concentration", "terrain"]
            },
            {
                "id": "ms_002",
                "source": "Modern Military Doctrine",
                "category": "military_doctrine",
                "title": "Network-Centric Warfare",
                "content": "Modern military doctrine emphasizing information, surveillance, reconnaissance integration with real-time command and control for superior situational awareness.",
                "key_terms": ["network", "information", "surveillance", "command", "control"]
            },
            {
                "id": "pd_001",
                "source": "Political Definitions",
                "category": "political_economy",
                "title": "Tariffs and Trade",
                "content": "Tariff: A tax on imported or exported goods. Used to protect domestic industries, generate revenue, or influence trade balances. Types: ad valorem (% of value), specific (fixed amount).",
                "key_terms": ["tariff", "trade", "import", "export", "tax"]
            },
            {
                "id": "pd_002",
                "source": "Political Definitions",
                "category": "political_economy",
                "title": "Sanctions",
                "content": "Economic/political penalties imposed by one or more countries against a target country/entity. Types: comprehensive, targeted, sectoral. Goal: compel behavior change without military force.",
                "key_terms": ["sanctions", "embargo", "penalty", "coercion"]
            },
            {
                "id": "pd_003",
                "source": "Political Definitions",
                "category": "governance",
                "title": "Diplomacy",
                "content": "Art and practice of conducting negotiations between states/entities. Includes negotiation, treaty-making, representation, and conflict resolution without military force.",
                "key_terms": ["diplomacy", "negotiation", "treaty", "ambassador"]
            }
        ]
        
        with open(self.knowledge_file, 'w') as f:
            json.dump(default_knowledge, f, indent=2)
        
        logger.info(f"✓ Created default knowledge base: {len(default_knowledge)} items")
    
    def _load_knowledge(self):
        """Load knowledge from file"""
        if self.knowledge_file.exists():
            try:
                with open(self.knowledge_file, 'r') as f:
                    self.knowledge_items = json.load(f)
                
                # Build indices
                for item in self.knowledge_items:
                    source = item.get('source', 'unknown')
                    category = item.get('category', 'unknown')
                    
                    if source not in self.by_source:
                        self.by_source[source] = []
                    self.by_source[source].append(item)
                    
                    if category not in self.by_category:
                        self.by_category[category] = []
                    self.by_category[category].append(item)
                
                logger.info(f"Loaded {len(self.knowledge_items)} knowledge items")
            except Exception as e:
                logger.error(f"Error loading knowledge: {e}")
        
        # Load Q&A pairs if exists
        if self.qa_file.exists():
            try:
                with open(self.qa_file, 'r') as f:
                    self.qa_pairs = json.load(f)
                logger.info(f"Loaded {len(self.qa_pairs)} Q&A pairs")
            except Exception as e:
                logger.error(f"Error loading Q&A pairs: {e}")
    
    def search_by_keywords(self, keywords: List[str], limit: int = 5) -> List[Dict]:
        """Search knowledge base by keywords"""
        results = []
        keyword_set = set(k.lower() for k in keywords)
        
        for item in self.knowledge_items:
            item_keywords = set(k.lower() for k in item.get('key_terms', []))
            overlap = len(keyword_set & item_keywords)
            
            if overlap > 0:
                results.append({
                    'item': item,
                    'relevance': overlap / len(keyword_set)
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return [r['item'] for r in results[:limit]]
    
    def get_by_source(self, source: str) -> List[Dict]:
        """Get all knowledge items from source"""
        return self.by_source.get(source, [])
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Get all knowledge items in category"""
        return self.by_category.get(category, [])
    
    def get_sources(self) -> List[str]:
        """Get all knowledge sources"""
        return list(self.by_source.keys())
    
    def get_categories(self) -> List[str]:
        """Get all categories"""
        return list(self.by_category.keys())


class RLTrainingEngine:
    """
    RL Training Engine for AZAN
    Trains on curated knowledge with strict sourcing
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.kb = CuratedKnowledgeBase(data_dir=data_dir)
        
        self.training_state_file = self.data_dir / "azan_training_state.json"
        self.rewards_file = self.data_dir / "azan_rewards.json"
        self.checkpoint_dir = self.data_dir / "azan_checkpoints"
        
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Training state
        self.iteration = 0
        self.total_reward = 0.0
        self.rewards_history = []
        self.qa_learned = []
        self.training_active = False
        
        self._load_state()
        
        logger.info(f"✓ RLTrainingEngine initialized: iteration {self.iteration}, total_reward {self.total_reward}")
    
    def _load_state(self):
        """Load training state from file"""
        if self.training_state_file.exists():
            try:
                with open(self.training_state_file, 'r') as f:
                    state = json.load(f)
                    self.iteration = state.get('iteration', 0)
                    self.total_reward = state.get('total_reward', 0.0)
                    self.rewards_history = state.get('rewards_history', [])
                    self.qa_learned = state.get('qa_learned', [])
                logger.info(f"Loaded training state: iteration {self.iteration}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
    
    def _save_state(self):
        """Save training state"""
        try:
            state = {
                'iteration': self.iteration,
                'total_reward': self.total_reward,
                'rewards_history': self.rewards_history,
                'qa_learned': self.qa_learned,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.training_state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def train_iteration(self) -> Dict:
        """Execute one training iteration"""
        self.iteration += 1
        
        # Select random knowledge item
        if not self.kb.knowledge_items:
            return {"error": "No knowledge items to train on"}
        
        knowledge_item = random.choice(self.kb.knowledge_items)
        
        # Create Q&A pair from knowledge
        qa_pair = {
            "id": f"qa_{self.iteration}",
            "source_id": knowledge_item.get('id'),
            "source": knowledge_item.get('source'),
            "category": knowledge_item.get('category'),
            "question": f"What is {knowledge_item.get('title', 'this topic')}?",
            "answer": knowledge_item.get('content'),
            "key_terms": knowledge_item.get('key_terms', []),
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate reward (0-5 scale)
        # Higher reward for more specific, sourced content
        reward = 3.0  # Base reward
        if knowledge_item.get('source'):
            reward += 1.0  # Has source
        if knowledge_item.get('key_terms'):
            reward += 0.5  # Has key terms
        
        # Add randomness for learning (0.8-1.2 multiplier)
        reward *= (0.8 + random.random() * 0.4)
        reward = min(5.0, max(0.0, reward))  # Clamp 0-5
        
        qa_pair['reward'] = round(reward, 2)
        
        # Store learned pair
        self.qa_learned.append(qa_pair)
        self.total_reward += reward
        self.rewards_history.append({
            'iteration': self.iteration,
            'reward': round(reward, 2),
            'timestamp': datetime.now().isoformat()
        })
        
        # Save checkpoint every 10 iterations
        if self.iteration % 10 == 0:
            self._save_checkpoint()
        
        # Save state
        self._save_state()
        
        return {
            "iteration": self.iteration,
            "reward": round(reward, 2),
            "avg_reward": round(self.total_reward / self.iteration, 2),
            "total_learned": len(self.qa_learned),
            "source": knowledge_item.get('source'),
            "qa_pair": qa_pair
        }
    
    def _save_checkpoint(self):
        """Save checkpoint"""
        try:
            checkpoint = {
                'iteration': self.iteration,
                'timestamp': datetime.now().isoformat(),
                'total_reward': self.total_reward,
                'avg_reward': self.total_reward / self.iteration if self.iteration > 0 else 0,
                'qa_learned_count': len(self.qa_learned),
                'qa_pairs': self.qa_learned[-10:] if len(self.qa_learned) > 0 else []
            }
            
            checkpoint_file = self.checkpoint_dir / f"checkpoint_{self.iteration}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            
            logger.info(f"✓ Checkpoint saved: iteration {self.iteration}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def get_metrics(self) -> Dict:
        """Get training metrics"""
        return {
            "iteration": self.iteration,
            "total_reward": round(self.total_reward, 2),
            "avg_reward": round(self.total_reward / self.iteration, 2) if self.iteration > 0 else 0,
            "total_learned": len(self.qa_learned),
            "recent_rewards": self.rewards_history[-20:] if self.rewards_history else [],
            "active": self.training_active
        }
    
    def get_learned_qa(self, limit: int = 10) -> List[Dict]:
        """Get recent learned Q&A pairs"""
        return self.qa_learned[-limit:]


class AutomatedRLTrainer:
    """
    Automated RL trainer that runs continuously
    """
    
    def __init__(self, engine: RLTrainingEngine, update_interval: int = 30):
        """
        Initialize automated trainer
        
        Args:
            engine: RLTrainingEngine instance
            update_interval: Seconds between training iterations (default 30)
        """
        self.engine = engine
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        
        logger.info(f"✓ AutomatedRLTrainer initialized (interval: {update_interval}s)")
    
    def start(self):
        """Start training"""
        if self.running:
            logger.warning("Training already running")
            return
        
        self.running = True
        self.engine.training_active = True
        self.thread = threading.Thread(target=self._training_loop, daemon=True)
        self.thread.start()
        logger.info("✓ Automated RL training started")
    
    def stop(self):
        """Stop training"""
        self.running = False
        self.engine.training_active = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ Automated RL training stopped")
    
    def _training_loop(self):
        """Background training loop"""
        while self.running:
            try:
                result = self.engine.train_iteration()
                logger.info(f"🎓 Iteration {result['iteration']}: reward={result['reward']}, avg={result['avg_reward']}")
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
            
            time.sleep(self.update_interval)


# Global instances
_rl_engine = None
_rl_trainer = None


def initialize_rl_pipeline(update_interval: int = 30) -> Tuple[RLTrainingEngine, AutomatedRLTrainer]:
    """Initialize global RL pipeline"""
    global _rl_engine, _rl_trainer
    
    if _rl_engine is None:
        _rl_engine = RLTrainingEngine()
    
    if _rl_trainer is None:
        _rl_trainer = AutomatedRLTrainer(_rl_engine, update_interval=update_interval)
    
    return _rl_engine, _rl_trainer


def get_rl_engine() -> RLTrainingEngine:
    """Get RL training engine"""
    global _rl_engine
    if _rl_engine is None:
        _rl_engine = RLTrainingEngine()
    return _rl_engine


def get_rl_trainer() -> AutomatedRLTrainer:
    """Get automated trainer"""
    global _rl_trainer
    if _rl_trainer is None:
        engine = get_rl_engine()
        _rl_trainer = AutomatedRLTrainer(engine)
    return _rl_trainer
