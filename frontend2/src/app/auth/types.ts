export type BackendRoleMetadata = {
  key: string;
  displayName?: string | null;
  description?: string | null;
  isSystem: boolean;
  isEnabled: boolean;
  permissionCount: number;
};

export type CurrentUser = {
  sub: string;
  email: string;
  name: string;
  userType: string;
  roles: string[];
  permissions: string[];
  roleMetadata: BackendRoleMetadata[];
};
