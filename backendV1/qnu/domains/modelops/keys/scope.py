"""One credential owner per connection; legacy model credentials remain restricted."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.platform.errors import EntityNotFound


def key_scope(provider: Provider):
    owner = provider.parent_id or provider.id
    if provider.is_connection:
        return ProviderKey.provider_id == owner
    return (ProviderKey.provider_id == owner) & or_(
        ProviderKey.model_ids.is_(None), ProviderKey.model_ids.contains([provider.id])
    )


async def credential_owner(db: AsyncSession, provider_id: str, *, lock: bool = False) -> Provider:
    provider = await db.get(Provider, provider_id)
    if provider is None:
        raise EntityNotFound("Không tìm thấy nhà cung cấp/model.", code="provider_not_found")
    stmt = select(Provider).where(Provider.id == (provider.parent_id or provider.id))
    if lock:
        stmt = stmt.with_for_update()
    return (await db.scalars(stmt.execution_options(populate_existing=True))).one()
