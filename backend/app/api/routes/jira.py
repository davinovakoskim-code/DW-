from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chamado import JiraImportResult
from app.services.jira_service import JiraImportService

router = APIRouter(prefix="/jira", tags=["Jira"])


@router.post("/importar-chamados", response_model=JiraImportResult)
def importar_chamados(db: Session = Depends(get_db)):
    """Importa ate 50 chamados criados nos ultimos 90 dias no Jira."""
    return JiraImportService.importar_chamados(db=db)

