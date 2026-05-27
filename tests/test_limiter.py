import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.services.limiter import LimiterService

@pytest.mark.asyncio
async def test_check_and_increment_free_requests_allowed():
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()
    
    limiter = LimiterService(mock_redis, 3.0)
    allowed = await limiter.check_and_increment_free_requests(123)
    
    assert allowed is True
    mock_redis.expire.assert_called_once()

@pytest.mark.asyncio
async def test_check_and_increment_free_requests_denied():
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(return_value=6) # max is 5
    mock_redis.decr = AsyncMock()
    
    limiter = LimiterService(mock_redis, 3.0)
    allowed = await limiter.check_and_increment_free_requests(123)
    
    assert allowed is False
    mock_redis.decr.assert_called_once()

@pytest.mark.asyncio
async def test_reserve_budget_allowed():
    mock_redis = MagicMock()
    mock_redis.incrbyfloat = AsyncMock(return_value=1.5) # limit is 3.0
    
    limiter = LimiterService(mock_redis, 3.0)
    allowed = await limiter.reserve_budget(0.05)
    
    assert allowed is True

@pytest.mark.asyncio
async def test_reserve_budget_denied():
    mock_redis = MagicMock()
    mock_redis.incrbyfloat = AsyncMock(side_effect=[3.1, 3.05]) # limit is 3.0, revert returns 3.05
    
    limiter = LimiterService(mock_redis, 3.0)
    allowed = await limiter.reserve_budget(0.1)
    
    assert allowed is False
    assert mock_redis.incrbyfloat.call_count == 2
