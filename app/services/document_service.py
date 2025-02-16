import os
from datetime import datetime
from uuid import UUID

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models import File

load_dotenv()


async def extract_text(document_url: str, file_id: UUID, session: Session):
    """
    Process the uploaded file by making an HTTP POST request and update the
    contents field.
    """
    auth_token = os.getenv('AUTH_TOKEN')
    headers = {'Authorization': f'Bearer {auth_token}'}

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=60)) as client:
        response = await client.post(
            'https://habibasseiss--docling-process.modal.run',
            headers=headers,
            json={'document_url': document_url},
        )
        response.raise_for_status()

        # Update the contents field with the result
        result_content = response.text
        file_record = session.get(File, file_id)
        if file_record:
            file_record.contents = result_content
            file_record.processed_at = datetime.now()
            session.commit()
