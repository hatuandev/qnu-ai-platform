import { createFileRoute } from "@tanstack/react-router";
import { PublicChatPortal } from "@/features/chat/public-chat-portal";

export const Route = createFileRoute("/chat/")({
  component: PublicChatPortal,
});
