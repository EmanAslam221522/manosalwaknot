import { create } from 'zustand';
import type { UserRole } from '@/types/domain';

export type ExperienceRole = 'RECIPIENT' | 'FOOD_PROVIDER' | 'VOLUNTEER';

type ExperienceState = {
  selectedRole: ExperienceRole | null;
  selectRole: (role: ExperienceRole) => void;
};

export const useExperienceStore = create<ExperienceState>((set) => ({
  selectedRole: null,
  selectRole: (selectedRole) => set({ selectedRole }),
}));

export function getAvailableExperiences(roles: UserRole[]): ExperienceRole[] {
  const experiences: ExperienceRole[] = [];
  if (roles.includes('RECIPIENT') || roles.includes('ORGANIZATION')) experiences.push('RECIPIENT');
  if (roles.includes('FOOD_PROVIDER')) experiences.push('FOOD_PROVIDER');
  if (roles.includes('VOLUNTEER')) experiences.push('VOLUNTEER');
  return experiences.length > 0 ? experiences : ['RECIPIENT'];
}

export function getActiveExperience(
  roles: UserRole[],
  selectedRole: ExperienceRole | null,
): ExperienceRole {
  const available = getAvailableExperiences(roles);
  return selectedRole && available.includes(selectedRole) ? selectedRole : available[0];
}
