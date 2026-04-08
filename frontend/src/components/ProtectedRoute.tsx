import { Navigate, Outlet, useLocation } from "react-router-dom";
import { isAuthenticated, isAdmin } from "@/lib/auth";

interface Props {
  children?: React.ReactNode;
  adminOnly?: boolean;
}

/**
 * Wraps a route and redirects:
 * - unauthenticated users → /login
 * - non-admin users trying to access admin routes → /
 *
 * Works both as a wrapper (children) and as a layout route (Outlet).
 */
export function ProtectedRoute({ children, adminOnly = false }: Props) {
  const location = useLocation();

  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && !isAdmin()) {
    return <Navigate to="/" replace />;
  }

  // If used as a layout route (no children), render Outlet
  return <>{children ?? <Outlet />}</>;
}
