import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { ToastProvider, ToastContainer } from '@/components/common';
import router from './router';

const App: React.FC = () => {
  return (
    <ToastProvider>
      <RouterProvider router={router} />
      <ToastContainer />
    </ToastProvider>
  );
};

export default App;
