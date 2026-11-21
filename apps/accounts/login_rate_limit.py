import math
import threading
import time
from dataclasses import dataclass
from typing import Any

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

MAX_FAILURES = 10
LOCKOUT_SECONDS = (5 * 60, 10 * 60)
CACHE_KEY_PREFIX = "accounts:login_rl"
_STATE_TTL = max(LOCKOUT_SECONDS) + (MAX_FAILURES * 60)

_LUA_SCRIPT = """
local key = KEYS[1]
local max_failures = tonumber(ARGV[1])
local lockout_0 = tonumber(ARGV[2])
local lockout_1 = tonumber(ARGV[3])
local now = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])
local action = ARGV[6]

local function reply(locked, retry_after, attempts_left)
  return {locked, retry_after, attempts_left}
end

if action == 'clear' then
  redis.call('DEL', key)
  return reply(0, 0, max_failures)
end

local failures = tonumber(redis.call('HGET', key, 'failures') or '0')
local lockout_until = tonumber(redis.call('HGET', key, 'lockout_until') or '0')
local stage = tonumber(redis.call('HGET', key, 'stage') or '0')

if lockout_until > now then
  local retry = math.ceil(lockout_until - now)
  if retry < 1 then retry = 1 end
  return reply(1, retry, 0)
end

if action == 'check' then
  return reply(0, 0, max_failures - failures)
end

failures = failures + 1
if failures >= max_failures then
  local duration = lockout_0
  if stage >= 1 then
    duration = lockout_1
  end
  lockout_until = now + duration
  failures = 0
  if stage < 1 then
    stage = 1
  end
  redis.call(
    'HSET', key,
    'failures', failures,
    'lockout_until', lockout_until,
    'stage', stage
  )
  redis.call('EXPIRE', key, ttl)
  local retry = math.ceil(duration)
  if retry < 1 then retry = 1 end
  return reply(1, retry, 0)
end

redis.call(
  'HSET', key,
  'failures', failures,
  'lockout_until', lockout_until,
  'stage', stage
)
redis.call('EXPIRE', key, ttl)
return reply(0, 0, max_failures - failures)
"""

_redis_script_sha: str | None = None
_redis_script_lock = threading.Lock()

_fallback_state: dict[str, dict[str, float | int]] = {}
_fallback_locks: dict[str, threading.Lock] = {}
_fallback_registry_lock = threading.Lock()


@dataclass(frozen=True)
class BlockStatus:
    retry_after_seconds: int
    scope: str


@dataclass(frozen=True)
class FailureStatus:
    locked: bool
    retry_after_seconds: int | None
    scope: str | None
    attempts_until_lockout: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempts_until_lockout": self.attempts_until_lockout,
            "retry_after_seconds": self.retry_after_seconds,
        }


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def normalize_username(username: Any) -> str:
    if not isinstance(username, str):
        return ""
    return username.strip().lower()


def is_auth_failure(errors: dict) -> bool:
    return bool(errors.get("non_field_errors"))


def _logical_key(scope: str, identifier: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{scope}:{identifier}"


def _storage_key(scope: str, identifier: str) -> str:
    return cache.make_key(_logical_key(scope, identifier))


def _get_redis_client():
    client_wrapper = getattr(cache, "client", None)
    if client_wrapper is None or not hasattr(client_wrapper, "get_client"):
        return None
    try:
        client = client_wrapper.get_client(write=True)
    except Exception:
        return None
    if client is None or not callable(getattr(client, "evalsha", None)):
        return None
    return client


def _parse_script_result(result: Any) -> tuple[int, int, int]:
    locked, retry_after, attempts_left = result
    return int(locked), int(retry_after), int(attempts_left)


def _empty_status() -> FailureStatus:
    return FailureStatus(
        locked=False,
        retry_after_seconds=None,
        scope=None,
        attempts_until_lockout=MAX_FAILURES,
    )


def _to_failure_status(
    scope: str, locked: int, retry_after: int, attempts_left: int
) -> FailureStatus:
    if locked:
        return FailureStatus(
            locked=True,
            retry_after_seconds=max(1, retry_after),
            scope=scope,
            attempts_until_lockout=0,
        )
    return FailureStatus(
        locked=False,
        retry_after_seconds=None,
        scope=None,
        attempts_until_lockout=max(0, attempts_left),
    )


def _fallback_lock(logical_key: str) -> threading.Lock:
    with _fallback_registry_lock:
        lock = _fallback_locks.get(logical_key)
        if lock is None:
            lock = threading.Lock()
            _fallback_locks[logical_key] = lock
        return lock


def _fallback_get_state(logical_key: str) -> dict[str, float | int]:
    state = _fallback_state.get(logical_key)
    if state is None:
        return {"failures": 0, "lockout_until": 0.0, "stage": 0}
    return {
        "failures": int(state.get("failures") or 0),
        "lockout_until": float(state.get("lockout_until") or 0.0),
        "stage": min(int(state.get("stage") or 0), len(LOCKOUT_SECONDS) - 1),
    }


def _fallback_apply(logical_key: str, action: str) -> tuple[int, int, int]:
    lock = _fallback_lock(logical_key)
    with lock:
        if action == "clear":
            _fallback_state.pop(logical_key, None)
            return 0, 0, MAX_FAILURES

        state = _fallback_get_state(logical_key)
        now = time.time()

        if state["lockout_until"] > now:
            retry = max(1, int(math.ceil(state["lockout_until"] - now)))
            return 1, retry, 0

        if action == "check":
            return 0, 0, MAX_FAILURES - int(state["failures"])

        state["failures"] = int(state["failures"]) + 1
        if state["failures"] >= MAX_FAILURES:
            stage = int(state["stage"])
            duration = LOCKOUT_SECONDS[0] if stage < 1 else LOCKOUT_SECONDS[1]
            state["lockout_until"] = now + duration
            state["failures"] = 0
            if stage < 1:
                state["stage"] = 1
            _fallback_state[logical_key] = state
            return 1, max(1, int(math.ceil(duration))), 0

        _fallback_state[logical_key] = state
        return 0, 0, MAX_FAILURES - int(state["failures"])


def _run_script(scope: str, identifier: str, action: str) -> tuple[int, int, int]:
    logical_key = _logical_key(scope, identifier)
    redis_client = _get_redis_client()
    if redis_client is None:
        return _fallback_apply(logical_key, action)

    key = _storage_key(scope, identifier)
    args = (
        MAX_FAILURES,
        LOCKOUT_SECONDS[0],
        LOCKOUT_SECONDS[1],
        int(time.time()),
        _STATE_TTL,
        action,
    )

    global _redis_script_sha
    with _redis_script_lock:
        if _redis_script_sha is None:
            _redis_script_sha = redis_client.script_load(_LUA_SCRIPT)

    try:
        result = redis_client.evalsha(_redis_script_sha, 1, key, *args)
    except Exception:
        with _redis_script_lock:
            _redis_script_sha = redis_client.script_load(_LUA_SCRIPT)
        result = redis_client.evalsha(_redis_script_sha, 1, key, *args)

    return _parse_script_result(result)


def _check_scope(scope: str, identifier: str) -> BlockStatus | None:
    if not identifier:
        return None
    locked, retry_after, _ = _run_script(scope, identifier, "check")
    if not locked:
        return None
    return BlockStatus(retry_after_seconds=retry_after, scope=scope)


def check_blocked(ip: str, username: str) -> BlockStatus | None:
    candidates: list[BlockStatus] = []
    for scope, identifier in (("ip", ip), ("username", username)):
        status_info = _check_scope(scope, identifier)
        if status_info is not None:
            candidates.append(status_info)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.retry_after_seconds)


def lockout_response(retry_after_seconds: int, scope: str) -> Response:
    return Response(
        {
            "detail": "Too many failed login attempts.",
            "retry_after_seconds": retry_after_seconds,
            "rate_limited_by": scope,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def _record_failure_for(scope: str, identifier: str) -> FailureStatus:
    if not identifier:
        return _empty_status()
    locked, retry_after, attempts_left = _run_script(scope, identifier, "record")
    return _to_failure_status(scope, locked, retry_after, attempts_left)


def record_failures(ip: str, username: str) -> FailureStatus:
    ip_status = _record_failure_for("ip", ip)
    user_status = _record_failure_for("username", username)
    if ip_status.locked and user_status.locked:
        if (ip_status.retry_after_seconds or 0) >= (user_status.retry_after_seconds or 0):
            return ip_status
        return user_status
    if ip_status.locked:
        return ip_status
    if user_status.locked:
        return user_status
    return FailureStatus(
        locked=False,
        retry_after_seconds=None,
        scope=None,
        attempts_until_lockout=min(
            ip_status.attempts_until_lockout,
            user_status.attempts_until_lockout
            if username
            else ip_status.attempts_until_lockout,
        ),
    )


def clear(ip: str, username: str) -> None:
    for scope, identifier in (("ip", ip), ("username", username)):
        if identifier:
            _run_script(scope, identifier, "clear")
