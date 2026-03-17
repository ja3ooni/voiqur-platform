import { LatencyMetric, Region, SipTrunk } from "./types";

export const ORCHESTRATOR_VERSION = "v1.0.4-beta";

export const REGIONS_CONFIG = [
  { id: Region.EU_FRANKFURT, lat: 50.11, lng: 8.68, active: true },
  { id: Region.ME_BAHRAIN, lat: 26.06, lng: 50.55, active: true },
  { id: Region.ASIA_MUMBAI, lat: 19.07, lng: 72.87, active: true },
  { id: Region.ASIA_SINGAPORE, lat: 1.35, lng: 103.81, active: false },
  { id: Region.ASIA_TOKYO, lat: 35.67, lng: 139.65, active: false },
];

export const MOCK_SIP_TRUNKS: SipTrunk[] = [
  { id: '1', name: 'Tata Pri', provider: 'Tata Communications', uri: 'sip:gw.tata.com', status: 'Connected', region: Region.ASIA_MUMBAI },
  { id: '2', name: 'Twilio EU', provider: 'Twilio', uri: 'sip:voiquyr.pstn.twilio.com', status: 'Connected', region: Region.EU_FRANKFURT },
];

export const MOCK_LATENCY_DATA: LatencyMetric[] = Array.from({ length: 20 }).map((_, i) => ({
  timestamp: `10:${30 + i}`,
  ttfb: Math.floor(Math.random() * (250 - 150) + 150),
  e2e: Math.floor(Math.random() * (600 - 350) + 350),
  region: Region.EU_FRANKFURT,
}));