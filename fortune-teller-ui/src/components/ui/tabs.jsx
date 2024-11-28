// src/components/ui/tabs.jsx
import React, { createContext, useContext, useState } from 'react';

const TabsContext = createContext();

const Tabs = ({ defaultValue, children, className = '' }) => {
  const [activeTab, setActiveTab] = useState(defaultValue);
  
  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={className}>
        {children}
      </div>
    </TabsContext.Provider>
  );
};

const TabsList = ({ className = '', children }) => {
  return (
    <div className={`inline-flex bg-gray-100 p-1 rounded-lg ${className}`}>
      {children}
    </div>
  );
};

const TabsTrigger = ({ value, children, className = '' }) => {
  const { activeTab, setActiveTab } = useContext(TabsContext);
  const isActive = activeTab === value;
  
  return (
    <button
      onClick={() => setActiveTab(value)}
      className={`
        px-4 py-2 text-sm font-medium rounded-md transition-colors
        ${isActive 
          ? 'bg-white text-black shadow-sm' 
          : 'text-gray-600 hover:text-gray-900'
        }
        ${className}
      `}
    >
      {children}
    </button>
  );
};

const TabsContent = ({ value, children }) => {
  const { activeTab } = useContext(TabsContext);
  
  if (value !== activeTab) {
    return null;
  }
  
  return (
    <div className="mt-4">
      {children}
    </div>
  );
};

export { Tabs, TabsList, TabsTrigger, TabsContent };