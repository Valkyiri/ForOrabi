from pathlib import Path
from app.application.services.chunking_service import ChunkingService
from app.infrastructure.ingestion.fastapi_loader import parse_fastapi_document
from app.infrastructure.ingestion.sources import OFFICIAL_DOCS_HOST, OFFICIAL_FASTAPI_PAGES
FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'first_steps.html'
SAMPLE_HTML = '\n<article class="md-content__inner md-typeset">\n  <h1 id="dependencies">Dependencies<a class="headerlink" href="#dependencies">¶</a></h1>\n  <p>FastAPI provides a <code>Depends</code> system.</p>\n  <h2 id="use-depends">Use Depends<a class="headerlink" href="#use-depends">¶</a></h2>\n  <p>Declare the dependency in the function parameters.</p>\n  <div class="tabbed-set tabbed-alternate">\n    <div class="tabbed-labels"><label>Python 3.10+</label><label>Python 3.9+</label></div>\n    <div class="tabbed-content">\n      <div class="tabbed-block">\n        <div class="highlight"><pre><code>from fastapi import Depends, FastAPI\n\napp = FastAPI()\n\ndef common():\n    return "ok"\n\n@app.get("/items/")\ndef read_items(value: str = Depends(common)):\n    return {"value": value}\n</code></pre></div>\n      </div>\n      <div class="tabbed-block">\n        <div class="highlight"><pre><code>DUPLICATE_OLD_PYTHON</code></pre></div>\n      </div>\n    </div>\n  </div>\n  <ul>\n    <li>Import Depends.</li>\n    <li>Add it to the path operation.</li>\n  </ul>\n</article>\n'

def test_parser_keeps_sections_code_and_first_tab_only() -> None:
    document = parse_fastapi_document(SAMPLE_HTML, source='tutorial_dependencies', url='https://fastapi.tiangolo.com/tutorial/dependencies/', title='Dependencies')
    assert document.title == 'Dependencies'
    assert all(('¶' not in section.heading for section in document.sections))
    combined = '\n'.join((block.text for section in document.sections for block in section.blocks))
    assert 'DUPLICATE_OLD_PYTHON' not in combined
    assert 'from fastapi import Depends, FastAPI' in combined
    assert 'Import Depends.' in combined
    use_depends = next((section for section in document.sections if section.heading.endswith('Use Depends')))
    assert use_depends.heading == 'Dependencies > Use Depends'
    assert any((block.kind == 'code' for block in use_depends.blocks))
    assert any((block.kind == 'list' for block in use_depends.blocks))

def test_real_first_steps_page_is_structure_aware() -> None:
    html = FIXTURE.read_text(encoding='utf-8')
    document = parse_fastapi_document(html, source='tutorial_first-steps', url='https://fastapi.tiangolo.com/tutorial/first-steps/', title='First Steps')
    assert 'First Steps' in document.title
    assert all(('¶' not in section.heading for section in document.sections))
    assert any(('Recap' in section.heading for section in document.sections))
    text = '\n'.join((block.text for section in document.sections for block in section.blocks))
    assert 'Skip to content' not in text
    assert 'FastAPI' in text
    code_blocks = [block.text for section in document.sections for block in section.blocks if block.kind == 'code']
    assert code_blocks
    assert any(('FastAPI' in block for block in code_blocks))
    chunks = ChunkingService().chunk_document(document)
    assert chunks
    assert all((chunk.text.startswith('Section:') for chunk in chunks))
    assert all((len(chunk.text) <= 1400 for chunk in chunks))
    assert all((chunk.document_type == 'fastapi_documentation' for chunk in chunks))
    assert any(('FastAPI' in chunk.text for chunk in chunks))

def test_official_corpus_is_a_fixed_fastapi_list() -> None:
    urls = [page.url for page in OFFICIAL_FASTAPI_PAGES]
    assert len(urls) == len(set(urls))
    assert all((url.startswith(f'https://{OFFICIAL_DOCS_HOST}/') for url in urls))
    joined = ' '.join(urls)
    for fragment in ('first-steps', 'path-params', 'query-params', '/body/', 'response-model', 'dependencies', 'security', 'middleware', 'background-tasks', '/async/', 'handling-errors'):
        assert fragment in joined
