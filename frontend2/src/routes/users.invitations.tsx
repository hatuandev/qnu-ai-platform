import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { MailPlus } from "lucide-react";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRbac } from "@/rbac/context";
export const Route = createFileRoute("/users/invitations")({
  component: InvitationsPage,
});
function InvitationsPage() {
  const { can, roles } = useRbac();
  const navigate = useNavigate({ from: "/users/invitations" });
  if (!can("users.create")) return <AccessDenied />;
  const invitations = [
    { email: "maya.chen@example.com", roleKey: "editor", sent: "Hôm nay" },
    { email: "noah.wilson@example.com", roleKey: "viewer", sent: "Hôm qua" },
  ];
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Quản lý / Người dùng"
        title="Lời mời"
        description="Danh sách đơn giản sử dụng lại cùng hợp đồng thiết kế của các primitive."
        actions={
          <Button
            onClick={() =>
              void navigate({
                to: "/users",
                search: {
                  q: "",
                  roles: "",
                  statuses: "",
                  create: true,
                  page: 1,
                  pageSize: 10,
                  sort: "createdAt.desc",
                },
              })
            }
          >
            <MailPlus />
            Mời người dùng
          </Button>
        }
      />
      <div className="overflow-hidden rounded-lg border bg-card">
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Vai trò</TableHead>
              <TableHead>Đã gửi</TableHead>
              <TableHead>Trạng thái</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invitations.map((invitation) => (
              <TableRow key={invitation.email}>
                <TableCell className="font-medium">
                  {invitation.email}
                </TableCell>
                <TableCell>
                  {roles.find((role) => role.key === invitation.roleKey)
                    ?.name ?? invitation.roleKey}
                </TableCell>
                <TableCell>{invitation.sent}</TableCell>
                <TableCell>
                  <Badge variant="warning">Đang chờ</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
