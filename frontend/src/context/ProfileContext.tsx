import { ReactNode } from "react";
import { useProfile } from "@/hooks/useProfile";
import { ProfileContext } from "@/context/profileContextValue";

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
