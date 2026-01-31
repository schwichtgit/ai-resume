import { createContext, useContext, ReactNode } from "react";
import { Profile, useProfile, UseProfileResult } from "@/hooks/useProfile";

interface ProfileContextValue extends UseProfileResult {}

const ProfileContext = createContext<ProfileContextValue | undefined>(undefined);

/**
 * Provider component that loads and provides profile data to the app.
 *
 * Usage:
 * ```tsx
 * <ProfileProvider>
 *   <App />
 * </ProfileProvider>
 * ```
 */
export function ProfileProvider({ children }: { children: ReactNode }) {
  const profileData = useProfile();

  return (
    <ProfileContext.Provider value={profileData}>
      {children}
    </ProfileContext.Provider>
  );
}

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
    throw new Error("useProfileContext must be used within a ProfileProvider");
  }

  return context;
}

// Export Profile type for convenience
export type { Profile };
