"""Validate captured E2E requests against the actual FastAPI routes, offline.

No handler/dependency is executed: this cannot use credentials, databases or LLMs.
"""

import json
import sys
from pathlib import Path

from fastapi.routing import APIRoute
from starlette.routing import Match

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backendV1"))

from qnu.domains.assistants.router import router as assistants
from qnu.domains.conversations.router import router as conversations
from qnu.domains.knowledge.compilation.review.router import (
    router as reviews,
)
from qnu.domains.knowledge.compilation.router import (
    router as compilations,
)
from qnu.domains.knowledge.index.router import router as indexes
from qnu.domains.knowledge.publication.router import (
    router as publications,
)
from qnu.domains.ocr.review.router import router as text_review
from qnu.domains.ocr.router import router as ocr


def check(requests: list[dict]) -> list[dict]:
    routes = [
        route
        for router in (
            compilations,
            reviews,
            publications,
            indexes,
            assistants,
            conversations,
            text_review,
            ocr,
        )
        for route in router.routes
    ]
    checked = []
    for item in requests:
        path, _, query = item["path"].partition("?")
        scope = {
            "type": "http",
            "method": item["method"],
            "path": path,
            "root_path": "",
        }
        found = next(
            (
                r
                for r in routes
                if isinstance(r, APIRoute) and r.matches(scope)[0] == Match.FULL
            ),
            None,
        )
        if found is None:
            raise ValueError(f"Unknown route: {item['method']} {path}")
        if found.body_field:
            _, errors = found.body_field.validate(item.get("body"), {}, loc=("body",))
            if errors:
                # Deliberately exclude input values; callers only need field/type.
                raise ValueError(str([(e["loc"], e["type"]) for e in errors]))
        headers = {k.lower(): v for k, v in item.get("headers", {}).items()}
        for field in found.dependant.header_params:
            value = headers.get(field.alias.lower(), field.default)
            _, errors = field.validate(value, {}, loc=("header", field.alias))
            if errors:
                raise ValueError(f"Invalid header: {field.alias}")
        from urllib.parse import parse_qs

        params = parse_qs(query)
        for field in found.dependant.query_params:
            if field.alias in params:
                _, errors = field.validate(
                    params[field.alias][0], {}, loc=("query", field.alias)
                )
                if errors:
                    raise ValueError(f"Invalid query: {field.alias}")
        checked.append({"method": item["method"], "route": found.path})
    return checked


if __name__ == "__main__":
    try:
        print(json.dumps({"checked": check(json.load(sys.stdin))}))
    except (ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
