import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import SecurityPanel from './SecurityPanel';
import { mockSystemStatus, mockPolicy } from '@/services/mockData';
import type { RiskLevel } from '@/types';

interface Props {
  riskLevel?: RiskLevel;
}

export default function MainLayout({ riskLevel = 'low' }: Props) {
  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <Sidebar status={mockSystemStatus} />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <SecurityPanel policy={mockPolicy} riskLevel={riskLevel} />
    </div>
  );
}
