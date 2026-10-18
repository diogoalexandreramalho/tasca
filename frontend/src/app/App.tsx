import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';

import { AppRoutes } from '@/app/routes';
import { useAuth } from '@/features/auth/AuthContext';

export function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-3 px-6 py-4">
          <Link to="/" className="mr-auto">
            <span className="text-lg font-semibold tracking-tight">Tasca Tagarela</span>
            <span className="ml-2 text-sm text-stone-500">admin</span>
          </Link>
          {isAuthenticated && (
            <>
              <SearchBox />
              <button
                type="button"
                onClick={logout}
                className="rounded-md border border-stone-300 px-3 py-1.5 text-sm hover:bg-stone-100"
              >
                Log out
              </button>
            </>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <AppRoutes />
      </main>
    </div>
  );
}

function SearchBox() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <form role="search" onSubmit={handleSubmit} className="order-last w-full sm:order-none sm:w-64">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search name or phone"
        aria-label="Search bookings by name or phone"
        className="w-full rounded-md border border-stone-300 px-3 py-1.5 text-sm"
      />
    </form>
  );
}
