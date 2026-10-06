export interface AuthActor {
  username: string;
  tenant_id: string;
  workspace_id: string;
  role: string;
  authenticated: boolean;
}

export interface AuthStatusResponse {
  authenticated: boolean;
  actor?: AuthActor | null;
  message?: string | null;
}

export interface DevLoginRequest {
  access_key: string;
}
