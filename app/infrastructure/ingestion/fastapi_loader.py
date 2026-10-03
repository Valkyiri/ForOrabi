import logging
import re
from html import unescape
from pathlib import Path
import httpx
from bs4 import BeautifulSoup, Tag
from app.domain.entities.document import ContentBlock, Document, Section
from app.domain.exceptions import ExternalServiceError, IngestionError
from app.infrastructure.ingestion.sources import OFFICIAL_DOCS_HOST, OFFICIAL_FASTAPI_PAGES, DocumentationPage
logger = logging.getLogger(__name__)
HEADING_TAGS = {'h1': 1, 'h2': 2, 'h3': 3, 'h4': 4}
_TAG_RE = re.compile('</?(?:font|span|b|u|i)\\b[^>]*>', re.IGNORECASE)
_USER_AGENT = 'FastAPI-Docs-RAG-Ingestion/1.0'

class FastAPIDocumentationLoader:

    def __init__(self, raw_dir: Path, pages: tuple[DocumentationPage, ...] | list[DocumentationPage] | None=None) -> None:
        self._raw_dir = raw_dir
        self._pages = tuple(pages or OFFICIAL_FASTAPI_PAGES)

    async def load(self) -> list[Document]:
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        documents: list[Document] = []
        headers = {'User-Agent': _USER_AGENT}
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            for page in self._pages:
                logger.info('Downloading %s', page.url)
                html = await self._download(client, page)
                destination = self._raw_dir / f'{page.slug}.html'
                destination.write_text(html, encoding='utf-8')
                documents.append(parse_fastapi_document(html, source=page.slug, url=page.url, title=page.title))
        return documents

    async def _download(self, client: httpx.AsyncClient, page: DocumentationPage) -> str:
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                response = await client.get(page.url)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning('Download attempt %s failed for %s', attempt, page.url)
                continue
            host = (response.url.host or '').lower()
            if host != OFFICIAL_DOCS_HOST:
                raise ExternalServiceError(f'Refusing to ingest {page.url} because it redirected to {response.url}.')
            if response.status_code == 200 and response.text.strip():
                return response.text
            last_error = ExternalServiceError(f'Failed to download {page.url}: HTTP {response.status_code}.')
            logger.warning('Download attempt %s returned HTTP %s for %s', attempt, response.status_code, page.url)
        raise ExternalServiceError(f'Failed to download {page.url}.') from last_error

def parse_fastapi_document(html: str, *, source: str, url: str, title: str) -> Document:
    soup = BeautifulSoup(html, 'html.parser')
    article = soup.select_one('article.md-content__inner') or soup.select_one('article')
    if article is None:
        raise IngestionError(f'Could not find the documentation article at {url}.')
    for tag in article.select('script, style, a.headerlink'):
        tag.decompose()
    page_title = _first_heading(article) or _clean_text(title) or title
    state: dict = {'stack': [], 'blocks': [], 'sections': []}
    _walk(article, state)
    _flush(state, page_title)
    if not state['sections']:
        raise IngestionError(f'No documentation sections were extracted from {url}.')
    return Document(source=source, url=url, title=page_title, sections=state['sections'])

def _walk(node: Tag, state: dict) -> None:
    for child in list(node.children):
        if not isinstance(child, Tag):
            continue
        name = child.name
        classes = set(child.get('class') or [])
        if name in {'script', 'style', 'button', 'svg', 'input', 'label', 'form', 'nav'}:
            continue
        if 'headerlink' in classes:
            continue
        if name in HEADING_TAGS:
            _flush(state, _heading_path(state) or _clean_text(child.get_text(' ', strip=True)))
            _push_heading(state, HEADING_TAGS[name], child)
            continue
        if 'tabbed-set' in classes:
            block = child.select_one('.tabbed-block')
            if block is not None:
                _walk(block, state)
            continue
        if 'highlight' in classes or name == 'pre':
            code = _extract_code(child)
            if code:
                state['blocks'].append(ContentBlock(kind='code', text=code))
            continue
        if name == 'p':
            text = _clean_text(child.get_text(' ', strip=True))
            if text:
                state['blocks'].append(ContentBlock(kind='paragraph', text=text))
            continue
        if name in {'ul', 'ol'}:
            rendered = _render_list(child, ordered=name == 'ol')
            if rendered:
                state['blocks'].append(ContentBlock(kind='list', text=rendered))
            continue
        if name == 'table':
            rendered = _render_table(child)
            if rendered:
                state['blocks'].append(ContentBlock(kind='paragraph', text=rendered))
            continue
        if name in {'div', 'section', 'article', 'blockquote', 'details'}:
            _walk(child, state)

def _flush(state: dict, fallback_heading: str) -> None:
    if not state['blocks']:
        return
    stack = state['stack']
    heading = ' > '.join((text for _, text in stack)) or fallback_heading
    level = stack[-1][0] if stack else 1
    state['sections'].append(Section(heading=heading, level=level, blocks=list(state['blocks'])))
    state['blocks'] = []

def _push_heading(state: dict, level: int, node: Tag) -> None:
    text = _clean_text(node.get_text(' ', strip=True))
    if not text:
        return
    while state['stack'] and state['stack'][-1][0] >= level:
        state['stack'].pop()
    state['stack'].append((level, text))

def _heading_path(state: dict) -> str:
    return ' > '.join((text for _, text in state['stack']))

def _first_heading(article: Tag) -> str:
    heading = article.find(['h1', 'h2'])
    if not isinstance(heading, Tag):
        return ''
    return _clean_text(heading.get_text(' ', strip=True))

def _extract_code(node: Tag) -> str:
    pre = node if node.name == 'pre' else node.find('pre')
    source = pre if isinstance(pre, Tag) else node
    text = unescape(source.get_text())
    text = _TAG_RE.sub('', text)
    lines = [line.rstrip() for line in text.splitlines()]
    return '\n'.join(lines).strip('\n')

def _render_list(node: Tag, *, ordered: bool) -> str:
    items: list[str] = []
    for index, item in enumerate(node.find_all('li', recursive=False), start=1):
        text = _clean_text(item.get_text(' ', strip=True))
        if not text:
            continue
        prefix = f'{index}. ' if ordered else '- '
        items.append(prefix + text)
    return '\n'.join(items)

def _render_table(node: Tag) -> str:
    rows: list[str] = []
    for row in node.find_all('tr'):
        cells = [_clean_text(cell.get_text(' ', strip=True)) for cell in row.find_all(['th', 'td'])]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(' | '.join(cells))
    return '\n'.join(rows)

def _clean_text(value: str) -> str:
    cleaned = value.replace('¶', ' ')
    return ' '.join(cleaned.split())
