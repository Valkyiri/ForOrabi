import re
from app.application.services.chunking_service import ChunkingService
from app.domain.entities.document import ContentBlock, Document, Section
URL = 'https://fastapi.tiangolo.com/tutorial/dependencies/'

def _document(sections: list[Section], title: str='Dependencies') -> Document:
    return Document(source='tutorial_dependencies', url=URL, title=title, sections=sections)

def test_sections_stay_separate_when_they_fit() -> None:
    document = _document([Section(heading='Dependencies', level=1, blocks=[ContentBlock(kind='paragraph', text='Intro text about Depends.')]), Section(heading='Dependencies > Use Depends', level=2, blocks=[ContentBlock(kind='paragraph', text='Call Depends in the parameter list.')])])
    chunks = ChunkingService().chunk_document(document)
    assert len(chunks) == 2
    assert chunks[0].section == 'Dependencies'
    assert 'Intro text about Depends.' in chunks[0].text
    assert 'Call Depends' not in chunks[0].text
    assert chunks[1].section == 'Dependencies > Use Depends'
    assert chunks[1].text.startswith('Section: Dependencies > Use Depends')

def test_repeated_section_headings_still_get_unique_ids() -> None:
    document = _document([Section(heading='Dependencies > Recap', level=2, blocks=[ContentBlock(kind='paragraph', text='First recap.')]), Section(heading='Dependencies > Recap', level=2, blocks=[ContentBlock(kind='paragraph', text='Second recap.')])])
    chunks = ChunkingService().chunk_document(document)
    assert len(chunks) == 2
    assert chunks[0].chunk_id != chunks[1].chunk_id

def test_chunk_ids_and_metadata_are_stable() -> None:
    document = _document([Section(heading='Dependencies', level=1, blocks=[ContentBlock(kind='paragraph', text='Depends is a callable.')])])
    service = ChunkingService()
    first = service.chunk_document(document)
    second = service.chunk_document(document)
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    metadata = first[0].to_metadata()
    assert set(metadata) == {'source', 'url', 'title', 'section', 'chunk_id', 'document_type'}
    assert metadata['document_type'] == 'fastapi_documentation'
    assert metadata['url'] == URL
    assert metadata['chunk_id'] == first[0].chunk_id

def test_small_code_block_stays_intact() -> None:
    code = "def endpoint():\n    return {'ok': True}\n# UNIQUE_CODE_LINE"
    document = _document([Section(heading='Dependencies', level=1, blocks=[ContentBlock(kind='paragraph', text='Use a dependency in the path operation.'), ContentBlock(kind='code', text=code)])])
    chunks = ChunkingService().chunk_document(document)
    assert len(chunks) == 1
    assert 'def endpoint():' in chunks[0].text
    assert '# UNIQUE_CODE_LINE' in chunks[0].text
    assert chunks[0].text.count('```') == 2

def test_large_section_splits_with_overlap_and_keeps_the_heading() -> None:
    blocks = [ContentBlock(kind='paragraph', text=f'PARAGRAPH-{index}-' + 'x' * 80) for index in range(12)]
    document = _document([Section(heading='Demo', level=1, blocks=blocks)], title='Demo')
    chunks = ChunkingService(max_chars=350, overlap_chars=150).chunk_document(document)
    assert len(chunks) > 1
    assert all((chunk.text.startswith('Section: Demo') for chunk in chunks))
    assert all((len(chunk.text) <= 350 for chunk in chunks))
    shared = False
    for left, right in zip(chunks, chunks[1:]):
        left_ids = set(re.findall('PARAGRAPH-\\d+', left.text))
        right_ids = set(re.findall('PARAGRAPH-\\d+', right.text))
        if left_ids & right_ids:
            shared = True
    assert shared

def test_code_inside_a_large_section_is_not_torn_apart() -> None:
    paragraphs = [ContentBlock(kind='paragraph', text='WORD ' * 40 + f'P{index}') for index in range(10)]
    code = ContentBlock(kind='code', text="def endpoint():\n    return {'ok': True}\n# UNIQUE_CODE_LINE")
    blocks = paragraphs[:5] + [code] + paragraphs[5:]
    document = _document([Section(heading='Handlers', level=1, blocks=blocks)], title='Handlers')
    chunks = ChunkingService(max_chars=500, overlap_chars=40).chunk_document(document)
    holders = [chunk for chunk in chunks if 'UNIQUE_CODE_LINE' in chunk.text]
    assert holders
    assert all(('def endpoint():' in chunk.text for chunk in holders))
    assert all((len(chunk.text) <= 500 for chunk in chunks))

def test_oversized_code_block_is_split_by_lines() -> None:
    code = '\n'.join((f'line_{index} = {index}' for index in range(80)))
    document = _document([Section(heading='First Steps', level=1, blocks=[ContentBlock(kind='code', text=code)])], title='First Steps')
    chunks = ChunkingService(max_chars=300, overlap_chars=40).chunk_document(document)
    assert len(chunks) > 1
    assert all((chunk.text.startswith('Section: First Steps') for chunk in chunks))
    assert all(('```' in chunk.text for chunk in chunks))
    assert all((len(chunk.text) <= 300 for chunk in chunks))
    assert any(('line_0 = 0' in chunk.text for chunk in chunks))
