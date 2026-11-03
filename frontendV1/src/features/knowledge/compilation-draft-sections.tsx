import { Tag } from "lucide-react";
import { memo } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import type { DraftSection } from "./compilation-types";

export const CompilationDraftSections = memo(function CompilationDraftSections({
  sections,
  onSelectCitation,
}: {
  sections: DraftSection[];
  onSelectCitation: (id: string) => void;
}) {
  return (
    <Accordion type="multiple" defaultValue={["section-0"]}>
      {sections.map((section, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: immutable ordered sections of a pinned run
        <AccordionItem key={`section-${index}`} value={`section-${index}`}>
          <AccordionTrigger className="text-sm sm:text-base">
            {section.heading}
          </AccordionTrigger>
          <AccordionContent className="text-foreground [&>div]:pr-0">
            <div className="space-y-3">
              {section.paragraphs.map((paragraph, paragraphIndex) => (
                <div
                  // biome-ignore lint/suspicious/noArrayIndexKey: immutable ordered document
                  key={paragraphIndex}
                  className="text-sm leading-relaxed"
                >
                  <span>{paragraph.text}</span>
                  <span className="inline-flex flex-wrap gap-1 ml-1.5 align-baseline">
                    {paragraph.citations.map((id, citationIndex) => (
                      <Button
                        key={id}
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => onSelectCitation(id)}
                        className="h-6 px-1.5 text-xs text-primary"
                        aria-label={`Xem dẫn chứng ${citationIndex + 1} của đoạn ${index + 1}.${paragraphIndex + 1}`}
                      >
                        <Tag className="size-3" />
                        {citationIndex + 1}
                      </Button>
                    ))}
                  </span>
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
});
