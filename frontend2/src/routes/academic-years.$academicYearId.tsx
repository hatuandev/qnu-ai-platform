import { createFileRoute } from "@tanstack/react-router";
import { AcademicYearDetail } from "@/features/academic-years/academic-year-detail";
export const Route = createFileRoute("/academic-years/$academicYearId")({
  component: () => <AcademicYearDetail id={Route.useParams().academicYearId} />,
});
