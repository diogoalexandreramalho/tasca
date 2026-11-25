import { useEffect, useState, type FormEvent } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router';

import { AppRoutes } from '@/app/routes';
import { AzulejoStrip } from '@/components/AzulejoStrip';
import { useAuth } from '@/features/auth/AuthContext';

export function App() {
  const { isAuthenticated, isGuest, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-2 gap-y-3 px-4 py-4 sm:gap-x-4 sm:px-6">
          <Link to="/" className="mr-auto">
            <span className="font-display text-lg whitespace-nowrap text-azulejo-800 sm:text-xl">
              Tasca Tagarela
            </span>
            {isGuest ? (
              <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                Guest · read-only
              </span>
            ) : (
              <span className="ml-2 hidden text-sm text-azulejo-600 sm:inline">admin</span>
            )}
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
                      `inline-flex h-11 items-center rounded-md px-2 sm:h-auto sm:px-3 sm:py-1.5 ${isActive ? 'bg-azulejo-50 font-medium text-azulejo-800' : 'text-stone-700 hover:bg-stone-100'}`
                    }
                  >
                    {label}
                  </NavLink>
                ))}
              </nav>
              <SearchBox byNameOnly={isGuest} />
              <button
                type="button"
                onClick={logout}
                className="h-11 rounded-md border border-stone-300 bg-white px-2 text-sm hover:bg-stone-100 sm:h-auto sm:px-3 sm:py-1.5"
              >
                {isGuest ? 'Leave demo' : 'Log out'}
              </button>
            </>
          )}
        </div>
      </header>
      <AzulejoStrip />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <AppRoutes />
      </main>
    </div>
  );
}

function SearchBox({ byNameOnly }: { byNameOnly: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  // On the search page, show what was searched so it can be changed; elsewhere, empty.
  const searched =
    location.pathname === '/search' ? (new URLSearchParams(location.search).get('q') ?? '') : '';
  const [query, setQuery] = useState(searched);
  useEffect(() => setQuery(searched), [searched]);

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
        placeholder={byNameOnly ? 'Search by name' : 'Search name or phone'}
        aria-label={byNameOnly ? 'Search bookings by name' : 'Search bookings by name or phone'}
        className="h-11 w-full rounded-md border border-stone-300 px-3 text-sm sm:h-auto sm:py-1.5"
      />
    </form>
  );
}
