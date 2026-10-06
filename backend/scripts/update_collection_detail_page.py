file_path = r'd:\DuAnPhanMem\qnu-ai-platform\frontend\src\pages\collection-detail-page.tsx'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Import
text = text.replace(
    'import type {\n  IngestionTask,\n  KnowledgeDocument,\n  SandboxSearchResult,\n} from "../components/knowledge/types";',
    'import type {\n  IngestionTask,\n  KnowledgeDocument,\n  SandboxSearchResult,\n} from "../components/knowledge/types";\nimport type { CollectionDataProcessingConfig } from "@/types/knowledge";'
).replace(
    'import type {\r\n  IngestionTask,\r\n  KnowledgeDocument,\r\n  SandboxSearchResult,\r\n} from "../components/knowledge/types";',
    'import type {\r\n  IngestionTask,\r\n  KnowledgeDocument,\r\n  SandboxSearchResult,\r\n} from "../components/knowledge/types";\r\nimport type { CollectionDataProcessingConfig } from "@/types/knowledge";'
)

# 2. State
text = text.replace(
    '  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);',
    '  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);\n  const [configDataProcessing, setConfigDataProcessing] = useState<CollectionDataProcessingConfig>({});'
).replace(
    '  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);\r\n',
    '  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);\r\n  const [configDataProcessing, setConfigDataProcessing] = useState<CollectionDataProcessingConfig>({});\r\n'
)

# 3. openConfigDialog
text = text.replace(
    '  const openConfigDialog = () => {\n    setConfigName(currentCollection.name);\n    setConfigDescription(currentCollection.description || "");\n    setIsConfigOpen(true);\n  };',
    '  const openConfigDialog = () => {\n    setConfigName(currentCollection.name);\n    setConfigDescription(currentCollection.description || "");\n    setConfigDataProcessing(\n      currentCollection.data_processing || {\n        embedding_model: "bge-m3:latest",\n        embedding_provider_id: "prov_rtx5090_ollama",\n        embedding_dimension: 1024,\n        ocr_mode: "combo",\n        primary_ocr_model: "qwen3-vl:8b",\n        primary_ocr_provider_id: "prov_rtx5090_ollama",\n        fallback_ocr_model: "gemini-3.1-flash-lite",\n        fallback_ocr_provider_id: "prov_gemini",\n        enable_ocr_rescue: true,\n      }\n    );\n    setIsConfigOpen(true);\n  };'
).replace(
    '  const openConfigDialog = () => {\r\n    setConfigName(currentCollection.name);\r\n    setConfigDescription(currentCollection.description || "");\r\n    setIsConfigOpen(true);\r\n  };',
    '  const openConfigDialog = () => {\r\n    setConfigName(currentCollection.name);\r\n    setConfigDescription(currentCollection.description || "");\r\n    setConfigDataProcessing(\r\n      currentCollection.data_processing || {\r\n        embedding_model: "bge-m3:latest",\r\n        embedding_provider_id: "prov_rtx5090_ollama",\r\n        embedding_dimension: 1024,\r\n        ocr_mode: "combo",\r\n        primary_ocr_model: "qwen3-vl:8b",\r\n        primary_ocr_provider_id: "prov_rtx5090_ollama",\r\n        fallback_ocr_model: "gemini-3.1-flash-lite",\r\n        fallback_ocr_provider_id: "prov_gemini",\r\n        enable_ocr_rescue: true,\r\n      }\r\n    );\r\n    setIsConfigOpen(true);\r\n  };'
)

# 4. handleSaveConfig
text = text.replace(
    '      await apiClient.updateCollection(currentCollection.id, {\n        name: configName.trim(),\n        description: configDescription.trim(),\n      });',
    '      await apiClient.updateCollection(currentCollection.id, {\n        name: configName.trim(),\n        description: configDescription.trim(),\n        data_processing: configDataProcessing,\n      });'
).replace(
    '      await apiClient.updateCollection(currentCollection.id, {\r\n        name: configName.trim(),\r\n        description: configDescription.trim(),\r\n      });',
    '      await apiClient.updateCollection(currentCollection.id, {\r\n        name: configName.trim(),\r\n        description: configDescription.trim(),\r\n        data_processing: configDataProcessing,\r\n      });'
)

# 5. JSX
text = text.replace(
    '      {/* DIALOG 3: Collection Config */}\n      <CollectionConfigDialog\n        open={isConfigOpen}\n        onOpenChange={setIsConfigOpen}\n        configName={configName}\n        setConfigName={setConfigName}\n        configDescription={configDescription}\n        setConfigDescription={setConfigDescription}\n        isSaving={isSavingConfig}\n        onSave={handleSaveConfig}\n      />',
    '      {/* DIALOG 3: Collection Config */}\n      <CollectionConfigDialog\n        open={isConfigOpen}\n        onOpenChange={setIsConfigOpen}\n        configName={configName}\n        setConfigName={setConfigName}\n        configDescription={configDescription}\n        setConfigDescription={setConfigDescription}\n        documentCount={currentCollection.document_count}\n        dataProcessingConfig={configDataProcessing}\n        setDataProcessingConfig={setConfigDataProcessing}\n        isSaving={isSavingConfig}\n        onSave={handleSaveConfig}\n      />'
).replace(
    '      {/* DIALOG 3: Collection Config */}\r\n      <CollectionConfigDialog\r\n        open={isConfigOpen}\r\n        onOpenChange={setIsConfigOpen}\r\n        configName={configName}\r\n        setConfigName={setConfigName}\r\n        configDescription={configDescription}\r\n        setConfigDescription={setConfigDescription}\r\n        isSaving={isSavingConfig}\r\n        onSave={handleSaveConfig}\r\n      />',
    '      {/* DIALOG 3: Collection Config */}\r\n      <CollectionConfigDialog\r\n        open={isConfigOpen}\r\n        onOpenChange={setIsConfigOpen}\r\n        configName={configName}\r\n        setConfigName={setConfigName}\r\n        configDescription={configDescription}\r\n        setConfigDescription={setConfigDescription}\r\n        documentCount={currentCollection.document_count}\r\n        dataProcessingConfig={configDataProcessing}\r\n        setDataProcessingConfig={setConfigDataProcessing}\r\n        isSaving={isSavingConfig}\r\n        onSave={handleSaveConfig}\r\n      />'
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("collection-detail-page.tsx updated successfully.")
