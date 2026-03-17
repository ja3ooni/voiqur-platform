import React, { useState } from 'react';
import { Box, Typography, Grid, Paper, Tabs, Tab } from '@mui/material';
import { AudioStreamingPanel } from '../../components/Audio';
import { AnalyticsDashboard } from '../../components/Analytics';

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
      id={`dashboard-tabpanel-${index}`}
      aria-labelledby={`dashboard-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ height: '100%' }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const Dashboard = () => {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box sx={{ p: 3, height: '100vh', overflow: 'hidden' }}>
      <Typography variant="h4" gutterBottom>
        EUVoice AI Dashboard
      </Typography>
      
      <Paper sx={{ height: 'calc(100vh - 120px)' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="dashboard tabs"
          sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}
        >
          <Tab label="Voice Assistant" id="dashboard-tab-0" />
          <Tab label="Analytics & Monitoring" id="dashboard-tab-1" />
        </Tabs>

        <Box sx={{ height: 'calc(100% - 48px)', overflow: 'auto' }}>
          <TabPanel value={tabValue} index={0}>
            <Box sx={{ p: 2, height: '100%' }}>
              <AudioStreamingPanel />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Box sx={{ p: 2, height: '100%' }}>
              <AnalyticsDashboard />
            </Box>
          </TabPanel>
        </Box>
      </Paper>
    </Box>
  );
};

export default Dashboard;
