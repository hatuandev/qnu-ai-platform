export type ActivityResource = "users" | "roles" | "settings" | "security";
export type ActivityEventType =
  | "user.created"
  | "user.updated"
  | "user.deleted"
  | "role.created"
  | "role.updated"
  | "settings.updated"
  | "security.changed";

export type ActivityEvent = {
  id: string;
  type: ActivityEventType;
  resource: ActivityResource;
  actor: string;
  actorInitials: string;
  action: string;
  subject: string;
  createdAt: string;
  metadata?: Record<string, string>;
};
