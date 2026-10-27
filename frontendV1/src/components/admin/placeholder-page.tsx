import { PageHeader } from "@/components/admin/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
export function PlaceholderPage({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-7">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <Card>
        <CardHeader>
          <CardTitle>Nền tảng đã sẵn sàng</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Trang này được giữ gọn để làm nền tảng. Hãy xây dựng nội dung riêng
            cho từng tính năng mà không tạo thêm các primitive giao diện thay
            thế.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
