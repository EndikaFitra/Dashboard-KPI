import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { postLogin } from "@/api/client";
import { setAuth, isAuthenticated, getRole } from "@/lib/auth";
import { BarChart3, Eye, EyeOff, Loader2, ShieldCheck, HeartPulse } from "lucide-react";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from?.pathname || "/";

  // Redirect if already logged in
  if (isAuthenticated()) {
    const role = getRole();
    navigate(role === "admin" ? "/admin" : from, { replace: true });
  }

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Username dan password wajib diisi");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await postLogin({ username, password });
      setAuth(data.access_token, data.role, data.username);
      navigate(data.role === "admin" ? "/admin" : from, { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Login gagal. Periksa username dan password.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Left/Hero Panel - Hidden on mobile */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-primary items-center justify-center overflow-hidden">
        {/* Background Overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/90 to-[#107049] mix-blend-multiply z-10" />
        <div
          className="absolute inset-0 opacity-30 z-0 bg-cover bg-center"
          style={{ backgroundImage: 'url("https://images.unsplash.com/photo-1599658880436-c61792e70672?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D")' }}
        />

        {/* Decorative blur elements */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white/10 rounded-full blur-3xl z-0" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#0c593a]/30 rounded-full blur-3xl z-0" />
      </div>

      {/* Right/Form Panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-white shadow-[-10px_0_30px_rgba(0,0,0,0.02)] z-10">
        <div className="w-full max-w-md">
          {/* Logo Section */}
          <div className="flex flex-col items-center mb-10 lg:items-start lg:mb-12">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-md shadow-primary/20">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">KPI Analytics</h2>
            </div>
            <p className="text-slate-500 text-sm">Masuk ke akun Anda untuk melanjutkan</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Username
              </label>
              <input
                id="login-username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Masukkan username"
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition text-sm"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPw ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Masukkan password"
                  className="w-full px-4 py-3 pr-11 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition p-1"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-red-600 text-sm flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 px-4 bg-primary hover:bg-primary/90 disabled:opacity-70 disabled:cursor-not-allowed text-white font-semibold rounded-xl shadow-md shadow-primary/20 transition-all duration-200 flex items-center justify-center gap-2 text-sm"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Sedang Masuk...</>
              ) : (
                <><ShieldCheck className="w-5 h-5" /> Masuk Sekarang</>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-12 pt-6 border-t border-slate-100 flex flex-col items-center">
            <p className="text-center text-slate-400 text-xs">
              &copy; {new Date().getFullYear()}. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
