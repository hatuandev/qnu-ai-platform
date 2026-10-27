import { GraduationCap, Mail, User } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { StudentRegistrationStudent } from "@/features/student/types";

export function StudentProfileCard({
  student,
}: {
  student: StudentRegistrationStudent | null | undefined;
}) {
  if (!student) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <User className="size-5" />
          </div>
          <div className="min-w-0">
            <CardTitle className="text-base leading-tight">
              {student.fullName}
            </CardTitle>
            <CardDescription>
              Mã sinh viên:{" "}
              <span className="font-mono font-medium text-foreground">
                {student.studentCode}
              </span>
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2.5">
        <p className="flex items-center gap-2 text-sm">
          <GraduationCap className="size-4 shrink-0 text-muted-foreground" />
          {[student.faculty, student.className].filter(Boolean).join(" · ") ||
            "Chưa rõ khoa / lớp"}
        </p>
        {student.schoolEmail || student.studentCode ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Mail className="size-4 shrink-0" />
            <span className="truncate">
              {student.schoolEmail ||
                `${student.studentCode.toLowerCase()}@st.qnu.edu.vn`}
            </span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
