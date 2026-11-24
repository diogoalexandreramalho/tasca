import { lazy, Suspense } from 'react';

import tascaInterior from '@/assets/tasca-interior.webp';
import { TalkButton } from '@/features/call/TalkButton';

// The voice SDK is most of the JavaScript: show the page first, load it after.
const CallSection = lazy(() => import('@/features/call/CallSection'));

/** The restaurant's one-page website. Customers book by talking to the voice agent. */
export function App() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-4 sm:px-6">
        <p className="flex items-baseline gap-2.5">
          <span className="font-display text-2xl text-azulejo-800">Tasca Tagarela</span>
          <span className="text-sm text-azulejo-600">Lisboa</span>
        </p>
        <span className="rounded-full bg-terracotta-50 px-3 py-1 text-xs text-terracotta-800">
          Demo project · fictional restaurant
        </span>
      </header>

      <AzulejoStrip />

      <main className="mx-auto grid w-full max-w-5xl flex-1 items-center gap-8 px-4 py-10 sm:px-6 md:grid-cols-2 md:gap-12 md:py-16">
        <section aria-labelledby="hero-title">
          <h1
            id="hero-title"
            className="mb-4 font-display text-4xl leading-tight text-azulejo-800 sm:text-5xl"
          >
            Petiscos, vinho and a good conversation.
          </h1>
          <p className="mb-8 max-w-md text-base leading-relaxed">
            Book your table by talking to us. Our assistant picks up straight away, any time of day.
          </p>
          <Suspense fallback={<TalkButton onClick={() => {}} />}>
            <CallSection />
          </Suspense>
        </section>

        <img
          src={tascaInterior}
          alt="Inside a traditional tasca: blue and white tiles, wooden tables, red wine and petiscos under warm lamps."
          width={1200}
          height={900}
          className="w-full rounded-2xl border border-azulejo-100 object-cover"
        />
      </main>

      <footer className="bg-azulejo-600 text-sm text-azulejo-50">
        <div className="mx-auto grid max-w-5xl gap-6 px-4 py-8 sm:grid-cols-2 sm:px-6">
          <div>
            <h2 className="mb-1 font-medium text-white">Opening hours</h2>
            <p>Tuesday to Sunday · closed on Mondays</p>
            <p>Lunch 12:00 · 13:30</p>
            <p>Dinner 19:00 · 20:30</p>
          </div>
          <div>
            <h2 className="mb-1 font-medium text-white">Bookings</h2>
            <p>Parties of 1 to 8</p>
            <p>From 1 hour to 60 days ahead</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

/** A band of blue tiles under the header. */
function AzulejoStrip() {
  return (
    <svg aria-hidden className="block h-6 w-full">
      <defs>
        <pattern id="azulejo" width="24" height="24" patternUnits="userSpaceOnUse">
          <rect width="24" height="24" fill="#e6f1fb" />
          <path d="M12 2 L22 12 L12 22 L2 12 Z" fill="none" stroke="#185fa5" strokeWidth="1.3" />
          <circle cx="12" cy="12" r="2.8" fill="#185fa5" />
          {[0, 24].map((x) =>
            [0, 24].map((y) => <circle key={`${x}-${y}`} cx={x} cy={y} r="3.2" fill="#378add" />),
          )}
        </pattern>
      </defs>
      <rect width="100%" height="24" fill="url(#azulejo)" />
    </svg>
  );
}
