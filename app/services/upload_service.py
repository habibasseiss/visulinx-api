# This module will handle the upload functionality for projects.

import mimetypes
from http import HTTPStatus
from uuid import UUID, uuid4

import boto3
import magic
from fastapi import HTTPException, UploadFile
from mypy_boto3_s3.client import S3Client

from app.settings import Settings

settings = Settings()


async def upload_file_to_s3(project_id: UUID, file: UploadFile):
    if not file:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='No file uploaded.',
        )

    contents = await file.read()
    filetype = magic.from_buffer(contents, mime=True)
    extension = mimetypes.guess_extension(filetype)

    if not extension:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Unsupported file type.',
        )

    key = f'projects/{project_id}/{uuid4()}{extension}'

    # Save the file to S3
    s3: S3Client = boto3.client('s3')
    s3response = s3.put_object(
        Body=contents,
        Bucket=settings.BUCKET_NAME,
        Key=key,
        ContentType=filetype,
        Metadata={
            'filename': str(file.filename),
        },
    )

    return {
        'path': key,
        'status_code': s3response['ResponseMetadata']['HTTPStatusCode'],
    }
