import hashlib
import logging
from app.domain.entities.chunk import DOCUMENT_TYPE, Chunk
from app.domain.entities.document import ContentBlock, Document
logger = logging.getLogger(__name__)

class ChunkingService:

    def __init__(self, max_chars: int=1400, overlap_chars: int=200) -> None:
        if max_chars < 1:
            raise ValueError('max_chars must be at least 1.')
        if overlap_chars < 0 or overlap_chars >= max_chars:
            raise ValueError('overlap_chars must be smaller than max_chars.')
        self._max_chars = max_chars
        self._overlap = overlap_chars

    def chunk_document(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        sequential = 0
        for section in document.sections:
            heading = section.heading.strip() or document.title
            units = self._units_for_section(heading, section.blocks)
            if not units:
                continue
            for text in self._split_section(heading, units):
                chunks.append(Chunk(chunk_id=self._make_id(document.url, heading, sequential), text=text, source=document.source, url=document.url, title=document.title, section=heading, document_type=DOCUMENT_TYPE))
                sequential += 1
        logger.info('Chunked %s into %s chunks', document.source, len(chunks))
        return chunks

    def _units_for_section(self, heading: str, blocks: list[ContentBlock]) -> list[str]:
        budget = self._body_budget(heading)
        units: list[str] = []
        for block in blocks:
            text = block.text.strip()
            if not text:
                continue
            if block.kind == 'code':
                fenced = text if text.startswith('```') else f'```\n{text}\n```'
                raw = self._strip_fence(fenced)
                if len(f'```\n{raw}\n```') <= budget:
                    units.append(f'```\n{raw}\n```')
                else:
                    units.extend(self._split_code(raw, budget))
                continue
            if len(text) <= budget:
                units.append(text)
            else:
                units.extend(self._window(text, budget))
        return units

    def _split_section(self, heading: str, units: list[str]) -> list[str]:
        if not units:
            return []
        if len(units) == 1 or self._fits(heading, units):
            rendered = self._render(heading, units)
            if len(rendered) <= self._max_chars:
                return [rendered]
            budget = self._body_budget(heading)
            return [self._render(heading, [part]) for part in self._window(units[0], budget)]
        mid = len(units) // 2
        left = units[:mid]
        right = units[mid:]
        overlap = self._tail_overlap(left)
        if overlap and len(overlap) + len(right) < len(units):
            right = overlap + right
        return self._split_section(heading, left) + self._split_section(heading, right)

    def _tail_overlap(self, units: list[str]) -> list[str]:
        selected: list[str] = []
        size = 0
        for unit in reversed(units):
            if len(selected) == len(units) - 1:
                break
            extra = len(unit) + (2 if selected else 0)
            if extra > self._overlap or size + extra > self._overlap:
                break
            selected.insert(0, unit)
            size += extra
        return selected

    def _split_code(self, code: str, budget: int) -> list[str]:
        lines = code.splitlines() or [code]
        groups: list[str] = []
        current: list[str] = []
        for line in lines:
            if current and len(self._fence(current + [line])) > budget:
                groups.append(self._fence(current))
                current = self._line_overlap(current)
                if current and len(self._fence(current + [line])) > budget:
                    current = []
            if len(self._fence(current + [line])) > budget:
                for part in self._window(line, max(1, budget - 8)):
                    groups.append(f'```\n{part}\n```')
                current = []
                continue
            current.append(line)
        if current:
            groups.append(self._fence(current))
        return groups

    def _line_overlap(self, lines: list[str]) -> list[str]:
        selected: list[str] = []
        size = 0
        for line in reversed(lines):
            extra = len(line) + 1
            if extra > self._overlap or size + extra > self._overlap:
                break
            if len(selected) == len(lines) - 1:
                break
            selected.insert(0, line)
            size += extra
        return selected

    def _window(self, text: str, budget: int) -> list[str]:
        if len(text) <= budget:
            return [text]
        overlap = min(self._overlap, max(0, budget // 3))
        parts: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + budget)
            part = text[start:end].strip()
            if part:
                parts.append(part)
            if end >= len(text):
                break
            next_start = end - overlap
            if next_start <= start:
                next_start = end
            start = next_start
        return parts

    def _fits(self, heading: str, units: list[str]) -> bool:
        return len(self._render(heading, units)) <= self._max_chars

    def _render(self, heading: str, units: list[str]) -> str:
        body = '\n\n'.join((unit.strip() for unit in units if unit and unit.strip()))
        prefix = self._prefix(heading)
        if prefix and body:
            return prefix + body
        return body or prefix.strip()

    def _prefix(self, heading: str) -> str:
        cleaned = heading.strip()
        if not cleaned:
            return ''
        return f'Section: {cleaned}\n\n'

    def _body_budget(self, heading: str) -> int:
        return max(1, self._max_chars - len(self._prefix(heading)))

    @staticmethod
    def _fence(lines: list[str]) -> str:
        return '```\n' + '\n'.join(lines) + '\n```'

    @staticmethod
    def _strip_fence(text: str) -> str:
        if not text.startswith('```'):
            return text
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        return '\n'.join(lines).strip('\n')

    @staticmethod
    def _make_id(url: str, section: str, index: int) -> str:
        payload = f'{url}|{section}|{index}'.encode()
        return hashlib.sha256(payload).hexdigest()[:32]
