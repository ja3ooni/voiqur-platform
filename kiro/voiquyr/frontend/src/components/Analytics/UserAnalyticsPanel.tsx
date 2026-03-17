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
  Chip
} from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { PieChart } from '@mui/x-charts/PieChart';
import { LineChart } from '@mui/x-charts/LineChart';
import { useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import PeopleIcon from '@mui/icons-material/People';
import ChatIcon from '@mui/icons-material/Chat';
import LanguageIcon from '@mui/icons-material/Language';
import MoodIcon from '@mui/icons-material/Mood';

const UserAnalyticsPanel: React.FC = () => {
  const { userAnalytics } = useSelector((state: RootState) => state.analytics);

  const languageData = userAnalytics.conversationInsights.mostUsedLanguages.map(lang => ({
    label: lang.language,
    value: lang.count,
    id: lang.language
  }));

  const emotionData = userAnalytics.conversationInsights.emotionDistribution.map(emotion => ({
    label: emotion.emotion,
    value: emotion.percentage,
    id: emotion.emotion
  }));

  const peakHoursData = userAnalytics.userBehavior.peakUsageHours.map(hour => hour.usage);
  const hourLabels = userAnalytics.userBehavior.peakUsageHours.map(hour => 
    `${hour.hour.toString().padStart(2, '0')}:00`
  );

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Box display="flex" alignItems="center" mb={3}>
        <PeopleIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6">User Analytics & Conversation Insights</Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Conversation Overview */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <ChatIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="subtitle1">Conversation Overview</Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Box textAlign="center">
                    <Typography variant="h3" color="primary.main">
                      {userAnalytics.conversationInsights.totalConversations.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Conversations
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box textAlign="center">
                    <Typography variant="h3" color="success.main">
                      {userAnalytics.conversationInsights.averageConversationLength.toFixed(1)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Avg Turns per Conversation
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>  
      {/* Language Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <LanguageIcon sx={{ mr: 1, color: 'warning.main' }} />
                <Typography variant="subtitle1">Language Usage</Typography>
              </Box>
              <Box sx={{ height: 200 }}>
                <PieChart
                  series={[{
                    data: languageData,
                    highlightScope: { faded: 'global', highlighted: 'item' }
                  }]}
                  width={300}
                  height={200}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Emotion Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MoodIcon sx={{ mr: 1, color: 'success.main' }} />
                <Typography variant="subtitle1">Emotion Distribution</Typography>
              </Box>
              <Box sx={{ height: 200 }}>
                <BarChart
                  xAxis={[{
                    scaleType: 'band',
                    data: emotionData.map(e => e.label)
                  }]}
                  series={[{
                    data: emotionData.map(e => e.value),
                    color: '#4caf50'
                  }]}
                  width={300}
                  height={200}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Peak Usage Hours */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Peak Usage Hours (24h)
              </Typography>
              <Box sx={{ height: 200 }}>
                <LineChart
                  xAxis={[{
                    scaleType: 'point',
                    data: hourLabels.filter((_, i) => i % 2 === 0) // Show every 2nd hour for readability
                  }]}
                  series={[{
                    data: peakHoursData.filter((_, i) => i % 2 === 0),
                    color: '#2196f3',
                    curve: 'linear'
                  }]}
                  width={300}
                  height={200}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Intent Distribution */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Most Common Intents
              </Typography>
              <List>
                {userAnalytics.conversationInsights.intentDistribution.map((intent, index) => (
                  <ListItem key={index} divider>
                    <ListItemText
                      primary={intent.intent}
                      secondary={`${intent.count} occurrences`}
                    />
                    <Chip
                      label={`${((intent.count / userAnalytics.conversationInsights.totalConversations) * 100).toFixed(1)}%`}
                      color="primary"
                      variant="outlined"
                      size="small"
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default UserAnalyticsPanel;