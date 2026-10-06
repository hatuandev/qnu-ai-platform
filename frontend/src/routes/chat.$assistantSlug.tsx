import { createFileRoute } from "@tanstack/react-router";
import { PublicChatView } from "@/features/chat/public-chat-view";

interface ChatSearchParams {
  q?: string;
}

export const Route = createFileRoute("/chat/$assistantSlug")({
  validateSearch: (search: Record<string, unknown>): ChatSearchParams => {
    return {
      q: typeof search.q === "string" ? search.q : undefined,
    };
  },
  component: ChatRouteComponent,
});

function ChatRouteComponent() {
  const { assistantSlug } = Route.useParams();
  const { q } = Route.useSearch();
  return <PublicChatView assistantSlug={assistantSlug} initialQuestion={q} />;
}
