import {
  createContext,
  PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { clearAuthTokens, getAccessToken, saveAccessToken } from "../../shared/lib/token";

type AuthUser = {
  id: number;
  nickname: string;
  email: string;
};

type AuthContextValue = {
  isAuthenticated: boolean;
  user: AuthUser | null;
  signInDemo: () => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      setIsAuthenticated(true);
      setUser({
        id: 1,
        nickname: "고니",
        email: "gonny@example.com",
      });
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      user,
      signInDemo: () => {
        saveAccessToken("demo-access-token");
        setUser({
          id: 1,
          nickname: "고니",
          email: "gonny@example.com",
        });
        setIsAuthenticated(true);
      },
      signOut: () => {
        clearAuthTokens();
        setUser(null);
        setIsAuthenticated(false);
      },
    }),
    [isAuthenticated, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
