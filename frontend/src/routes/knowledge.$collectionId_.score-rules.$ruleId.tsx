import { createFileRoute } from "@tanstack/react-router";
import { ScoreRuleDetail } from "@/features/knowledge/score-rule-detail";

export const Route = createFileRoute(
  "/knowledge/$collectionId_/score-rules/$ruleId",
)({ component: ScoreRuleDetailRoute });

function ScoreRuleDetailRoute() {
  const { collectionId, ruleId } = Route.useParams();
  return <ScoreRuleDetail collectionId={collectionId} ruleId={ruleId} />;
}
