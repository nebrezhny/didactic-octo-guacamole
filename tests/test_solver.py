import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.services.solver import solve_task

@pytest.mark.asyncio
async def test_solve_task_text():
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Решение: 4"))]
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=50, completion_tokens=50)
    
    async_mock = AsyncMock(return_value=mock_response)
    client.chat.completions.create = async_mock

    answer, tokens, cost = await solve_task(client, "Russia", "math", "2+2")
    
    assert "Решение: 4" in answer
    assert tokens == 100
    # Text cost: 50 * 0.00015 + 50 * 0.0006 = 0.0000075 + 0.00003 = 0.0000375
    assert cost > 0.0
