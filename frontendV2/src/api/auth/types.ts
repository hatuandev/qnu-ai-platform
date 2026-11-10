/**
 * Authentication and identity DTOs.
 * Mirrors `backendV1/qnu/domains/identity/schemas.py`.
 */

export type AuthActor = {
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

export type ActorResponse = {
  actor: AuthActor;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  default_workspace_code?: string;
};

export type DevLoginRequest = {
  access_key: string;
};

export type LogoutResponse = {
  status: string;
};
