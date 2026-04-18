import { useContext } from 'react';
import {
  ProfileContext,
  ProfileContextValue,
} from '@/context/profileContextValue';

/**
 * Hook to access profile data from context.
 *
 * Must be used within a ProfileProvider.
 *
 * @returns Profile data, loading state, and error state
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { profile, isLoading, error } = useProfileContext();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *   if (!profile) return null;
 *
 *   return <div>Hello, {profile.name}</div>;
 * }
 * ```
 */
export function useProfileContext(): ProfileContextValue {
  const context = useContext(ProfileContext);

  if (context === undefined) {
    throw new Error('useProfileContext must be used within a ProfileProvider');
  }

  return context;
}
