import asyncio
import logging
from app.config import get_settings
from app.dependencies import build_ingest_use_case
from app.domain.exceptions import DomainError
from app.logging_config import configure_logging
logger = logging.getLogger(__name__)

def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    use_case = build_ingest_use_case(settings)
    try:
        report = asyncio.run(use_case.execute())
    except DomainError as exc:
        logger.error('%s', exc)
        raise SystemExit(1) from exc
    print(f'Ingested {report.documents} documents and {report.chunks} chunks.')
if __name__ == '__main__':
    main()
