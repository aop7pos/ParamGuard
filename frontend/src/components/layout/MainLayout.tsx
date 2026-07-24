import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import SecurityPanel from './SecurityPanel';
import { fetchSystemStatus, fetchPolicies } from '@/services/dataService';
import { mockSystemStatus, mockPolicy } from '@/services/mockData';
import type { SystemStatus, SecurityPolicy, RiskLevel } from '@/types';

interface Props {
  riskLevel?: RiskLevel;
}

export default function MainLayout({ riskLevel = 'low' }: Props) {
  const [status, setStatus] = useState<SystemStatus>(mockSystemStatus);
  const [policy, setPolicy] = useState<SecurityPolicy>(mockPolicy);

  useEffect(() => {
    fetchSystemStatus().then(setStatus).catch(() => {});
    fetchPolicies().then(setPolicy).catch(() => {});
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <Sidebar status={status} />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <SecurityPanel policy={policy} riskLevel={riskLevel} />
    </div>
  );
}
