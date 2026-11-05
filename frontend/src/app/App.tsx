import { useState, type FormEvent } from 'react';
import { Link, NavLink, useNavigate } from 'react-router';

import { AppRoutes } from '@/app/routes';
import { useAuth } from '@/features/auth/AuthContext';

export function App() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-2 gap-y-3 px-4 py-4 sm:gap-x-4 sm:px-6">
          <Link to="/" className="mr-auto">
            <span className="text-lg font-semibold tracking-tight">Tasca Tagarela</span>
            <span className="ml-2 hidden text-sm text-stone-500 sm:inline">admin</span>
          </Link>
          {isAuthenticated && (
            <>
              <nav aria-label="Main" className="flex gap-1 text-sm">
                {[
                  { to: '/', label: 'Bookings' },
                  { to: '/calls', label: 'Calls' },
                ].map(({ to, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end
                    className={({ isActive }) =>
                      `rounded-md px-2.5 py-1.5 sm:px-3 ${isActive ? 'bg-stone-900 text-white' : 'hover:bg-stone-100'}`
                    }
                  >
                    {label}
                  </NavLink>
                ))}
              </nav>
              <SearchBox />
              <button
                type="button"
                onClick={logout}
                className="rounded-md border border-stone-300 px-2.5 py-1.5 text-sm hover:bg-stone-100 sm:px-3"
              >
                Log out
              </button>
            </>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
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
