import { AppRoutes } from '@/app/routes';

export function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-4">
          <span className="text-lg font-semibold tracking-tight">Tasca Tagarela</span>
          <span className="ml-2 text-sm text-stone-500">admin</span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <AppRoutes />
      </main>
    </div>
  );
}
