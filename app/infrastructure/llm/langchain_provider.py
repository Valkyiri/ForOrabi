import json
import logging
import re
from collections.abc import Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from app.domain.exceptions import ExternalServiceError
logger = logging.getLogger(__name__)
_JSON_BLOCK = re.compile('```(?:json)?\\s*(.*?)\\s*```', re.DOTALL)

class LangChainChatProvider:

    def __init__(self, models: BaseChatModel | Sequence[BaseChatModel]) -> None:
        if isinstance(models, Sequence) and (not isinstance(models, (str, bytes))):
            self._models = list(models)
        else:
            self._models = [models]
        if not self._models:
            raise ValueError('At least one chat model is required.')
        self._index = 0
        self._prompt = ChatPromptTemplate.from_messages([('system', '{system_prompt}'), ('human', '{user_prompt}')])

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        last_error: Exception | None = None
        for offset in range(len(self._models)):
            model = self._models[(self._index + offset) % len(self._models)]
            chain = self._prompt | model
            try:
                message = await chain.ainvoke({'system_prompt': system_prompt, 'user_prompt': user_prompt})
            except Exception as exc:
                last_error = exc
                if _should_switch_model(exc) and offset + 1 < len(self._models):
                    self._index = (self._index + offset + 1) % len(self._models)
                    logger.warning('Chat model failed; trying the next Gemini model')
                    continue
                logger.exception('LangChain chat request failed')
                raise ExternalServiceError(_user_message(exc)) from exc
            if offset:
                self._index = (self._index + offset) % len(self._models)
            content = getattr(message, 'content', message)
            if isinstance(content, list):
                content = ''.join((part.get('text', '') if isinstance(part, dict) else str(part) for part in content))
            text = str(content).strip()
            if not text:
                raise ExternalServiceError('The language model returned an empty answer.')
            return text
        raise ExternalServiceError(_user_message(last_error)) from last_error

    async def complete_structured(self, *, system_prompt: str, user_prompt: str, response_model: type[BaseModel]) -> BaseModel:
        schema = json.dumps(response_model.model_json_schema(), indent=2)
        raw = await self.complete(system_prompt=f'{system_prompt}\n\nReturn only valid JSON that matches this schema. Do not include markdown, comments, or extra keys.\n{schema}', user_prompt=user_prompt)
        try:
            parsed = response_model.model_validate(_extract_json(raw))
        except Exception as exc:
            logger.exception('Structured JSON from the language model was invalid')
            raise ExternalServiceError('The language model returned a response that could not be verified.') from exc
        return parsed

def _extract_json(text: str) -> dict:
    match = _JSON_BLOCK.search(text)
    payload = match.group(1) if match else text
    start = payload.find('{')
    end = payload.rfind('}')
    if start == -1 or end == -1:
        raise ValueError('No JSON object was found.')
    return json.loads(payload[start:end + 1])

def _should_switch_model(exc: Exception) -> bool:
    text = str(exc).upper()
    return any((token in text for token in ('429', 'RESOURCE_EXHAUSTED', '404', 'NOT_FOUND')))

def _user_message(exc: Exception | None) -> str:
    text = str(exc or '').upper()
    if 'RESOURCE_EXHAUSTED' in text or '429' in text:
        return 'The Gemini quota for the current model is exhausted. Wait for the daily reset or set GEMINI_MODEL to another available model.'
    if 'NOT_FOUND' in text or '404' in text:
        return 'The configured Gemini chat model is not available. Set GEMINI_MODEL to another model.'
    return 'The language model request failed.'
