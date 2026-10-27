/** Actor contract returned by `GET /auth/me` (`qnu.domains.identity.actor.AuthActor`). */

export type V1Actor = {
  username: string;
  actor_id: string;
  display_name: string;
  email: string | null;
  user_type: string;
  role: string;
  roles: string[];
  permissions: string[];
  authenticated: boolean;
};

export type V1LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type V1ActorResponse = { actor: V1Actor };
