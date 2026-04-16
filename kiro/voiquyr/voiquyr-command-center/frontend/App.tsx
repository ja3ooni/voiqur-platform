import React, { useState } from 'react';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { FlashSimulator } from './pages/FlashSimulator';
import { Config } from './pages/Config';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'simulator':
        return <FlashSimulator />;
      case 'trunks':
      case 'compliance':
      case 'deployment':
      case 'settings':
        return <Config activeTab={activeTab} />;
      default:
        return (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-2">
            <span className="text-2xl">🚧</span>
            <span className="text-sm">This section is not yet available.</span>
          </div>
        );
    }
  };

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab}>
      {renderContent()}
    </Layout>
  );
};

export default App;