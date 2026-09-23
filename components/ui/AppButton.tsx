import type { ComponentProps } from 'react';
import { Button, Spinner } from 'heroui-native';

type AppButtonProps = ComponentProps<typeof Button> & {
  label: string;
  isLoading?: boolean;
};

export function AppButton({ label, isLoading = false, isDisabled, ...props }: AppButtonProps) {
  return (
    <Button isDisabled={isDisabled || isLoading} {...props}>
      {isLoading ? <Spinner size="sm" /> : null}
      <Button.Label>{label}</Button.Label>
    </Button>
  );
}
