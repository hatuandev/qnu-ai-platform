"""Public chat continuation requires a signed capability, not a guessed conversation ID."""
import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.modules.conversations.models import ConversationThreadModel

HEADER = 'X-Conversation-Token'
AUDIENCE = 'qnu-assistant-conversation-v1'


def _key() -> bytes:
    # Domain separation: this token MUST NOT be accepted as a platform/SSO access token.
    return hmac.new(get_settings().SECRET_KEY.encode(), AUDIENCE.encode(), hashlib.sha256).digest()


def issue_grant(reference: str, conversation_id: str) -> str:
    return jwt.encode({'assistant': reference, 'conversation': conversation_id, 'aud': AUDIENCE,
        'exp': datetime.now(UTC) + timedelta(days=1)}, _key(), algorithm='HS256')


def verify_grant(token: str, reference: str, conversation_id: str) -> None:
    try:
        if len(token) > 2048:
            raise ValueError('Oversized capability')
        claims = jwt.decode(token, _key(), algorithms=['HS256'], audience=AUDIENCE,
            options={'require': ['aud', 'exp', 'assistant', 'conversation']})
        if claims['assistant'] != reference or claims['conversation'] != conversation_id:
            raise ValueError('Capability scope mismatch')
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AppException('Không thể truy cập phiên hội thoại này. Hãy bắt đầu hội thoại mới.',
            code='conversation_not_found', status_code=404) from exc


async def authorize_conversation(db: AsyncSession, reference: str, conversation_id: str | None,
                                 token: str | None, *, privileged: bool = False) -> tuple[str, str]:
    if conversation_id:
        thread = (await db.execute(select(ConversationThreadModel.id).where(
            ConversationThreadModel.id == conversation_id))).scalar_one_or_none()
        if token:
            verify_grant(token, reference, conversation_id)
            if not thread:
                raise AppException('Phiên hội thoại không còn tồn tại. Hãy bắt đầu hội thoại mới.',
                    code='conversation_not_found', status_code=404)
            return conversation_id, issue_grant(reference, conversation_id)
        if thread:
            if not privileged:
                raise AppException('Không thể truy cập phiên hội thoại này. Hãy bắt đầu hội thoại mới.',
                    code='conversation_not_found', status_code=404)
            return conversation_id, issue_grant(reference, conversation_id)
    # Do not let simultaneous anonymous clients reserve the same client-chosen ID.
    created = 'conv_' + uuid.uuid4().hex[:24]
    return created, issue_grant(reference, created)
