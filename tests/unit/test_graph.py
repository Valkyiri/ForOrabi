import pytest
from pydantic import ValidationError
from app.application.use_cases.chat_use_case import ChatUseCase
from app.domain.entities.chat import RouteDecision
from app.domain.entities.chunk import Chunk
from app.domain.exceptions import DomainError
from app.domain.messages import INSUFFICIENT_DOCUMENTATION, UNVERIFIED_ANSWER
from app.infrastructure.agents.graph import DocumentationAssistantGraph, select_specialist
from tests.fakes import FakeLLM, FakeRetrieval

def _chunk() -> Chunk:
    return Chunk(chunk_id='chunk-1', text='Depends declares a dependency for a path operation.', source='tutorial_dependencies', url='https://fastapi.tiangolo.com/tutorial/dependencies/', title='Dependencies', section='Dependencies', document_type='fastapi_documentation')

def test_route_decision_rejects_unknown_intent() -> None:
    with pytest.raises(ValidationError):
        RouteDecision(intent='other')

async def test_router_uses_question_words_for_the_two_intents() -> None:
    from app.infrastructure.agents.router_agent import RouterAgent
    router = RouterAgent(FakeLLM())
    summary = await router.route('Summarize the FastAPI middleware documentation.')
    docs = await router.route('How does Depends work?')
    assert summary.intent == 'summary_request'
    assert docs.intent == 'documentation_question'

def test_select_specialist_reads_the_router_intent() -> None:
    assert select_specialist({'intent': 'summary_request'}) == 'summary'
    assert select_specialist({'intent': 'documentation_question'}) == 'documentation_rag'

async def test_documentation_question_uses_rag_and_verification() -> None:
    graph = DocumentationAssistantGraph(FakeLLM(), FakeRetrieval([_chunk()]))
    result = await graph.answer('How does Depends work?')
    assert result.intent == 'documentation_question'
    assert result.agent == 'documentation_rag'
    assert 'Depends' in result.answer
    assert result.verification.supported is True
    assert result.sources[0].url.endswith('/dependencies/')
    assert result.chunks[0].chunk_id == 'chunk-1'

async def test_summary_request_uses_summary_agent() -> None:
    graph = DocumentationAssistantGraph(FakeLLM(), FakeRetrieval([_chunk()]))
    result = await graph.answer('Summarize the FastAPI middleware documentation.')
    assert result.intent == 'summary_request'
    assert result.agent == 'summary'
    assert result.answer == 'Middleware runs for every request.'
    assert result.verification.supported is True

async def test_failed_verification_returns_a_safe_answer() -> None:
    graph = DocumentationAssistantGraph(FakeLLM(unsupported=True), FakeRetrieval([_chunk()]))
    result = await graph.answer('How does Depends work?')
    assert result.answer == UNVERIFIED_ANSWER
    assert result.verification.supported is False
    assert result.verification.unsupported_claims == ['@app.magic() exists']
    assert result.sources

async def test_empty_retrieval_does_not_invent_an_answer() -> None:
    llm = FakeLLM()
    graph = DocumentationAssistantGraph(llm, FakeRetrieval([]))
    result = await graph.answer('How do I configure a quantum router?')
    assert result.answer == INSUFFICIENT_DOCUMENTATION
    assert llm.completions == []
    assert result.verification.supported is True
    assert result.chunks == []

async def test_chat_use_case_rejects_blank_question() -> None:

    class Assistant:

        async def answer(self, question: str):
            raise AssertionError('The workflow should not run.')
    use_case = ChatUseCase(Assistant())
    with pytest.raises(DomainError):
        await use_case.execute('   ')
