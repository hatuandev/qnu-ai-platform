import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { InboxPage } from "@/features/inbox/inbox-page";
import { INBOX_KINDS } from "@/features/inbox/inbox-schemas";
import { pageSearchSchema } from "@/features/workspaces/search";

const inboxSearchSchema = pageSearchSchema.extend({
  kind: z.enum(INBOX_KINDS).optional().catch(undefined),
  collectionId: z.string().optional().catch(undefined),
});

export const Route = createFileRoute("/workspaces/$workspaceId/inbox")({
  validateSearch: (search) => inboxSearchSchema.parse(search),
  component: InboxRoute,
});

function InboxRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <InboxPage
      workspaceId={workspaceId}
      page={search.page}
      pageSize={search.pageSize}
      kind={search.kind}
      collectionId={search.collectionId}
      onKindChange={(kind) =>
        void navigate({
          search: (previous) => ({ ...previous, kind, page: 1 }),
        })
      }
      onCollectionChange={(collectionId) =>
        void navigate({
          search: (previous) => ({ ...previous, collectionId, page: 1 }),
        })
      }
      onResetFilters={() =>
        void navigate({
          search: (previous) => ({
            ...previous,
            kind: undefined,
            collectionId: undefined,
            page: 1,
          }),
        })
      }
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
      onPageSizeChange={(pageSize) =>
        void navigate({
          search: (previous) => ({ ...previous, pageSize, page: 1 }),
        })
      }
    />
  );
}
