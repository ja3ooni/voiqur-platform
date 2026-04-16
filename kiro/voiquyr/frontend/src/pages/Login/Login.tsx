import React, { useState, useEffect } from 'react';
import {
  Box, Button, TextField, Typography, Paper,
  Alert, Tabs, Tab, CircularProgress,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { AppDispatch, RootState } from '../../store/store';
import { login, register, clearError } from '../../store/slices/authSlice';

const Login = () => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();
  const { isAuthenticated, loading, error } = useSelector((s: RootState) => s.auth);

  const [tab, setTab] = useState(0);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (isAuthenticated) navigate('/');
  }, [isAuthenticated, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(login({ username, password }));
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await dispatch(register({ email, username, password }));
    if (register.fulfilled.match(result)) {
      dispatch(login({ username, password }));
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#0f172a' }}>
      <Paper sx={{ p: 4, width: 380, bgcolor: '#1e293b', color: 'white' }} elevation={8}>
        <Typography variant="h5" fontWeight={700} mb={1} color="white">
          EUVoice AI Platform
        </Typography>
        <Typography variant="body2" color="text.secondary" mb={3}>
          EU-compliant voice AI infrastructure
        </Typography>

        <Tabs value={tab} onChange={(_, v) => { setTab(v); dispatch(clearError()); }}
          sx={{ mb: 3, '& .MuiTab-root': { color: '#94a3b8' }, '& .Mui-selected': { color: 'white' } }}>
          <Tab label="Sign In" />
          <Tab label="Register" />
        </Tabs>

        {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => dispatch(clearError())}>{error}</Alert>}

        {tab === 0 ? (
          <Box component="form" onSubmit={handleLogin}>
            <TextField fullWidth label="Username" value={username} onChange={e => setUsername(e.target.value)}
              margin="normal" required autoFocus
              InputLabelProps={{ style: { color: '#94a3b8' } }}
              InputProps={{ style: { color: 'white' } }}
              sx={{ '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: '#334155' } } }} />
            <TextField fullWidth label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)}
              margin="normal" required
              InputLabelProps={{ style: { color: '#94a3b8' } }}
              InputProps={{ style: { color: 'white' } }}
              sx={{ '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: '#334155' } } }} />
            <Button fullWidth type="submit" variant="contained" sx={{ mt: 3, py: 1.5, bgcolor: '#6366f1' }}
              disabled={loading}>
              {loading ? <CircularProgress size={22} color="inherit" /> : 'Sign In'}
            </Button>
          </Box>
        ) : (
          <Box component="form" onSubmit={handleRegister}>
            <TextField fullWidth label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)}
              margin="normal" required autoFocus
              InputLabelProps={{ style: { color: '#94a3b8' } }}
              InputProps={{ style: { color: 'white' } }}
              sx={{ '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: '#334155' } } }} />
            <TextField fullWidth label="Username" value={username} onChange={e => setUsername(e.target.value)}
              margin="normal" required
              InputLabelProps={{ style: { color: '#94a3b8' } }}
              InputProps={{ style: { color: 'white' } }}
              sx={{ '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: '#334155' } } }} />
            <TextField fullWidth label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)}
              margin="normal" required
              InputLabelProps={{ style: { color: '#94a3b8' } }}
              InputProps={{ style: { color: 'white' } }}
              sx={{ '& .MuiOutlinedInput-root': { '& fieldset': { borderColor: '#334155' } } }} />
            <Button fullWidth type="submit" variant="contained" sx={{ mt: 3, py: 1.5, bgcolor: '#6366f1' }}
              disabled={loading}>
              {loading ? <CircularProgress size={22} color="inherit" /> : 'Create Account'}
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default Login;
