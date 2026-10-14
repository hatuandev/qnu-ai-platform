import { useNavigate } from "@tanstack/react-router";
import { FileText, MoreHorizontal, Scan } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { KnowledgeBinding } from "@/types/knowledge";
import { DeleteSourceButton } from "./delete-source-button";
import { PauseSourceButton } from "./pause-source-button";
import { VectorLoadControls } from "./vector-load-controls";

export function SourceActionsMenu({
  collectionId,
  source,
  generationId,
  canLoad,
  onDeleted,
}: {
  collectionId: string;
  source: KnowledgeBinding;
  generationId: string;
  canLoad: boolean;
  onDeleted: () => void;
}) {
  const navigate = useNavigate();
  const title = source.document_title || source.id;

  // Keep action owners outside the menu so closing it does not unmount dialogs or job tracking.
  return (
    <VectorLoadControls
      collectionId={collectionId}
      initialGenerationId={generationId}
      targets={
        canLoad
          ? [
              {
                binding_id: source.id,
                source_revision_id: source.active_source_revision_id || "",
              },
            ]
          : []
      }
      disabledReason={
        canLoad ? undefined : "Hãy bóc tách và duyệt Markdown trước."
      }
      renderTrigger={(vectorItem) => (
        <PauseSourceButton
          sourceId={source.id}
          title={title}
          status={source.status}
          renderTrigger={(pauseItem) => (
            <DeleteSourceButton
              sourceId={source.id}
              status={source.status}
              title={title}
              onDeleted={onDeleted}
              renderTrigger={(deleteItem) => (
                <DropdownMenu modal={false}>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="icon-sm"
                      variant="ghost"
                      aria-label={`Thao tác với ${title}`}
                      title="Thao tác"
                    >
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {vectorItem}
                    <DropdownMenuItem
                      onSelect={() =>
                        navigate({
                          to: "/knowledge/$collectionId/sources/$sourceId",
                          search: { view: "studio", revision: undefined },
                          params: { collectionId, sourceId: source.id },
                        })
                      }
                    >
                      <Scan /> Studio OCR
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onSelect={() =>
                        navigate({
                          to: "/knowledge/$collectionId/sources/$sourceId",
                          search: { view: undefined, revision: undefined },
                          params: { collectionId, sourceId: source.id },
                        })
                      }
                    >
                      <FileText /> Chi tiết
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {pauseItem}
                    {deleteItem}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            />
          )}
        />
      )}
    />
  );
}
