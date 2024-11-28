import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import FortuneTellerUI from './components/FortuneTellerUI';
import ReconstructionUI from './components/ReconstructionUI';

const App = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">Fortune Teller Tool</h1>
        
        <Tabs defaultValue="process" className="w-full">
          <TabsList className="flex w-full max-w-md mx-auto mb-8">
            <TabsTrigger value="process" className="flex-1">
              Process Image
            </TabsTrigger>
            <TabsTrigger value="reconstruct" className="flex-1">
              Reconstruct
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="process">
            <FortuneTellerUI />
          </TabsContent>
          
          <TabsContent value="reconstruct">
            <ReconstructionUI />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default App;