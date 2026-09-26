import type { ComponentProps } from 'react';
import { TextInput } from 'react-native';
import { FieldError, Label, TextField } from 'heroui-native';
import { cn } from '@/lib/utils';

type AppTextFieldProps = ComponentProps<typeof TextInput> & {
  label: string;
  error?: string;
  isRequired?: boolean;
};

export function AppTextField({
  label,
  error,
  isRequired,
  className,
  ...inputProps
}: AppTextFieldProps) {
  return (
    <TextField isInvalid={Boolean(error)} isRequired={isRequired}>
      <Label>{label}</Label>
      <TextInput
        {...inputProps}
        aria-invalid={Boolean(error)}
        className={cn(
          'bg-default text-foreground h-12 w-full rounded-xl border px-4 text-base outline-none',
          error ? 'border-danger' : 'border-border focus:border-accent',
          className,
        )}
      />
      {error ? <FieldError>{error}</FieldError> : null}
    </TextField>
  );
}
