"""Atomic daily token accounting for public model calls."""

from dataclasses import dataclass, field

from qnu.platform.cache import get_redis
from qnu.platform.errors import AppException

TOKEN_TTL = 172800

_RESERVE_TOKENS = """
local used = tonumber(redis.call('GET', KEYS[1]) or '0')
local held = tonumber(redis.call('HGET', KEYS[2], 'total') or '0')
local amount = tonumber(ARGV[2])
if redis.call('HEXISTS', KEYS[2], ARGV[1]) == 1 then return 1 end
if used + held + amount > tonumber(ARGV[3]) then return 0 end
redis.call('HSET', KEYS[2], ARGV[1], amount)
redis.call('HINCRBY', KEYS[2], 'total', amount)
redis.call('EXPIRE', KEYS[2], tonumber(ARGV[4]))
return 1
"""

_SETTLE_TOKENS = """
if ARGV[3] == 'capped' then
    local held = redis.call('HGET', KEYS[2], ARGV[1])
    if not held then return 0 end
    redis.call('HINCRBY', KEYS[2], 'total', -tonumber(held))
    redis.call('HDEL', KEYS[2], ARGV[1])
end
local amount = tonumber(ARGV[2])
if amount > 0 then
    redis.call('INCRBY', KEYS[1], amount)
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[4]))
end
return 1
"""


def _budget_exhausted() -> AppException:
    return AppException(
        "Trợ lý đã đạt hạn mức trả lời trong ngày. Vui lòng quay lại vào ngày mai.",
        code="public_chat_budget_exhausted",
        status_code=429,
    )


@dataclass(slots=True)
class DailyBudget:
    key: str
    limit: int | None
    observed_tokens: int = 0
    _settled: set[str] = field(default_factory=set)

    async def check(self) -> None:
        if self.limit is not None and int(await get_redis().get(self.key) or 0) >= self.limit:
            raise _budget_exhausted()

    async def reserve(self, usage_id: str, tokens: int) -> None:
        if self.limit is None:
            return
        accepted = await get_redis().eval(
            _RESERVE_TOKENS,
            2,
            self.key,
            self.key + ":pending",
            usage_id,
            tokens,
            self.limit,
            TOKEN_TTL,
        )
        if not accepted:
            raise _budget_exhausted()

    async def settle(self, usage_id: str, tokens: int | None) -> None:
        # Unknown usage retains its reservation, just as in ModelOps.
        if tokens is None or usage_id in self._settled:
            return
        self._settled.add(usage_id)
        applied = await get_redis().eval(
            _SETTLE_TOKENS,
            2,
            self.key,
            self.key + ":pending",
            usage_id,
            tokens,
            "unlimited" if self.limit is None else "capped",
            TOKEN_TTL,
        )
        if applied:
            self.observed_tokens += tokens
