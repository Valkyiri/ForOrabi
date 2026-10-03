import pytest
from fastapi.testclient import TestClient
from app.config import get_settings
from app.dependencies import get_chat_use_case, get_ingest_use_case
from app.domain.entities.chat import ChatResult, SourceReference
from app.domain.entities.chunk import Chunk
from app.domain.entities.document import IngestionReport
from app.domain.entities.verification import VerificationResult
from app.domain.exceptions import EmptyCorpusError
from app.main import create_app

def _result(question: str) -> ChatResult:
    chunk = Chunk(chunk_id='chunk-1', text='Use @app.post to declare a POST path operation.', source='tutorial_body', url='https://fastapi.tiangolo.com/tutorial/body/', title='Request Body', section='Request Body', document_type='fastapi_documentation')
    return ChatResult(question=question, intent='documentation_question', answer='Declare a POST endpoint with @app.post.', agent='documentation_rag', sources=[SourceReference(title=chunk.title, url=chunk.url, section=chunk.section, chunk_id=chunk.chunk_id)], chunks=[chunk], verification=VerificationResult(supported=True, explanation='The decorator is present in the retrieved documentation.', unsupported_claims=[]))

class _ChatStub:

    async def execute(self, question: str) -> ChatResult:
        return _result(question)

class _IngestStub:

    async def execute(self) -> IngestionReport:
        return IngestionReport(documents=11, chunks=40, sources=['https://fastapi.tiangolo.com/tutorial/first-steps/'])

class _EmptyStub:

    async def execute(self, question: str) -> ChatResult:
        raise EmptyCorpusError('No FastAPI documentation is indexed. Run ingestion before asking questions.')

def test_health() -> None:
    client = TestClient(create_app())
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_home_page_is_the_chat_ui() -> None:
    client = TestClient(create_app())
    home = client.get('/')
    ui = client.get('/ui')
    assert home.status_code == 200
    assert ui.status_code == 200
    assert 'FastAPI Documentation Assistant' in home.text
    assert 'id="question"' in home.text

def test_chat_returns_answer_sources_and_verification() -> None:
    application = create_app()
    application.dependency_overrides[get_chat_use_case] = lambda: _ChatStub()
    client = TestClient(application)
    response = client.post('/chat', json={'question': 'How do I create a POST endpoint in FastAPI?'})
    assert response.status_code == 200
    body = response.json()
    assert body['intent'] == 'documentation_question'
    assert body['agent'] == 'documentation_rag'
    assert body['answer']
    assert body['sources'][0]['url'] == 'https://fastapi.tiangolo.com/tutorial/body/'
    assert body['chunks'][0]['document_type'] == 'fastapi_documentation'
    assert body['verification']['supported'] is True

def test_chat_rejects_a_short_question() -> None:
    application = create_app()
    application.dependency_overrides[get_chat_use_case] = lambda: _ChatStub()
    response = TestClient(application).post('/chat', json={'question': 'Hi'})
    assert response.status_code == 422

def test_chat_reports_an_empty_corpus() -> None:
    application = create_app()
    application.dependency_overrides[get_chat_use_case] = lambda: _EmptyStub()
    response = TestClient(application).post('/chat', json={'question': 'How does Depends work?'})
    assert response.status_code == 409
    assert 'ingestion' in response.json()['detail'].lower()

def test_chat_requires_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('OPENAI_API_KEY', '')
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('LLM_PROVIDER', '')
    get_settings.cache_clear()
    get_chat_use_case.cache_clear()
    application = create_app()
    response = TestClient(application).post('/chat', json={'question': 'How does Depends work?'})
    assert response.status_code == 503
    assert 'API_KEY' in response.json()['detail']

def test_ingest_route_returns_the_report() -> None:
    application = create_app()
    application.dependency_overrides[get_ingest_use_case] = lambda: _IngestStub()
    response = TestClient(application).post('/ingest')
    assert response.status_code == 200
    body = response.json()
    assert body['documents'] == 11
    assert body['chunks'] == 40
    assert body['sources']
