export type PaymentConfiguration = {
  id: string;
  name: string;
  isEnabled: boolean;
  qrMode: "dynamic" | "uploaded" | string;
  hasQrImage: boolean;
  qrImageUrl?: string | null;
  bankCode: string;
  accountNumber: string;
  accountName: string;
  contentTemplate: string;
  instructionText: string;
};

export type PaymentConfigurationInput = Omit<
  PaymentConfiguration,
  "id" | "hasQrImage" | "qrImageUrl"
> & { qrImage?: File };
