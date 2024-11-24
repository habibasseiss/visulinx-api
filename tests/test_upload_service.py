from http import HTTPStatus
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.stub import Stubber
from fastapi import UploadFile

from app.services.upload_service import upload_file_to_s3
from app.settings import Settings

settings = Settings()


@pytest.mark.asyncio
async def test_upload_file_to_s3():
    # Initialize a real boto3 S3 client and wrap it with Stubber
    s3_client = boto3.client('s3')
    stubber = Stubber(s3_client)

    # Mock UUID generation to return a fixed value
    uuid = '327d7bdb-f820-412f-8c5a-34f61ff321be'
    with patch('app.services.upload_service.uuid4', return_value=uuid):
        # Mock the response for put_object
        expected_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        stubber.add_response(
            'put_object',
            expected_response,
            {
                'Body': b'Sample file content',
                'Bucket': settings.BUCKET_NAME,
                'ContentType': 'text/plain',
                'Key': f'projects/test_project_id/{uuid}.txt',
                'Metadata': {'filename': 'test.txt'},
            },
        )

        # Activate the Stubber
        stubber.activate()

        # Mock UploadFile to simulate an uploaded file
        file_content = b'Sample file content'
        file = UploadFile(filename='test.txt', file=MagicMock())
        file.file.read = MagicMock(return_value=file_content)

        # Patch the S3 client used in the service to use the stubbed client
        with patch(
            'app.services.upload_service.boto3.client',
            return_value=s3_client,
        ):
            # Call the upload function
            result = await upload_file_to_s3('test_project_id', file)

            # Assertions
            assert result['status_code'] == HTTPStatus.OK
            assert 'path' in result

        # Deactivate the Stubber
        stubber.deactivate()
