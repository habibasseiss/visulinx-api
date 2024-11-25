import mimetypes
from http import HTTPStatus
from uuid import UUID, uuid4

import boto3
import magic
from fastapi import HTTPException, UploadFile
from mypy_boto3_s3.client import S3Client

from app.schemas import FileSchema
from app.settings import Settings

settings = Settings.model_validate({})


async def upload_file_to_s3(project_id: UUID, file: UploadFile) -> FileSchema:
    contents = await file.read()
    filetype = magic.from_buffer(contents, mime=True)
    filesize = len(contents)
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

    if s3response['ResponseMetadata']['HTTPStatusCode'] != HTTPStatus.OK:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Failed to upload file to S3.',
        )

    return FileSchema(
        path=key,
        size=filesize,
    )


async def delete_file_from_s3(file_path: str) -> None:
    if not file_path:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='No file path provided.',
        )

    # Delete the file from S3
    s3: S3Client = boto3.client('s3')

    s3response = s3.delete_object(
        Bucket=settings.BUCKET_NAME,
        Key=file_path,
    )
    response_code = s3response['ResponseMetadata']['HTTPStatusCode']
    if response_code != HTTPStatus.NO_CONTENT:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Failed to delete file from S3.',
        )
