import { Navigate, Route, Routes } from 'react-router';

import { HomePage } from '@/features/home/HomePage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
