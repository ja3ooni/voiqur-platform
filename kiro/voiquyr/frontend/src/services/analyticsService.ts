import { PerformanceMetrics, UserAnalytics, SystemHealth } from '../types/analytics';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class AnalyticsService {
  private async fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 5000): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json', ...options.headers },
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    try {
      // Use the real health endpoint and map to PerformanceMetrics shape
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/v1/health/detailed`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      return {
        latency: { stt: 0, llm: 0, tts: 0, total: 0 },
        throughput: { requestsPerSecond: 0, activeConnections: 0 },
        accuracy: { stt: 0, llm: 0, tts: 0 },
        uptime: data.uptime ?? 0,
        errorRate: 0,
        cpuUsage: data.performance?.cpu_usage_percent ?? 0,
        memoryUsage: data.performance?.memory_usage_percent ?? 0,
        alerts: [],
      } as unknown as PerformanceMetrics;
    } catch {
      // Return empty metrics rather than crashing the UI
      return {} as PerformanceMetrics;
    }
  }

  async getUserAnalytics(): Promise<UserAnalytics> {
    return {} as UserAnalytics;
  }

  async getSystemHealth(): Promise<SystemHealth> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/v1/health/`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch {
      return {} as SystemHealth;
    }
  }

  async acknowledgeAlert(_alertId: string): Promise<void> {}
  async dismissAlert(_alertId: string): Promise<void> {}

  subscribeToMetrics(_onUpdate: (metrics: PerformanceMetrics) => void): () => void {
    return () => {};
  }

  async exportMetrics(_startDate: string, _endDate: string, _format: 'csv' | 'json' = 'json'): Promise<Blob> {
    return new Blob();
  }
}

export const analyticsService = new AnalyticsService();
export default analyticsService;

class AnalyticsService {
  private async fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 5000): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
      
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/analytics/performance`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
      throw new Error('Failed to fetch performance metrics');
    }
  }

  async getUserAnalytics(): Promise<UserAnalytics> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/analytics/users`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch user analytics:', error);
      throw new Error('Failed to fetch user analytics');
    }
  }

  async getSystemHealth(): Promise<SystemHealth> {
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/analytics/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to fetch system health:', error);
      throw new Error('Failed to fetch system health');
    }
  }

  async acknowledgeAlert(alertId: string): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${API_BASE_URL}/analytics/alerts/${alertId}/acknowledge`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      throw new Error('Failed to acknowledge alert');
    }
  }

  async dismissAlert(alertId: string): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${API_BASE_URL}/analytics/alerts/${alertId}`,
        { method: 'DELETE' }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to dismiss alert:', error);
      throw new Error('Failed to dismiss alert');
    }
  }

  // Real-time metrics subscription using WebSocket
  subscribeToMetrics(onUpdate: (metrics: PerformanceMetrics) => void): () => void {
    const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/analytics/metrics/stream`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const metrics = JSON.parse(event.data);
        onUpdate(metrics);
      } catch (error) {
        console.error('Failed to parse metrics update:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    // Return cleanup function
    return () => {
      ws.close();
    };
  }

  // Export metrics data for reporting
  async exportMetrics(startDate: string, endDate: string, format: 'csv' | 'json' = 'json'): Promise<Blob> {
    try {
      const response = await this.fetchWithTimeout(
        `${API_BASE_URL}/analytics/export?start=${startDate}&end=${endDate}&format=${format}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.blob();
    } catch (error) {
      console.error('Failed to export metrics:', error);
      throw new Error('Failed to export metrics');
    }
  }
}

export const analyticsService = new AnalyticsService();
export default analyticsService;