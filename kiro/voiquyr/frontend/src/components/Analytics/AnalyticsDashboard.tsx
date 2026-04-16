import React, { useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/store';
import {
  fetchPerformanceMetrics,
  fetchUserAnalytics,
  fetchSystemHealth,
  clearError
} from '../../store/slices/analyticsSlice';
import PerformanceMetricsPanel from './PerformanceMetricsPanel';
import UserAnalyticsPanel from './UserAnalyticsPanel';
import SystemHealthPanel from './SystemHealthPanel';
import RefreshIcon from '@mui/icons-material/Refresh';
import CloseIcon from '@mui/icons-material/Close';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const AnalyticsDashboard: React.FC = () => {
  const dispatch = useDispatch();
  const { isLoading, error, lastUpdated } = useSelector((state: RootState) => state.analytics);
  const [tabValue, setTabValue] = React.useState(0);

  const handleRefreshData = useCallback(() => {
    dispatch(fetchPerformanceMetrics() as any);
    dispatch(fetchUserAnalytics() as any);
    dispatch(fetchSystemHealth() as any);
  }, [dispatch]);

  useEffect(() => {
    // Initial data fetch
    handleRefreshData();
    
    // Set up auto-refresh every 30 seconds
    const interval = setInterval(() => {
      handleRefreshData();
    }, 30000);

    return () => clearInterval(interval);
  }, [dispatch, handleRefreshData]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCloseError = () => {
    dispatch(clearError());
  };

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5">Analytics & Monitoring</Typography>
        <Box display="flex" alignItems="center" gap={2}>
          {lastUpdated && (
            <Typography variant="body2" color="text.secondary">
              Last updated: {new Date(lastUpdated).toLocaleTimeString()}
            </Typography>
          )}
          <Tooltip title="Refresh Data">
            <IconButton onClick={handleRefreshData} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <IconButton size="small" onClick={handleCloseError}>
              <CloseIcon fontSize="small" />
            </IconButton>
          }
        >
          {error}
        </Alert>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <Box display="flex" justifyContent="center" alignItems="center" py={4}>
          <CircularProgress />
          <Typography variant="body1" sx={{ ml: 2 }}>
            Loading analytics data...
          </Typography>
        </Box>
      )}

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="analytics tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Performance Metrics" id="analytics-tab-0" />
          <Tab label="User Analytics" id="analytics-tab-1" />
          <Tab label="System Health" id="analytics-tab-2" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <PerformanceMetricsPanel />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <UserAnalyticsPanel />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <SystemHealthPanel />
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default AnalyticsDashboard;