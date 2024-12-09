import logging
import mimetypes
from http import HTTPStatus
from uuid import UUID, uuid4

import boto3
import magic
from fastapi import HTTPException, UploadFile
from mypy_boto3_s3.client import S3Client

from app.schemas import FileSchema
from app.settings import Settings

logger = logging.getLogger(__name__)

settings = Settings.model_validate({})


async def upload_file_to_s3(project_id: UUID, file: UploadFile) -> FileSchema:
    contents = await file.read()
    mime_type = str(magic.from_buffer(contents, mime=True))
    filesize = len(contents)
    extension = mimetypes.guess_extension(mime_type)

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
        ContentType=mime_type,
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
        mime_type=mime_type,
        original_filename=str(file.filename),
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


async def get_download_url(file_path: str, original_filename: str) -> str:
    if not file_path:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='No file path provided.',
        )

    s3: S3Client = boto3.client('s3')
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.BUCKET_NAME,
                'Key': file_path,
                'ResponseContentDisposition': f'attachment; filename="{original_filename}"',  # noqa: E501
            },
            ExpiresIn=60,  # URL expires in 60 seconds
        )
        return url
    except Exception as e:
        logger.error(f'Error generating presigned URL: {str(e)}')
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Failed to generate download URL.',
        )
