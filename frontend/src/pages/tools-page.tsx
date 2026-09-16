import { useQuery } from "@tanstack/react-query";
import {
  FileSpreadsheet,
  FileText,
  GraduationCap,
  Layers,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { AdministrativeTemplatesView } from "../components/admin/administrative-templates-view";
import { BloomMatrixEditor } from "../components/admin/bloom-matrix-editor";
import { DocxNd30Editor, type DocxNd30EditorProps } from "../components/admin/docx-nd30-editor";
import { UisAdmissionsExplorer } from "../components/admin/uis-admissions-explorer";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { type AdministrativeTemplate, type ToolItem, apiClient } from "../services/api-client";

type DocEditingData = NonNullable<DocxNd30EditorProps["initialData"]>;

export const ToolsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("docx_nd30");
  const [editingDocData, setEditingDocData] = useState<DocEditingData | undefined>(undefined);

  const { data: tools = [] } = useQuery({
    queryKey: ["tools"],
    queryFn: () => apiClient.getTools(),
  });

  const getToolIcon = (code: string) => {
    switch (code) {
      case "uis_admissions_query":
        return <GraduationCap className="h-4 w-4" />;
      case "docx_nd30_exporter":
        return <FileText className="h-4 w-4" />;
      case "xlsx_bloom_matrix_exporter":
        return <FileSpreadsheet className="h-4 w-4" />;
      default:
        return <Wrench className="h-4 w-4" />;
    }
  };

  // Nạp dữ liệu từ phôi mẫu vào form soạn thảo Word NĐ 30
  const handleSelectTemplateToEdit = (template: AdministrativeTemplate) => {
    setEditingDocData({
      documentType: template.document_type,
      subAgency: template.department,
      documentNumber: "Số: ... /QĐ-ĐHQN",
      cityDate: "Quy Nhơn, ngày ... tháng ... năm 2026",
      title: template.default_title,
      paragraphs: template.default_paragraphs,
      signerTitle: template.default_signer_title,
      signerName: template.default_signer_name,
      recipients: template.default_recipients,
    });
    setActiveTab("docx_nd30");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <span>Cổng Công Cụ Ngoại Vi & Xuất Bản Biểu Mẫu</span>
            <Badge variant="outline" className="font-mono text-xs text-primary">
              OpenAPI Gateway
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Studio xuất bản tài liệu chuẩn Nghị định 30/2020/NĐ-CP, Ma trận đề thi Bloom, Tra cứu
            UIS và Thư viện Phôi mẫu QNU.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-xs px-2.5 py-1">
            <span className="size-2 rounded-full bg-success inline-block mr-1.5" />
            3/3 Core Tools Sẵn Sàng
          </Badge>
        </div>
      </div>

      {/* 03 Standard Tools Quick Selector Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tools.map((tool: ToolItem) => {
          const isSelected =
            (tool.code === "docx_nd30_exporter" && activeTab === "docx_nd30") ||
            (tool.code === "xlsx_bloom_matrix_exporter" && activeTab === "bloom_matrix") ||
            (tool.code === "uis_admissions_query" && activeTab === "uis_query");

          return (
            <Card
              key={tool.id}
              onClick={() => {
                if (tool.code === "docx_nd30_exporter") setActiveTab("docx_nd30");
                else if (tool.code === "xlsx_bloom_matrix_exporter") setActiveTab("bloom_matrix");
                else if (tool.code === "uis_admissions_query") setActiveTab("uis_query");
              }}
              className={`p-4 space-y-3 cursor-pointer transition-all flex flex-col justify-between ${
                isSelected
                  ? "border-primary ring-2 ring-primary/20 bg-primary/5 shadow-xs"
                  : "hover:border-primary/40"
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-control bg-primary/10 text-primary">
                      {getToolIcon(tool.code)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-xs text-foreground">{tool.name}</h3>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {tool.code}
                      </span>
                    </div>
                  </div>
                  {tool.requires_approval ? (
                    <Badge variant="warning" className="text-[10px]">
                      Duyệt Cán Bộ
                    </Badge>
                  ) : (
                    <Badge variant="success" className="text-[10px]">
                      Tự Động
                    </Badge>
                  )}
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">{tool.description}</p>
              </div>

              <div className="border-t border-border/60 pt-2.5 flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="font-mono text-primary truncate max-w-[180px]">
                  {tool.endpoint}
                </span>
                <span className="font-mono font-bold text-foreground">
                  {(tool.usage_count ?? 142).toLocaleString("vi-VN")} lượt
                </span>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Main Studio Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <div className="border-b border-border pb-px">
          <TabsList className="h-9 p-1 gap-1">
            <TabsTrigger
              value="docx_nd30"
              className="text-xs gap-1.5 px-3 data-[state=active]:font-semibold"
            >
              <FileText className="size-3.5" />
              <span>Soạn Thảo Word NĐ 30</span>
            </TabsTrigger>

            <TabsTrigger
              value="bloom_matrix"
              className="text-xs gap-1.5 px-3 data-[state=active]:font-semibold"
            >
              <FileSpreadsheet className="size-3.5" />
              <span>Ma Trận Đề Thi Bloom</span>
            </TabsTrigger>

            <TabsTrigger
              value="uis_query"
              className="text-xs gap-1.5 px-3 data-[state=active]:font-semibold"
            >
              <GraduationCap className="size-3.5" />
              <span>Cổng Dữ Liệu UIS</span>
            </TabsTrigger>

            <TabsTrigger
              value="templates"
              className="text-xs gap-1.5 px-3 data-[state=active]:font-semibold"
            >
              <Layers className="size-3.5" />
              <span>Thư Viện Phôi Mẫu</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Soạn Thảo Word NĐ 30 */}
        <TabsContent value="docx_nd30" className="m-0 focus-visible:outline-none">
          <DocxNd30Editor initialData={editingDocData} />
        </TabsContent>

        {/* Tab 2: Ma Trận Đề Thi Bloom */}
        <TabsContent value="bloom_matrix" className="m-0 focus-visible:outline-none">
          <BloomMatrixEditor />
        </TabsContent>

        {/* Tab 3: Cổng Dữ Liệu UIS Tuyển Sinh */}
        <TabsContent value="uis_query" className="m-0 focus-visible:outline-none">
          <UisAdmissionsExplorer />
        </TabsContent>

        {/* Tab 4: Thư Viện Phôi Mẫu */}
        <TabsContent value="templates" className="m-0 focus-visible:outline-none">
          <AdministrativeTemplatesView onSelectTemplateToEdit={handleSelectTemplateToEdit} />
        </TabsContent>
      </Tabs>

      {/* Human-in-the-loop Governance Banner */}
      <Card className="p-4 bg-primary/5 border-primary/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-control bg-primary text-primary-foreground shrink-0">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <h4 className="font-semibold text-foreground">
              Chính Sách Kiểm Soát Cán Bộ Phê Duyệt (Human-in-the-loop)
            </h4>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Mọi văn bản hành chính xuất ra chuẩn Nghị định 30/2020/NĐ-CP hoặc ma trận đề thi khảo
              thí đều được gắn mã định danh xác thực và lưu trữ bảo mật trên hệ thống MinIO S3 của
              Trường Đại học Quy Nhơn.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
