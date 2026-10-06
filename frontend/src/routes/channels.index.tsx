import { createFileRoute } from "@tanstack/react-router";
import { ChannelsPage } from "@/features/channels/channels-page";

export const Route = createFileRoute("/channels/")({
  component: ChannelsPage,
});
