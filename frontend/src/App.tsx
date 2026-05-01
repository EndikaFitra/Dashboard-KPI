import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

import { DashboardLayout } from "@/components/DashboardLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";

import LoginPage from "@/pages/LoginPage";
import DivisionDashboard from "@/pages/DivisionDashboard";
import ChatPage from "@/pages/ChatPage";
import NotFound from "@/pages/NotFound";

import AdminLayout from "@/pages/admin/AdminLayout";
import InsertKpiForm from "@/pages/admin/InsertKpiForm";
import InsertRealizationForm from "@/pages/admin/InsertRealizationForm";
import UserManagement from "@/pages/admin/UserManagement";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />

          {/* Dashboard (protected — any role) */}
          <Route
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Navigate to="/network" replace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/:divisionId" element={<DivisionDashboard />} />
          </Route>

          {/* Admin panel (protected — admin only) */}
          <Route
            element={
              <ProtectedRoute adminOnly>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/admin" element={<Navigate to="/admin/kpi" replace />} />
            <Route path="/admin/kpi" element={<InsertKpiForm />} />
            <Route path="/admin/realization" element={<InsertRealizationForm />} />
            <Route path="/admin/users" element={<UserManagement />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
