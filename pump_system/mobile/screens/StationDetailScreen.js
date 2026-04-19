import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';

import { api, realtime } from '../services/api';

const STATUS_COLOR = {
  normal: '#2ecc71',
  info: '#3498db',
  warning: '#f39c12',
  critical: '#e74c3c',
  offline: '#7f8c8d',
};

function Gauge({ level, warn, high, flood }) {
  const max = Math.max(flood * 1.1, level ?? 0, 1);
  const pct = Math.min(1, (level ?? 0) / max);
  const radius = 80;
  const circumference = Math.PI * radius; // semi-circle
  const offset = circumference * (1 - pct);

  let color = '#2ecc71';
  if (level >= flood) color = '#e74c3c';
  else if (level >= high) color = '#f39c12';
  else if (level >= warn) color = '#3498db';

  return (
    <View style={{ alignItems: 'center' }}>
      <Svg width="220" height="130" viewBox="0 0 220 130">
        <Circle
          cx="110"
          cy="110"
          r={radius}
          stroke="#ecf0f1"
          strokeWidth="16"
          fill="none"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset="0"
          transform="rotate(180 110 110)"
        />
        <Circle
          cx="110"
          cy="110"
          r={radius}
          stroke={color}
          strokeWidth="16"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={offset}
          transform="rotate(180 110 110)"
        />
        <SvgText
          x="110"
          y="100"
          textAnchor="middle"
          fontSize="28"
          fontWeight="bold"
          fill="#2c3e50"
        >
          {level != null ? level.toFixed(2) : '-'}
        </SvgText>
        <SvgText x="110" y="120" textAnchor="middle" fontSize="12" fill="#7f8c8d">
          m
        </SvgText>
      </Svg>
      <View style={styles.thresholdRow}>
        <Threshold label="주의" value={warn} color="#3498db" />
        <Threshold label="고수위" value={high} color="#f39c12" />
        <Threshold label="월류" value={flood} color="#e74c3c" />
      </View>
    </View>
  );
}

function Threshold({ label, value, color }) {
  return (
    <View style={styles.threshold}>
      <View style={[styles.thresholdDot, { backgroundColor: color }]} />
      <Text style={styles.thresholdLabel}>{label}</Text>
      <Text style={styles.thresholdValue}>{value.toFixed(2)}m</Text>
    </View>
  );
}

function HistoryChart({ readings, flood }) {
  const width = 320;
  const height = 160;
  const padding = 28;

  if (!readings || readings.length === 0) {
    return <Text style={styles.empty}>최근 24시간 데이터 없음</Text>;
  }

  const values = readings.map((r) => r.water_level_m);
  const minV = 0;
  const maxV = Math.max(flood * 1.1, ...values);
  const step = (width - padding * 2) / Math.max(1, readings.length - 1);

  const points = readings
    .map((r, i) => {
      const x = padding + i * step;
      const y =
        height - padding - ((r.water_level_m - minV) / (maxV - minV)) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  const floodY =
    height - padding - ((flood - minV) / (maxV - minV)) * (height - padding * 2);

  return (
    <Svg width={width} height={height}>
      <Rect x="0" y="0" width={width} height={height} fill="#fff" />
      <Line
        x1={padding}
        y1={floodY}
        x2={width - padding}
        y2={floodY}
        stroke="#e74c3c"
        strokeWidth="1"
        strokeDasharray="4,3"
      />
      <SvgText x={width - padding} y={floodY - 4} fontSize="10" fill="#e74c3c" textAnchor="end">
        월류 {flood.toFixed(2)}m
      </SvgText>
      <Polyline points={points} fill="none" stroke="#0b4a7a" strokeWidth="2" />
    </Svg>
  );
}

export default function StationDetailScreen({ route }) {
  const { id } = route.params;
  const [station, setStation] = useState(null);
  const [history, setHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [s, h] = await Promise.all([api.getStation(id), api.getHistory(id, 24)]);
      setStation(s);
      setHistory(h);
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const unsub = realtime.subscribe((msg) => {
      if (msg.type !== 'reading' || msg.station_id !== id) return;
      setStation((s) =>
        s
          ? {
              ...s,
              water_level_m: msg.water_level_m,
              inflow_m3s: msg.inflow_m3s ?? s.inflow_m3s,
              outflow_m3s: msg.outflow_m3s ?? s.outflow_m3s,
              pumps_running: msg.pumps_running ?? s.pumps_running,
              status: msg.status ?? s.status,
              last_reported_at: msg.timestamp ?? s.last_reported_at,
            }
          : s
      );
      setHistory((prev) => {
        const next = [...prev, {
          recorded_at: msg.timestamp,
          water_level_m: msg.water_level_m,
        }];
        return next.slice(-300);
      });
    });
    return unsub;
  }, [id]);

  const color = useMemo(() => STATUS_COLOR[station?.status] ?? '#7f8c8d', [station]);

  if (loading) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color="#0b4a7a" />
      </View>
    );
  }

  if (!station) {
    return (
      <View style={styles.container}>
        <Text style={styles.error}>펌프장 정보를 불러올 수 없습니다.</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            load();
          }}
        />
      }
    >
      <View style={[styles.headerCard, { borderColor: color }]}>
        <Text style={styles.region}>{station.region}</Text>
        <Text style={styles.title}>{station.name}</Text>
        <Gauge
          level={station.water_level_m}
          warn={station.warn_level_m}
          high={station.high_level_m}
          flood={station.flood_level_m}
        />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>현재 상태</Text>
        <Row label="유입량" value={fmt(station.inflow_m3s, 'm³/s')} />
        <Row label="방류량" value={fmt(station.outflow_m3s, 'm³/s')} />
        <Row
          label="가동 펌프"
          value={`${station.pumps_running ?? 0} / ${station.pump_count}`}
        />
        <Row
          label="설계용량"
          value={`${station.capacity_m3s.toFixed(1)} m³/s`}
        />
        <Row
          label="최근 보고"
          value={
            station.last_reported_at
              ? new Date(station.last_reported_at).toLocaleString('ko-KR')
              : '-'
          }
        />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>24시간 수위 추이</Text>
        <HistoryChart readings={history} flood={station.flood_level_m} />
      </View>
    </ScrollView>
  );
}

function Row({ label, value }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

function fmt(v, unit) {
  if (v == null) return '-';
  return `${Number(v).toFixed(2)} ${unit}`;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7fa', padding: 12 },
  headerCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 10,
    borderLeftWidth: 6,
    marginBottom: 12,
    alignItems: 'center',
  },
  region: { color: '#7f8c8d', alignSelf: 'flex-start' },
  title: {
    fontSize: 20,
    fontWeight: '700',
    alignSelf: 'flex-start',
    marginBottom: 8,
    color: '#2c3e50',
  },
  card: {
    backgroundColor: '#fff',
    padding: 14,
    borderRadius: 10,
    marginBottom: 12,
  },
  cardTitle: { fontSize: 15, fontWeight: '700', marginBottom: 8, color: '#2c3e50' },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#ecf0f1',
  },
  rowLabel: { color: '#7f8c8d' },
  rowValue: { color: '#2c3e50', fontWeight: '600' },
  thresholdRow: { flexDirection: 'row', marginTop: 6 },
  threshold: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 6 },
  thresholdDot: { width: 8, height: 8, borderRadius: 4, marginRight: 4 },
  thresholdLabel: { color: '#7f8c8d', marginRight: 3, fontSize: 12 },
  thresholdValue: { color: '#2c3e50', fontSize: 12, fontWeight: '600' },
  empty: { color: '#95a5a6', padding: 12 },
  error: { color: '#c0392b' },
});
