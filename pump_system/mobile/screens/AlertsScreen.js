import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert as RNAlert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { api, realtime } from '../services/api';

const LEVEL_COLOR = {
  info: '#3498db',
  warning: '#f39c12',
  critical: '#e74c3c',
  offline: '#7f8c8d',
};
const LEVEL_LABEL = {
  info: '주의',
  warning: '경보',
  critical: '위험',
  offline: '오프라인',
};
const FILTERS = [
  { key: 'all', label: '전체' },
  { key: 'active', label: '활성' },
  { key: 'critical', label: '위험' },
  { key: 'warning', label: '경보' },
  { key: 'offline', label: '오프라인' },
];

export default function AlertsScreen() {
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState('active');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const params = {};
    if (filter === 'active') params.activeOnly = true;
    else if (filter !== 'all') params.level = filter;
    try {
      const data = await api.listAlerts(params);
      setAlerts(data);
    } finally {
      setRefreshing(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const unsub = realtime.subscribe((msg) => {
      if (msg.type === 'alert') load();
      else if (msg.type === 'resolved' || msg.type === 'acknowledged') load();
    });
    return unsub;
  }, [load]);

  const doAck = async (a) => {
    try {
      await api.acknowledgeAlert(a.id);
      load();
    } catch (err) {
      RNAlert.alert('실패', err.message);
    }
  };

  const doResolve = async (a) => {
    try {
      await api.resolveAlert(a.id);
      load();
    } catch (err) {
      RNAlert.alert('실패', err.message);
    }
  };

  const renderItem = ({ item }) => {
    const color = LEVEL_COLOR[item.level] ?? '#7f8c8d';
    const ack = item.acknowledged_at != null;
    const resolved = item.resolved_at != null;
    return (
      <View style={[styles.card, { borderLeftColor: color }]}>
        <View style={styles.topRow}>
          <View style={[styles.levelBadge, { backgroundColor: color }]}>
            <Text style={styles.levelText}>{LEVEL_LABEL[item.level] ?? item.level}</Text>
          </View>
          <Text style={styles.time}>
            {new Date(item.triggered_at).toLocaleString('ko-KR')}
          </Text>
        </View>
        <Text style={styles.message}>{item.message}</Text>
        <View style={styles.meta}>
          <Text style={styles.metaText}>
            수위 {item.water_level_m != null ? `${item.water_level_m.toFixed(2)} m` : '-'}
          </Text>
          {ack && <Text style={styles.metaAck}>확인됨</Text>}
          {resolved && <Text style={styles.metaResolved}>해제됨</Text>}
        </View>
        {!resolved && (
          <View style={styles.actions}>
            {!ack && (
              <TouchableOpacity style={[styles.btn, styles.ackBtn]} onPress={() => doAck(item)}>
                <Text style={styles.btnText}>확인</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity
              style={[styles.btn, styles.resolveBtn]}
              onPress={() => doResolve(item)}
            >
              <Text style={styles.btnText}>해제</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterBtn, filter === f.key && styles.filterBtnActive]}
            onPress={() => setFilter(f.key)}
          >
            <Text
              style={[styles.filterText, filter === f.key && styles.filterTextActive]}
            >
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      <FlatList
        data={alerts}
        keyExtractor={(a) => String(a.id)}
        renderItem={renderItem}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              load();
            }}
          />
        }
        ListEmptyComponent={<Text style={styles.empty}>경보가 없습니다.</Text>}
        contentContainerStyle={{ paddingBottom: 24 }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f7fa', padding: 12 },
  filterRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10 },
  filterBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#ecf0f1',
    marginRight: 6,
    marginBottom: 6,
  },
  filterBtnActive: { backgroundColor: '#0b4a7a' },
  filterText: { color: '#2c3e50', fontWeight: '600' },
  filterTextActive: { color: '#fff' },
  card: {
    backgroundColor: '#fff',
    padding: 14,
    marginBottom: 10,
    borderRadius: 8,
    borderLeftWidth: 6,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  levelBadge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10 },
  levelText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  time: { color: '#7f8c8d', fontSize: 12 },
  message: { color: '#2c3e50', fontSize: 14, marginBottom: 6 },
  meta: { flexDirection: 'row', gap: 12 },
  metaText: { color: '#7f8c8d', fontSize: 12, marginRight: 10 },
  metaAck: { color: '#3498db', fontSize: 12, fontWeight: '600', marginRight: 10 },
  metaResolved: { color: '#2ecc71', fontSize: 12, fontWeight: '600' },
  actions: { flexDirection: 'row', marginTop: 10 },
  btn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 6,
    marginRight: 8,
  },
  ackBtn: { backgroundColor: '#3498db' },
  resolveBtn: { backgroundColor: '#27ae60' },
  btnText: { color: '#fff', fontWeight: '700' },
  empty: { textAlign: 'center', color: '#95a5a6', marginTop: 24 },
});
