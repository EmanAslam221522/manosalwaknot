import type { ComponentProps } from 'react';
import { FieldError, Input, Label, TextField } from 'heroui-native';

type AppTextFieldProps = ComponentProps<typeof Input> & {
  label: string;
  error?: string;
  isRequired?: boolean;
};

export function AppTextField({ label, error, isRequired, ...inputProps }: AppTextFieldProps) {
  return (
    <TextField isInvalid={Boolean(error)} isRequired={isRequired}>
      <Label>{label}</Label>
      <Input {...inputProps} />
      {error ? <FieldError>{error}</FieldError> : null}
    </TextField>
  );
}
