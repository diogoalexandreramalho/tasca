import { AppRoutes } from '@/app/routes';
import { useAuth } from '@/features/auth/AuthContext';

export function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div>
            <span className="text-lg font-semibold tracking-tight">Tasca Tagarela</span>
            <span className="ml-2 text-sm text-stone-500">admin</span>
          </div>
          {isAuthenticated && (
            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100"
            >
              Log out
            </button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <AppRoutes />
      </main>
    </div>
  );
}
