import logging
from fastapi import APIRouter, Depends
from app.application.use_cases.chat_use_case import ChatUseCase
from app.dependencies import get_chat_use_case
from app.presentation.api.schemas.chat import ChatRequest, ChatResponse
from app.presentation.api.schemas.common import ErrorResponse
logger = logging.getLogger(__name__)
router = APIRouter(tags=['chat'])

@router.post('/chat', response_model=ChatResponse, responses={400: {'model': ErrorResponse}, 409: {'model': ErrorResponse}, 502: {'model': ErrorResponse}, 503: {'model': ErrorResponse}})
async def chat(body: ChatRequest, use_case: ChatUseCase=Depends(get_chat_use_case)) -> ChatResponse:
    logger.info('Chat request received')
    result = await use_case.execute(body.question)
    return ChatResponse.from_result(result)
