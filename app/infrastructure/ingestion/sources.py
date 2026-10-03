from dataclasses import dataclass
from urllib.parse import urlsplit
OFFICIAL_DOCS_HOST = 'fastapi.tiangolo.com'

@dataclass(frozen=True)
class DocumentationPage:
    title: str
    url: str

    @property
    def slug(self) -> str:
        path = urlsplit(self.url).path.strip('/')
        return path.replace('/', '_') or 'index'
OFFICIAL_FASTAPI_PAGES: tuple[DocumentationPage, ...] = (DocumentationPage('First Steps', 'https://fastapi.tiangolo.com/tutorial/first-steps/'), DocumentationPage('Path Parameters', 'https://fastapi.tiangolo.com/tutorial/path-params/'), DocumentationPage('Query Parameters', 'https://fastapi.tiangolo.com/tutorial/query-params/'), DocumentationPage('Request Body', 'https://fastapi.tiangolo.com/tutorial/body/'), DocumentationPage('Response Model', 'https://fastapi.tiangolo.com/tutorial/response-model/'), DocumentationPage('Dependencies', 'https://fastapi.tiangolo.com/tutorial/dependencies/'), DocumentationPage('Security', 'https://fastapi.tiangolo.com/tutorial/security/first-steps/'), DocumentationPage('Middleware', 'https://fastapi.tiangolo.com/tutorial/middleware/'), DocumentationPage('Background Tasks', 'https://fastapi.tiangolo.com/tutorial/background-tasks/'), DocumentationPage('Async', 'https://fastapi.tiangolo.com/async/'), DocumentationPage('Handling Errors', 'https://fastapi.tiangolo.com/tutorial/handling-errors/'))
