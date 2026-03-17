import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Box,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
  AlertTitle,
  IconButton,
  LinearProgress,
  Tooltip
} from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/store';
import { acknowledgeAlert, dismissAlert } from '../../store/slices/analyticsSlice';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import CancelIcon from '@mui/icons-material/Cancel';
import CloseIcon from '@mui/icons-material/Close';
import CheckIcon from '@mui/icons-material/Check';
import MemoryIcon from '@mui/icons-material/Memory';
import StorageIcon from '@mui/icons-material/Storage';

const SystemHealthPanel: React.FC = () => {
  const dispatch = useDispatch();
  const { systemHealth } = useSelector((state: RootState) => state.analytics);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon sx={{ color: 'success.main' }} />;
      case 'warning':
        return <WarningIcon sx={{ color: 'warning.main' }} />;
      case 'critical':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      case 'down':
        return <CancelIcon sx={{ color: 'error.main' }} />;
      default:
        return <CheckCircleIcon sx={{ color: 'grey.500' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
      case 'down':
        return 'error';
      default:
        return 'default';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'info':
        return 'info';
      case 'warning':
        return 'warning';
      case 'error':
      case 'critical':
        return 'error';
      default:
        return 'info';
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const handleAcknowledgeAlert = (alertId: string) => {
    dispatch(acknowledgeAlert(alertId));
  };

  const handleDismissAlert = (alertId: string) => {
    dispatch(dismissAlert(alertId));
  };

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Box display="flex" alignItems="center" mb={3}>
        <HealthAndSafetyIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6">System Health & Monitoring</Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Service Status */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Service Status
              </Typography>
              <List>
                {systemHealth.services.map((service, index) => (
                  <ListItem key={index} divider>
                    <ListItemIcon>
                      {getStatusIcon(service.status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1">{service.name}</Typography>
                          <Chip
                            label={service.status}
                            color={getStatusColor(service.status) as any}
                            size="small"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Uptime: {formatUptime(service.uptime)} | 
                            Response: {service.responseTime}ms | 
                            Error Rate: {service.errorRate}%
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid> 
       {/* Resource Usage */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MemoryIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="subtitle1">Resource Usage</Typography>
              </Box>
              
              {Object.entries(systemHealth.resources).map(([resource, data]) => (
                <Box key={resource} mb={2}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                      {resource}
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {data.usage}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={data.usage}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: data.usage >= 90 ? 'error.main' : 
                                       data.usage >= 75 ? 'warning.main' : 'success.main'
                      }
                    }}
                  />
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* Alerts */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                System Alerts
              </Typography>
              {systemHealth.alerts.length === 0 ? (
                <Box display="flex" alignItems="center" justifyContent="center" py={4}>
                  <CheckCircleIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Typography variant="body1" color="success.main">
                    No active alerts - All systems operating normally
                  </Typography>
                </Box>
              ) : (
                <Box>
                  {systemHealth.alerts.map((alert) => (
                    <Alert
                      key={alert.id}
                      severity={getSeverityColor(alert.severity) as any}
                      sx={{ mb: 2, opacity: alert.acknowledged ? 0.7 : 1 }}
                      action={
                        <Box>
                          {!alert.acknowledged && (
                            <Tooltip title="Acknowledge Alert">
                              <IconButton
                                size="small"
                                onClick={() => handleAcknowledgeAlert(alert.id)}
                                sx={{ mr: 1 }}
                              >
                                <CheckIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          <Tooltip title="Dismiss Alert">
                            <IconButton
                              size="small"
                              onClick={() => handleDismissAlert(alert.id)}
                            >
                              <CloseIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      }
                    >
                      <AlertTitle>
                        {alert.service && `${alert.service} - `}
                        {alert.severity.toUpperCase()}
                        {alert.acknowledged && ' (Acknowledged)'}
                      </AlertTitle>
                      <Typography variant="body2">
                        {alert.message}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(alert.timestamp).toLocaleString()}
                      </Typography>
                    </Alert>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default SystemHealthPanel;