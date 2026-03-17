import React from 'react';
import { Box } from '@mui/material';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <Box>
      {/* You can add a header or sidebar here */}
      <main>{children}</main>
    </Box>
  );
};

export default Layout;
