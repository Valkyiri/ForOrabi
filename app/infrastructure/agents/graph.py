import logging
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from app.application.services.retrieval_service import RetrievalService
from app.domain.entities.chat import ChatResult, GeneratedAnswer
from app.domain.entities.chunk import Chunk
from app.domain.entities.verification import VerificationResult
from app.domain.exceptions import DomainError
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.messages import UNVERIFIED_ANSWER
from app.infrastructure.agents.rag_agent import DocumentationRAGAgent
from app.infrastructure.agents.router_agent import RouterAgent
from app.infrastructure.agents.summary_agent import SummaryAgent
from app.infrastructure.agents.verification_agent import VerificationAgent
logger = logging.getLogger(__name__)

class GraphState(TypedDict, total=False):
    question: str
    intent: str
    context: str
    chunks: list[dict]
    answer: str
    agent_name: str
    supported: bool
    verification_explanation: str
    unsupported_claims: list[str]

def select_specialist(state: GraphState) -> str:
    if state.get('intent') == 'summary_request':
        return 'summary'
    return 'documentation_rag'

class DocumentationAssistantGraph:

    def __init__(self, llm: LLMProvider, retrieval: RetrievalService) -> None:
        self._router = RouterAgent(llm)
        self._rag = DocumentationRAGAgent(llm, retrieval)
        self._summary = SummaryAgent(llm, retrieval)
        self._verification = VerificationAgent(llm)
        self._graph = self._build()

    async def answer(self, question: str) -> ChatResult:
        state = await self._graph.ainvoke({'question': question, 'intent': '', 'context': '', 'chunks': [], 'answer': '', 'agent_name': '', 'supported': False, 'verification_explanation': '', 'unsupported_claims': []})
        return self._to_result(question, state)

    def _build(self):
        graph = StateGraph(GraphState)
        graph.add_node('router', self._route)
        graph.add_node('documentation_rag', self._answer_from_docs)
        graph.add_node('summary', self._summarize)
        graph.add_node('verification', self._verify)
        graph.add_edge(START, 'router')
        graph.add_conditional_edges('router', select_specialist, {'documentation_rag': 'documentation_rag', 'summary': 'summary'})
        graph.add_edge('documentation_rag', 'verification')
        graph.add_edge('summary', 'verification')
        graph.add_edge('verification', END)
        return graph.compile()

    async def _route(self, state: GraphState) -> dict:
        decision = await self._router.route(state['question'])
        return {'intent': decision.intent}

    async def _answer_from_docs(self, state: GraphState) -> dict:
        generated = await self._rag.answer(state['question'])
        return _state_from_generated(generated)

    async def _summarize(self, state: GraphState) -> dict:
        generated = await self._summary.summarize(state['question'])
        return _state_from_generated(generated)

    async def _verify(self, state: GraphState) -> dict:
        result = await self._verification.verify(question=state['question'], answer=state['answer'], context=state.get('context', ''))
        answer = state['answer']
        if not result.supported:
            logger.warning('Verification rejected the answer: %s', result.explanation)
            answer = UNVERIFIED_ANSWER
        return {'answer': answer, 'supported': result.supported, 'verification_explanation': result.explanation, 'unsupported_claims': result.unsupported_claims}

    def _to_result(self, question: str, state: GraphState) -> ChatResult:
        intent = state.get('intent')
        if intent not in ('documentation_question', 'summary_request'):
            raise DomainError('The router returned an unsupported intent.')
        chunks = [Chunk.model_validate(item) for item in state.get('chunks', [])]
        verification = VerificationResult(supported=bool(state.get('supported')), explanation=state.get('verification_explanation') or '', unsupported_claims=[str(item) for item in state.get('unsupported_claims', [])])
        return ChatResult(question=question, intent=intent, answer=state.get('answer') or '', agent=state.get('agent_name') or '', sources=RetrievalService.collect_sources(chunks), chunks=chunks, verification=verification)

def _state_from_generated(generated: GeneratedAnswer) -> dict:
    return {'answer': generated.answer, 'context': generated.context, 'chunks': [chunk.model_dump() for chunk in generated.chunks], 'agent_name': generated.agent_name}
