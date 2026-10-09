import { useHealth } from '@/features/home/useHealth';

export function HomePage() {
  const { isPending, isError } = useHealth();

  const status = isPending
    ? { label: 'Checking API…', dot: 'bg-stone-400' }
    : isError
      ? { label: 'API unreachable', dot: 'bg-red-500' }
      : { label: 'API online', dot: 'bg-emerald-500' };

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <p className="mt-1 text-sm text-stone-600">
        Reservations, callbacks and call logs will live here.
      </p>
      <p className="mt-4 inline-flex items-center gap-2 text-sm" role="status">
        <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden />
        {status.label}
      </p>
    </section>
  );
}
