import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type { PaymentConfiguration, PaymentConfigurationInput } from "./types";

const path = "/PaymentConfigurations";
export const paymentConfigurationsQueryKey = [
  "payment-configurations",
] as const;

export function usePaymentConfigurationsQuery() {
  return useQuery({
    queryKey: paymentConfigurationsQueryKey,
    queryFn: () => apiClient.get<PaymentConfiguration[]>(path),
  });
}

function toFormData(input: PaymentConfigurationInput) {
  const body = new FormData();
  body.append("Name", input.name);
  body.append("IsEnabled", String(input.isEnabled));
  body.append("QrMode", input.qrMode);
  body.append("BankCode", input.bankCode);
  body.append("AccountNumber", input.accountNumber);
  body.append("AccountName", input.accountName);
  body.append("ContentTemplate", input.contentTemplate);
  body.append("InstructionText", input.instructionText);
  if (input.qrImage) body.append("QrImage", input.qrImage);
  return body;
}

export function useSavePaymentConfiguration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id?: string;
      input: PaymentConfigurationInput;
    }) =>
      id
        ? apiClient.put<string>(`${path}/${id}`, toFormData(input))
        : apiClient.post<string>(path, toFormData(input)),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: paymentConfigurationsQueryKey,
      });
      void queryClient.invalidateQueries({
        queryKey: ["registration-periods"],
      });
    },
  });
}
