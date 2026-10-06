export type DifficultAreaItem = {
  id: string;
  externalCode: string;
  name: string;
  divisionType: string;
  codename?: string | null;
  provinceCode?: string | null;
  provinceName?: string | null;
  specificVillages?: string | null;
  isWholeArea: boolean;
  source: string;
  datasetVersion: string;
};

export type DifficultAreasPage = {
  items: DifficultAreaItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

export type DifficultAreasListParams = {
  search?: string;
  provinceName?: string;
  provinceCode?: string;
  divisionType?: string;
  isWholeArea?: boolean;
  page: number;
  pageSize: number;
};

export type DifficultAreasStats = {
  total: number;
  totalProvinces: number;
  wholeAreaCount: number;
  partialAreaCount: number;
};

export type CreateDifficultAreaInput = {
  externalCode?: string;
  name: string;
  divisionType?: string;
  provinceCode?: string;
  provinceName: string;
  specificVillages?: string;
  isWholeArea: boolean;
};

export type UpdateDifficultAreaInput = {
  externalCode?: string;
  name: string;
  divisionType?: string;
  provinceCode?: string;
  provinceName: string;
  specificVillages?: string;
  isWholeArea: boolean;
  isActive?: boolean;
};
