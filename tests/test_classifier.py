import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.services.classifier import classify_subject

@pytest.mark.asyncio
async def test_classify_subject_math():
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="math"))]
    
    # We mock the async call correctly
    async_mock = AsyncMock(return_value=mock_response)
    client.chat.completions.create = async_mock

    subject = await classify_subject(client, "2 + 2 = ?")
    assert subject == "math"

@pytest.mark.asyncio
async def test_classify_subject_invalid():
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="unknown_subject"))]
    
    async_mock = AsyncMock(return_value=mock_response)
    client.chat.completions.create = async_mock

    subject = await classify_subject(client, "What is the meaning of life?")
    assert subject == "other"
