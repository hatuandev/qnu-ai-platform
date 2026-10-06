import re

file_path = r'd:\DuAnPhanMem\qnu-ai-platform\frontend2\src\features\modelops\modelops-page.tsx'

with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Clean imports
text = re.sub(r'[ \t]*Layers,\r?\n', '', text)
text = re.sub(r'[ \t]*Sparkles,\r?\n', '', text)
text = re.sub(r'import\s+\{\s*CombosVisionSection\s*\}\s+from\s+"@/components/modelops/combos-vision-section";\r?\n', '', text)
text = re.sub(r'import\s+\{\s*SystemDefaultsCard\s*\}\s+from\s+"@/components/modelops/system-defaults-card";\r?\n', '', text)
text = re.sub(r'[ \t]*type\s+SystemModelDefaults,\r?\n', '', text)

# 2. Remove mainViewMode state and handler
state_block = re.compile(
    r'[ \t]*// Master View Main Tab \(Providers as DEFAULT!\)\r?\n'
    r'[ \t]*const \[mainViewMode, setMainViewMode\] = useState<[\s\S]*?>\("providers"\);\r?\n'
    r'[ \t]*const \[combosTaskFilter, setCombosTaskFilter\] = useState<string>\("all"\);\r?\n\r?\n'
    r'[ \t]*const handleNavigateToCombos = \([\s\S]*?^  \};\r?\n',
    re.MULTILINE
)
text = state_block.sub('', text)

# 3. Remove defaultsQuery, mutations, allAvailableModels
queries_block = re.compile(
    r'[ \t]*const defaultsQuery = useQuery\(\{[\s\S]*?\}\);\r?\n'
    r'[ \t]*const systemDefaults = defaultsQuery\.data\?\.defaults;\r?\n'
    r'[ \t]*const availableEmbeddings = defaultsQuery\.data\?\.available_embeddings \|\| \[\];\r?\n'
    r'[ \t]*const availableRerankers = defaultsQuery\.data\?\.available_rerankers \|\| \[\];\r?\n'
    r'[ \t]*const availableOcrs = defaultsQuery\.data\?\.available_ocrs \|\| \[\];\r?\n\r?\n'
    r'[ \t]*const allAvailableModels = useMemo\(\(\) => \{[\s\S]*?\}, \[providers\]\);\r?\n\r?\n'
    r'[ \t]*const updateDefaultsMutation = useMutation\(\{[\s\S]*?\}\);\r?\n\r?\n'
    r'[ \t]*const setDefaultMutation = useMutation\(\{[\s\S]*?\}\);\r?\n',
    re.MULTILINE
)
text = queries_block.sub('', text)

# 4. Remove setDefaultMutation call inside handleConfirmAddCustomModel
set_default_call = re.compile(
    r'[ \t]*if \(defaultRole !== "none"\) \{[\s\S]*?setDefaultMutation\.mutate\(\{[\s\S]*?\}\);\r?\n[ \t]*\}\r?\n'
)
text = set_default_call.sub('', text)
text = text.replace('defaultRole: "none" | "embedding" | "reranker" | "ocr",', '_defaultRole: "none" | "embedding" | "reranker" | "ocr",')

# 5. Remove systemDefaults passed to ModelsGrid
text = text.replace('          systemDefaults={systemDefaults}\n', '').replace('          systemDefaults={systemDefaults}\r\n', '')

# 6. Remove navigation tab switcher and unwrap mainViewMode === "providers"
tab_switcher = re.compile(
    r'[ \t]*\{/\* Main Navigation Tabs \*/\}[\s\S]*?'
    r'\{/\* Main View Content \*/\}\r?\n'
    r'[ \t]*\{mainViewMode === "providers" && \(\r?\n',
    re.MULTILINE
)
text = tab_switcher.sub('{/* Provider Grid & Content */}\n', text)

# 7. Remove defaults and combos panels and the closing of mainViewMode === "providers"
panels_block = re.compile(
    r'[ \t]*\)\}\r?\n\r?\n'
    r'[ \t]*\{mainViewMode === "defaults" && \([\s\S]*?\)\}\r?\n\r?\n'
    r'[ \t]*\{mainViewMode === "combos" && \([\s\S]*?\)\}\r?\n',
    re.MULTILINE
)
text = panels_block.sub('', text)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("frontend2 modelops-page.tsx refactored successfully.")
