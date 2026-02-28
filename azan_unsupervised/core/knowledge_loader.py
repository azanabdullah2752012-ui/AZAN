"""
knowledge_loader.py — Streaming parser for knowledge_base.txt

Parses structured plain-text knowledge entries in CATEGORY/TITLE/SOURCE/CONTENT
blocks separated by '---'. Supports large files via generator pattern.
No external dependencies beyond stdlib.
"""

import logging
import re
from pathlib import Path
from typing import Generator, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class KnowledgeEntry:
    """Represents a single parsed knowledge entry."""

    __slots__ = ("category", "title", "source", "content", "raw_id")

    def __init__(self, category: str, title: str, source: str, content: str):
        self.category = category.strip().upper()
        self.title = title.strip()
        self.source = source.strip()
        self.content = content.strip()
        self.raw_id = f"{self.category}::{self.title}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_id": self.raw_id,
            "category": self.category,
            "title": self.title,
            "source": self.source,
            "content": self.content,
            "embed_text": f"{self.title}. {self.content}",
        }

    def __repr__(self) -> str:
        return f"<KnowledgeEntry category={self.category!r} title={self.title!r}>"


class KnowledgeLoader:
    """
    Streaming parser for knowledge_base.txt.

    Format expected:
        CATEGORY: <name>
        TITLE: <name>
        SOURCE: <source>
        CONTENT:
        <multi-line text>
        ---
    """

    _TAG_PATTERNS = {
        "category": re.compile(r"^CATEGORY:\s*(.+)$", re.IGNORECASE),
        "title": re.compile(r"^TITLE:\s*(.+)$", re.IGNORECASE),
        "source": re.compile(r"^SOURCE:\s*(.+)$", re.IGNORECASE),
        "content_start": re.compile(r"^CONTENT:\s*$", re.IGNORECASE),
        "separator": re.compile(r"^---\s*$"),
        "comment": re.compile(r"^#+"),
    }

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Knowledge base not found: {self.path}")

    def stream_entries(self) -> Generator[KnowledgeEntry, None, None]:
        """Yield KnowledgeEntry objects one by one (memory efficient)."""
        yield from self._parse_blocks(self._read_lines())

    def load_all(self) -> List[Dict[str, Any]]:
        """Load all entries as a list of dicts."""
        return [entry.to_dict() for entry in self.stream_entries()]

    def load_from_line(self, start_line: int) -> List[Dict[str, Any]]:
        """
        Load entries whose separator line is >= start_line.
        Used by the incremental indexer to read only new content.
        """
        entries = []
        for block_end_line, knowledge_entry in self._parse_blocks_with_lines(self._read_lines()):
            if block_end_line >= start_line:
                entries.append(knowledge_entry.to_dict())
        return entries

    def count_lines(self) -> int:
        """Return total line count of the knowledge base file."""
        with self.path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)

    def _read_lines(self) -> Generator[str, None, None]:
        with self.path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")

    def _parse_blocks(
        self, lines: Generator[str, None, None]
    ) -> Generator[KnowledgeEntry, None, None]:
        """Core parser: yields KnowledgeEntry from raw line stream."""
        state = "idle"
        category = title = source = ""
        content_lines: List[str] = []
        block_num = 0

        for line in lines:
            if self._TAG_PATTERNS["comment"].match(line):
                continue

            if self._TAG_PATTERNS["separator"].match(line):
                block_num += 1
                if category and title and content_lines:
                    content = "\n".join(content_lines).strip()
                    if content:
                        yield KnowledgeEntry(category, title, source, content)
                    else:
                        logger.warning("Block %d empty CONTENT — skipped", block_num)
                elif category or title:
                    logger.warning("Block %d incomplete — skipped", block_num)
                category = title = source = ""
                content_lines = []
                state = "idle"
                continue

            if state == "content":
                content_lines.append(line)
                continue

            m = self._TAG_PATTERNS["category"].match(line)
            if m:
                category = m.group(1)
                state = "header"
                continue

            m = self._TAG_PATTERNS["title"].match(line)
            if m:
                title = m.group(1)
                continue

            m = self._TAG_PATTERNS["source"].match(line)
            if m:
                source = m.group(1)
                continue

            if self._TAG_PATTERNS["content_start"].match(line):
                state = "content"
                content_lines = []
                continue

    def _parse_blocks_with_lines(
        self, lines: Generator[str, None, None]
    ) -> Generator[Tuple[int, KnowledgeEntry], None, None]:
        """Like _parse_blocks but yields (end_line_number, KnowledgeEntry)."""
        state = "idle"
        category = title = source = ""
        content_lines: List[str] = []
        block_num = 0
        line_num = 0

        for line in lines:
            line_num += 1
            if self._TAG_PATTERNS["comment"].match(line):
                continue

            if self._TAG_PATTERNS["separator"].match(line):
                block_num += 1
                if category and title and content_lines:
                    content = "\n".join(content_lines).strip()
                    if content:
                        yield (line_num, KnowledgeEntry(category, title, source, content))
                category = title = source = ""
                content_lines = []
                state = "idle"
                continue

            if state == "content":
                content_lines.append(line)
                continue

            m = self._TAG_PATTERNS["category"].match(line)
            if m:
                category = m.group(1)
                state = "header"
                continue
            m = self._TAG_PATTERNS["title"].match(line)
            if m:
                title = m.group(1)
                continue
            m = self._TAG_PATTERNS["source"].match(line)
            if m:
                source = m.group(1)
                continue
            if self._TAG_PATTERNS["content_start"].match(line):
                state = "content"
                content_lines = []
                continue
