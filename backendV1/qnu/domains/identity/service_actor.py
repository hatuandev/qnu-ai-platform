"""Fixed internal identity for anonymous public-chatbot turns.

Only server code builds this actor, and only after it has resolved an enabled
publication row; no request field can supply it. ``resolve_workspace_access``
admits it for read-role requirements on active workspaces and nothing else.
"""

from qnu.domains.identity.actor import AuthActor

PUBLIC_CHATBOT_ACTOR_ID = "svc:public-chatbot"


def public_chatbot_actor() -> AuthActor:
    return AuthActor(
        username="public-chatbot",
        actor_id=PUBLIC_CHATBOT_ACTOR_ID,
        display_name="Trợ lý công khai",
        user_type="service",
        role="service",
        roles=[],
        permissions=[],
        authenticated=True,
    )


def is_public_chatbot_actor(actor: AuthActor) -> bool:
    return actor.user_type == "service" and actor.actor_id == PUBLIC_CHATBOT_ACTOR_ID
