import React from 'react';
import { AppBar, Box, Button, Toolbar, Typography } from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '../../store/store';
import { logout } from '../../store/slices/authSlice';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const dispatch = useDispatch<AppDispatch>();
  const username = useSelector((s: RootState) => s.auth.username);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: '#0f172a' }}>
      <AppBar position="static" sx={{ bgcolor: '#1e293b', boxShadow: 'none', borderBottom: '1px solid #334155' }}>
        <Toolbar>
          <Typography variant="h6" fontWeight={700} sx={{ flexGrow: 1, color: 'white' }}>
            EUVoice AI
          </Typography>
          {username && (
            <Typography variant="body2" sx={{ color: '#94a3b8', mr: 2 }}>
              {username}
            </Typography>
          )}
          <Button variant="outlined" size="small" onClick={() => dispatch(logout())}
            sx={{ color: '#94a3b8', borderColor: '#334155' }}>
            Sign out
          </Button>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ flexGrow: 1 }}>
        {children}
      </Box>
    </Box>
  );
};

export default Layout;
