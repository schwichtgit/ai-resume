import { createContext } from 'react';
import type { UseProfileResult } from '@/hooks/useProfile';

export type ProfileContextValue = UseProfileResult;

export const ProfileContext = createContext<ProfileContextValue | undefined>(
  undefined,
);
