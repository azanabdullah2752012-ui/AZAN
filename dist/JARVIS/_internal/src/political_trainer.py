"""
Auto-training module for political news and world matters.

Fetches latest political news and automatically trains the AI model
to understand and discuss current world political events.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger(__name__)

# Data file to store fetched political topics
POLITICAL_DATA_PATH = Path("data") / "political_topics.json"
TRAINING_LOG_PATH = Path("data") / "auto_training_log.json"


class PoliticalNewsHelper:
    """Helper class to fetch and process political news topics."""
    
    @staticmethod
    def fetch_political_topics() -> list[dict]:
        """
        Fetch current world political topics and news summaries.
        
        Returns list of political topics with questions for training.
        """
        # Curated list of important political topics and questions
        topics = [
            {
                "topic": "Global Trade Relationships",
                "questions": [
                    "What are the current trade tensions between major world powers?",
                    "How are trade agreements affecting developing economies?",
                    "What is the impact of tariffs on global commerce?",
                    "How are supply chains adapting to new trade policies?"
                ]
            },
            {
                "topic": "Climate Policy and International Action",
                "questions": [
                    "What are the latest international climate agreements?",
                    "How are countries implementing carbon neutrality goals?",
                    "What is the role of renewable energy in global politics?",
                    "How does climate policy affect economic development?"
                ]
            },
            {
                "topic": "Democratic Institutions and Elections",
                "questions": [
                    "What are current trends in democratic participation worldwide?",
                    "How are elections being conducted in major democracies?",
                    "What challenges face electoral integrity today?",
                    "How is technology affecting democratic processes?"
                ]
            },
            {
                "topic": "International Security and Conflicts",
                "questions": [
                    "What are the major geopolitical tensions in the world today?",
                    "How are international organizations addressing conflicts?",
                    "What is the role of military alliances in modern geopolitics?",
                    "How are cyber threats affecting international security?"
                ]
            },
            {
                "topic": "Economic Development and Inequality",
                "questions": [
                    "How are developing nations addressing economic challenges?",
                    "What policies reduce wealth inequality globally?",
                    "How do labor policies affect international competitiveness?",
                    "What is the impact of automation on employment worldwide?"
                ]
            },
            {
                "topic": "Migration and Border Policy",
                "questions": [
                    "What are current approaches to immigration policy?",
                    "How are countries managing refugee crises?",
                    "What is the economic impact of labor migration?",
                    "How do border policies affect regional relationships?"
                ]
            },
            {
                "topic": "Technology and Governance",
                "questions": [
                    "How is technology regulation evolving globally?",
                    "What are the implications of AI development for governance?",
                    "How are data privacy policies being standardized internationally?",
                    "What role does tech innovation play in political systems?"
                ]
            },
            {
                "topic": "Healthcare and Pandemics",
                "questions": [
                    "How are countries preparing for future health emergencies?",
                    "What are global approaches to vaccine distribution?",
                    "How does healthcare policy affect international relations?",
                    "What lessons have been learned from recent pandemics?"
                ]
            },
            {
                "topic": "Energy Independence and Resources",
                "questions": [
                    "How are countries achieving energy independence?",
                    "What is the geopolitical importance of energy resources?",
                    "How are renewable energy transitions affecting politics?",
                    "What role does resource control play in conflicts?"
                ]
            },
            {
                "topic": "Human Rights and Social Justice",
                "questions": [
                    "What are global human rights concerns today?",
                    "How are countries addressing systemic inequality?",
                    "What is the role of activism in modern politics?",
                    "How do international organizations promote rights protection?"
                ]
            }
        ]
        return topics
    
    @staticmethod
    def generate_training_pairs(topics: list[dict]) -> list[dict]:
        """
        Convert political topics into training question-answer pairs.
        
        Returns list of dicts with 'question' and 'ideal_answer' keys.
        """
        pairs = []
        
        political_answers = {
            "Global Trade Relationships": [
                "Trade relationships are complex and involve negotiations between multiple countries balancing their economic interests. Modern trade involves both traditional goods and digital services, with organizations like the WTO facilitating agreements while bilateral relationships shape daily commerce.",
                "Current trade tensions reflect deeper strategic competition as countries pursue economic sovereignty while maintaining global supply chains. Developing nations often face challenges accessing markets while established economies protect key industries through tariffs and quotas.",
                "Tariffs serve multiple purposes - protecting domestic industries, raising government revenue, and negotiating leverage - but can increase consumer prices and trigger retaliatory measures. Trade policy increasingly reflects not just economics but national security concerns.",
                "Supply chains are becoming more resilient and localized following disruptions. Companies are diversifying sourcing, nearshoring operations, and building redundancy to reduce vulnerability to geopolitical shocks and trade barriers."
            ],
            "Climate Policy and International Action": [
                "International climate agreements like the Paris Agreement set targets for reducing greenhouse gas emissions. Countries commit to nationally determined contributions, though enforcement mechanisms remain challenging and developing nations often need financial support.",
                "Nations implement carbon neutrality through renewable energy transition, energy efficiency standards, carbon pricing mechanisms, and nature-based solutions. The timeline and investment levels vary significantly between developed and developing nations.",
                "Renewable energy has become central to climate politics because it addresses both environmental and economic concerns. It reduces dependence on fossil fuel imports, creates domestic jobs, and increasingly offers cheaper electricity than traditional sources.",
                "Climate policy directly influences economic growth, affecting job markets, investment patterns, and competitive advantage. Countries view climate action as both an obligation and an opportunity for economic leadership in clean technology sectors."
            ],
            "Democratic Institutions and Elections": [
                "Democratic participation shows varied trends globally - some regions see increased engagement while others face declining voter turnout. Digital tools and social media are reshaping how campaigns operate and how citizens engage with politics.",
                "Major democracies employ diverse electoral systems and practices. Recent focus includes securing elections against misinformation, ensuring accessibility, and adapting to hybrid voting methods while maintaining integrity and public trust.",
                "Electoral integrity faces threats from misinformation, cyberattacks, foreign interference, and domestic polarization. Election security requires coordination between government, tech companies, and civil society to verify voter rolls, secure voting systems, and combat false information.",
                "Technology enables broader participation through online platforms but also enables manipulation through bots and misinformation. Social media algorithms can amplify divisive content, making authentic democratic deliberation more challenging in digital spaces."
            ],
            "International Security and Conflicts": [
                "Geopolitical tensions center on regional conflicts, competition for influence between major powers, and proxy conflicts in areas of strategic importance. The international system remains multipolar with shifting alliances and competing security frameworks.",
                "International organizations like the UN facilitate dialogue and peacekeeping, though enforcement capabilities remain limited by member state cooperation. Regional organizations also play important roles in conflict prevention and resolution.",
                "Military alliances like NATO serve deterrent functions while raising concerns about escalation. Modern military strategy increasingly emphasizes cyber capabilities, space operations, and economic leverage alongside traditional force projection.",
                "Cyber threats from state and non-state actors target government systems, critical infrastructure, and election processes. The difficulty in attribution and proportional response makes cyber conflict a new frontier for international security management."
            ],
            "Economic Development and Inequality": [
                "Developing nations pursue varied strategies including trade liberalization, foreign investment attraction, technology transfer, and infrastructure development. Success depends on political stability, institutional quality, education, and access to capital and markets.",
                "Policies reducing inequality include progressive taxation, education investment, social safety nets, and labor protections. However, globalization and technology create downward pressure on wages for less-skilled workers in developed nations while benefiting others.",
                "Labor policies balance worker protections with business flexibility and international competitiveness. Countries increasingly focus on wage standards, working conditions, and skills training as cornerstones of sustainable development.",
                "Automation transforms labor markets, eliminating some jobs while creating others in different sectors. Societies grapple with retraining programs, social safety nets, and education systems to ensure workers can adapt to technological change."
            ],
            "Migration and Border Policy": [
                "Immigration policies reflect tensions between economic needs for workers and political concerns about cultural integration and job competition. Countries increasingly use points-based systems targeting specific skills while enforcing border security.",
                "Refugee crises often reflect conflict and persecution, requiring international burden-sharing. The responsibility to host refugees strains resources in neighboring countries while wealthy nations debate their moral and practical obligations.",
                "Labor migration generates economic benefits through remittances, filling labor gaps, and cultural exchange. However, it can also strain public services in destination countries and create brain drain in origin countries, requiring managed migration policies.",
                "Border policy reflects sovereignty concerns and security interests while affecting regional relationships, trade, and people's lives. Effective immigration policy balances security, economic needs, humanitarian obligations, and practical enforcement capability."
            ],
            "Technology and Governance": [
                "Technology regulation increasingly focuses on data privacy (GDPR, CCPA), competition (antitrust cases against Big Tech), content moderation, and cybersecurity. Governments struggle to develop adequate frameworks while protecting innovation.",
                "AI development raises governance questions about bias, transparency, accountability, and job displacement. International discussions explore AI ethics, standards, and frameworks for development and deployment while concerns about superintelligent AI persist.",
                "Data privacy regulations aim to give citizens control over personal information while balancing law enforcement needs and business innovation. The global nature of the internet creates friction between jurisdictions with different privacy standards.",
                "Tech innovation drives governance improvements through digital services, blockchain applications, and data analytics. However, it also enables surveillance, misinformation, and new forms of inequality, requiring thoughtful governance approaches."
            ],
            "Healthcare and Pandemics": [
                "Countries prepare for health emergencies through surveillance systems, supply stockpiles, vaccine development capacity, and international cooperation frameworks. COVID-19 revealed gaps in preparedness that nations continue addressing through health security investments.",
                "Vaccine distribution involves equity concerns as wealthy nations secured supply while developing countries faced shortages. International mechanisms like COVAX attempt to ensure access, though intellectual property rights and manufacturing capacity remain contested issues.",
                "Healthcare policy affects international relations through medical diplomacy, technology transfer, and funding for global health initiatives. Countries view healthcare capacity as both a humanitarian concern and a strategic asset.",
                "Recent pandemics taught lessons about preparedness, transparency, international cooperation, and the importance of investing in public health infrastructure. Nations are implementing pandemic prevention strategies and improving early warning systems."
            ],
            "Energy Independence and Resources": [
                "Energy independence strategies include renewable energy development, nuclear power, energy efficiency, and sometimes expanding domestic fossil fuel production. Achieving independence requires massive infrastructure investment and long-term planning.",
                "Energy resources like oil, natural gas, and rare earth minerals shape geopolitical relationships and conflicts. Control of resources generates wealth and leverage, making energy security a central concern for many nations.",
                "Renewable energy transitions require grid modernization, storage solutions, and investment in manufacturing capacity. Countries view renewable leadership as both a climate imperative and an economic opportunity in the growing clean tech market.",
                "Resource conflicts emerge when multiple nations claim territory, seek control of supply chains, or use energy as geopolitical leverage. The transition to renewables reshapes resource dependencies and creates new strategic competition."
            ],
            "Human Rights and Social Justice": [
                "Global human rights concerns include political repression, torture, discrimination, and restrictions on freedom of expression and assembly. International organizations document violations while facing challenges in enforcement and accountability.",
                "Countries address systemic inequality through legal reforms, affirmative action, education access, and wealth redistribution programs. Progress varies significantly based on political will and institutional capacity.",
                "Activism shapes politics through social movements addressing injustice. Activism increasingly uses digital tools for mobilization while facing suppression in authoritarian contexts and regulatory constraints in some democracies.",
                "International organizations promote rights through treaties, monitoring, advocacy, and capacity building. However, enforcement challenges persist as powerful states resist intervention while vulnerable populations still lack adequate protection."
            ]
        }
        
        for topic in topics:
            topic_name = topic["topic"]
            answers = political_answers.get(topic_name, [
                f"This is an important aspect of {topic_name} that requires careful analysis of multiple perspectives and evidence."
            ] * 4)
            
            for i, question in enumerate(topic["questions"]):
                ideal_answer = answers[i % len(answers)]
                pairs.append({
                    "question": question,
                    "ideal_answer": ideal_answer,
                    "topic": topic_name,
                    "timestamp": datetime.now().isoformat()
                })
        
        return pairs
    
    @staticmethod
    def save_topics_cache(topics: list[dict]) -> None:
        """Save fetched topics to disk cache."""
        POLITICAL_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(POLITICAL_DATA_PATH, "w") as f:
            json.dump(topics, f, indent=2)
    
    @staticmethod
    def load_topics_cache() -> Optional[list[dict]]:
        """Load cached topics if they exist."""
        if POLITICAL_DATA_PATH.exists():
            with open(POLITICAL_DATA_PATH, "r") as f:
                return json.load(f)
        return None


class AutoTrainer:
    """Manages automatic training on political topics."""
    
    def __init__(self):
        self.news_helper = PoliticalNewsHelper()
        self.training_log_path = TRAINING_LOG_PATH
        self._ensure_log_file()
    
    def _ensure_log_file(self) -> None:
        """Ensure training log file exists."""
        self.training_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.training_log_path.exists():
            with open(self.training_log_path, "w") as f:
                json.dump({"sessions": []}, f)
    
    def get_training_pairs(self) -> list[dict]:
        """Get training question-answer pairs on political topics."""
        topics = self.news_helper.fetch_political_topics()
        self.news_helper.save_topics_cache(topics)
        pairs = self.news_helper.generate_training_pairs(topics)
        return pairs
    
    def log_training_session(self, session_data: dict) -> None:
        """Log a training session."""
        try:
            with open(self.training_log_path, "r") as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            log_data = {"sessions": []}
        
        log_data["sessions"].append({
            **session_data,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(self.training_log_path, "w") as f:
            json.dump(log_data, f, indent=2)
    
    def get_training_stats(self) -> dict:
        """Get statistics about auto-training sessions."""
        try:
            with open(self.training_log_path, "r") as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "total_sessions": 0,
                "total_examples_trained": 0,
                "average_reward": 0.0,
                "last_training": None
            }
        
        sessions = log_data.get("sessions", [])
        if not sessions:
            return {
                "total_sessions": 0,
                "total_examples_trained": 0,
                "average_reward": 0.0,
                "last_training": None
            }
        
        total_examples = sum(s.get("examples_trained", 0) for s in sessions)
        rewards = [s.get("avg_reward", 0) for s in sessions if "avg_reward" in s]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
        
        return {
            "total_sessions": len(sessions),
            "total_examples_trained": total_examples,
            "average_reward": round(avg_reward, 3),
            "last_training": sessions[-1].get("timestamp") if sessions else None,
            "sessions_by_topic": self._group_by_topic(sessions)
        }
    
    @staticmethod
    def _group_by_topic(sessions: list[dict]) -> dict:
        """Group training sessions by political topic."""
        grouped = {}
        for session in sessions:
            topic = session.get("topic", "Unknown")
            if topic not in grouped:
                grouped[topic] = {"count": 0, "examples": 0}
            grouped[topic]["count"] += 1
            grouped[topic]["examples"] += session.get("examples_trained", 0)
        return grouped


# Singleton instance
auto_trainer = AutoTrainer()


def get_auto_trainer() -> AutoTrainer:
    """Get the auto-trainer instance."""
    return auto_trainer
