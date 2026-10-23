"""Bounded pages with deterministic continuation and complete source inventory."""
from app.modules.knowledge.wiki_schemas import WikiPage, WikiSection

VERSION = 'qnu-wiki-inventory/v1'
PAGE_SIZE = 512


def stored_pages(compiled: dict, identity: dict) -> list[dict]:
    from app.modules.knowledge.services.wiki_compiler import digest, render_page

    pages = []
    for key, page in compiled.items():
        count = (len(page.sections) + PAGE_SIZE - 1) // PAGE_SIZE
        ids = ['wiki_' + digest([identity, *key, *([part] if count > 1 else [])])[:24]
               for part in range(count)]
        for part in range(count):
            view = WikiPage(kind=page.kind, title=page.title,
                sections=page.sections[part * PAGE_SIZE:(part + 1) * PAGE_SIZE])
            pagination = {'inventory_version': VERSION, 'part': part + 1, 'part_count': count,
                'previous_page_id': ids[part - 1] if part else None,
                'next_page_id': ids[part + 1] if part + 1 < count else None} if count > 1 else {}
            pages.append({**view.model_dump(), **pagination, 'id': ids[part],
                          'markdown': render_page(view, identity)})
    return pages


def validate_inventory(pages: list[dict], identity: dict, units: dict, extractive: bool) -> None:
    from app.modules.knowledge.services.wiki_compiler import invalid

    groups = {}
    for stored in pages:
        groups.setdefault((stored['kind'], stored['title']), []).append(stored)
    if len([key for key in groups if key[0] == 'source']) != 1:
        raise invalid('source_inventory_groups')
    for key, group in groups.items():
        sections = [s for p in group for s in p['sections']]
        # model_construct is for internal aggregation only; each persisted page
        # remains validated with the bounded public contract.
        aggregate = WikiPage.model_construct(kind=key[0], title=key[1],
            sections=[WikiSection.model_validate(s) for s in sections])
        expected = stored_pages({key: aggregate}, identity)
        if group != expected:
            raise invalid('inventory_pagination_changed')
        if extractive:
            selected = [s['excerpt_unit_id'] for s in sections]
            if len(set(selected)) != len(selected):
                raise invalid('duplicate_inventory_unit')
            if key[0] == 'source' and set(selected) != {u.id for u in units.values() if not u.is_container}:
                raise invalid('incomplete_source_inventory')
