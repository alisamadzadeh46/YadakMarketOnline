"use client";
// Global auth + cart-count context.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, clearSessionFlag, hasSession } from "./api";
import { guestCartCount, mergeGuestCart } from "./ui";
import { errorStatus } from "@/lib/api";

export type User = {
  id: number;
  phone: string;
  full_name: string;
  role: string;
  role_display: string;
  is_approved: boolean;
};

type Ctx = {
  user: User | null;
  loading: boolean;
  cartCount: number;
  refreshCart: () => void;
  login: (phone: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => void;
};

const AuthContext = createContext<Ctx>({} as Ctx);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [cartCount, setCartCount] = useState(0);

  const loadUser = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.get<User>("/accounts/me/"));
    } catch (err) {
      // Only a real rejection ends the session. Clearing on *any* failure meant
      // one flaky request (timeout, 5xx, dropped connection) silently signed
      // the user out and wiped their token — while requests already in flight
      // kept succeeding, so the header showed "sign in / register" on top of a page
      // full of their own data. Keep the token for anything that isn't 401/403.
      if (errorStatus(err) === 401 || errorStatus(err) === 403) {
        clearSessionFlag();
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshCart = useCallback(async () => {
    // Signed out, the badge still reflects what's parked locally so the
    // shopper can see their picks weren't thrown away.
    if (!hasSession()) return setCartCount(guestCartCount());
    try {
      const cart = await api.get("/orders/cart/");
      setCartCount(
        (cart.items || []).reduce((n: number, i: any) => n + i.quantity, 0)
      );
    } catch {
      setCartCount(0);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);
  useEffect(() => {
    if (!user) { refreshCart(); return; }
    // A signed-in user may still have guest lines parked from before they
    // logged in (or from a session that expired) — adopt them, then refresh.
    mergeGuestCart().finally(refreshCart);
  }, [user, refreshCart]);
  // Keep the header badge honest while signed out too.
  useEffect(() => {
    const onChange = () => { if (!hasSession()) setCartCount(guestCartCount()); };
    window.addEventListener("ym-cart-changed", onChange);
    return () => window.removeEventListener("ym-cart-changed", onChange);
  }, []);

  const login = async (phone: string, password: string) => {
    // The response carries the user and a CSRF token; the JWT itself arrives
    // as HttpOnly cookies we never see. Nothing to store here any more.
    await api.post("/accounts/token/", { phone, password }, { auth: false });
    // Adopt anything added while signed out BEFORE the count is read.
    await mergeGuestCart();
    await loadUser();
    await refreshCart();
  };

  const logout = async () => {
    // Only the server can drop an HttpOnly cookie, and only it can blacklist
    // the refresh token — so signing out is a request, not a local erase.
    try {
      await api.post("/accounts/logout/", undefined, { auth: false });
    } catch {
      // Network trouble should not strand the user in a signed-in-looking UI.
    }
    clearSessionFlag();
    setUser(null);
    setCartCount(0);
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, cartCount, refreshCart, login, logout, reload: loadUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}
