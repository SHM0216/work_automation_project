import React, { useCallback, useEffect, useState } from 'react';
import {
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { api, realtime } from '../services/api';

const STATUS_COLOR = {
  normal: '#2ecc71',
  info: '#3498db',
  warning: '#f39c12',
  critical: '#e74c3c',
  offline: '#7f8c8d',
};
const STATUS_LABEL = {
  normal: '정상',
  info: '주의',
  warning: '경보',
  critical: '위험',
  offline: '오프라인',
};

function fillFromReading(station, msg) {
  return {
    ...station,
    water_level_m: msg.water_level_m,
    inflow_m3s: msg.inflow_m3s ?? station.inflow_m3s,
    outflow_m3s: msg.outflow_m3s ?? station.outflow_m3s,
    pumps_running: msg.pumps_running ?? station.pumps_running,
    status: msg.status ?? station.status,
    last_reported_at: msg.timestamp ?? station.last_reported_at,
  };
}

export default function DashboardScreen({ navigation }) {
  const [stations, setStations] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await api.listStations();
      setStations(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const unsub = realtime.subscribe((msg) => {
      if (msg.type === 'reading') {
        setStations((prev) =>
          prev.map((s) => (s.id === msg.station_id ? fillFromReading(s, msg) : s))
        );
      } else if (msg.type === 'alert') {
        setStations((prev) =>
          prev.map((s) =>
            s.id === msg.station_id
              ? { ...s, active_alert_count: (s.active_alert_count ?? 0) + 1, status: msg.level }
              : s
          )
        );
      } else if (msg.type === 'resolved') {
        setStations((prev) =>
          prev.map((s) =>
            s.id === msg.station_id
              ? { ...s, active_alert_count: Math.max(0, (s.active_alert_count ?? 1) - 1) }
              : s
          )
        );
      }
    });
    return unsub;
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    load();
  };

  const renderItem = ({ item }) => {
    const color = STATUS_COLOR[item.status] ?? STATUS_COLOR.offline;
    const level = item.water_level_m != null ? item.water_level_m.toFixed(2) : '-';
    return (
      <TouchableOpacity
        style={[styles.card, { borderLeftColor: color }]}
        onPress={() =>
          navigation.navigate('StationDetail', { id: item.id, name: item.name })
        }
      >
        <View style={styles.cardTop}>
          <Text style={styles.stationName} numberOfLines={1}>
            {item.name}
          </Text>
          <View style={[styles.badge, { backgroundColor: color }]}>
            <Text style={styles.badgeText}>{STATUS_LABEL[item.status] ?? '-'}</Text>
          </View>
        </View>
        <Text style={styles.region}>{item.region}</Text>
        <View style={styles.metrics}>
          <Metric label="수위" value={`${level} m`} />
          <Metric
            label="가동펌프"
            value={`${item.pumps_running ?? 0}/${item.pump_count}`}
          />
          <Metric
            label="경보"
            value={`${item.active_alert_count ?? 0}건`}
          />
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.headerText}>
          실시간 {stations.length}개 펌프장
        </Text>
        <TouchableOpacity
          style={styles.alertsBtn}
          onPress={() => navigation.navigate('Alerts')}
        >
          <Text style={styles.alertsBtnText}>경보 이력</Text>
        </TouchableOpacity>
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={stations}
        keyExtractor={(s) => String(s.id)}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        contentContainerStyle={{ paddingBottom: 24 }}
      />
    </View>
  );
}

function Metric({ label, value }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7fa', padding: 12 },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  headerText: { fontSize: 16, fontWeight: '600', color: '#2c3e50' },
  alertsBtn: {
    backgroundColor: '#0b4a7a',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
  },
  alertsBtnText: { color: '#fff', fontWeight: '600' },
  error: { color: '#c0392b', marginBottom: 8 },
  card: {
    backgroundColor: '#fff',
    padding: 14,
    marginBottom: 10,
    borderRadius: 8,
    borderLeftWidth: 6,
    elevation: 2,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stationName: { fontSize: 16, fontWeight: '700', color: '#2c3e50', flex: 1 },
  region: { color: '#7f8c8d', marginTop: 2 },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginLeft: 8,
  },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  metrics: { flexDirection: 'row', marginTop: 10 },
  metric: { flex: 1 },
  metricLabel: { color: '#95a5a6', fontSize: 12 },
  metricValue: { fontSize: 15, fontWeight: '600', color: '#2c3e50' },
});
