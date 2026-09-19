import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChannelsPage } from "@/pages/channels-page";
import { DeveloperPage } from "@/pages/developer-page";
import { Code2, Share2, Sparkles } from "lucide-react";
import * as React from "react";

interface SettingsIntegrationsPageProps {
  initialTab?: string;
  onTabChange?: (tab: string) => void;
}

export const SettingsIntegrationsPage: React.FC<SettingsIntegrationsPageProps> = ({
  initialTab = "channels",
  onTabChange,
}) => {
  const [activeTab, setActiveTab] = React.useState<string>(initialTab);

  React.useEffect(() => {
    if (initialTab && initialTab !== activeTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab, activeTab]);

  const handleValueChange = (val: string) => {
    setActiveTab(val);
    onTabChange?.(val);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="size-4 text-primary" />
            <span>Hệ Thống / Cài Đặt & Tích Hợp</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground mt-1">
            Tích Hợp & Kênh Triển Khai
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Quản lý mã nhúng Web Chat Widget, CDN Script và Khóa API cho các phòng ban, cổng thông
            tin trường.
          </p>
        </div>
      </div>

      {/* Main Tabs Container */}
      <Tabs value={activeTab} onValueChange={handleValueChange} className="space-y-6">
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="channels" className="gap-2 text-xs">
            <Share2 className="size-3.5" />
            <span>Kênh & Web Widget</span>
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="gap-2 text-xs">
            <Code2 className="size-3.5" />
            <span>Khóa API & Webhooks</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="channels" className="mt-0 focus-visible:outline-none">
          <ChannelsPage />
        </TabsContent>

        <TabsContent value="api-keys" className="mt-0 focus-visible:outline-none">
          <DeveloperPage />
        </TabsContent>
      </Tabs>
    </div>
  );
};
