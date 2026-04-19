import 'react-native-gesture-handler';
import React, { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

import DashboardScreen from './screens/DashboardScreen';
import StationDetailScreen from './screens/StationDetailScreen';
import AlertsScreen from './screens/AlertsScreen';
import { api, realtime } from './services/api';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

async function registerForPushNotifications() {
  if (!Device.isDevice) return null;
  const { status: existing } = await Notifications.getPermissionsAsync();
  let status = existing;
  if (existing !== 'granted') {
    const req = await Notifications.requestPermissionsAsync();
    status = req.status;
  }
  if (status !== 'granted') return null;
  const { data: token } = await Notifications.getExpoPushTokenAsync();
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('alerts', {
      name: '펌프장 경보',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF3B30',
    });
  }
  return token;
}

const Stack = createNativeStackNavigator();

export default function App() {
  const notifiedAlerts = useRef(new Set());

  useEffect(() => {
    (async () => {
      try {
        const token = await registerForPushNotifications();
        if (token) await api.registerPushToken(token);
      } catch (err) {
        console.warn('push token registration failed', err);
      }
    })();

    const unsub = realtime.subscribe(async (msg) => {
      if (msg.type !== 'alert') return;
      if (notifiedAlerts.current.has(msg.alert_id)) return;
      notifiedAlerts.current.add(msg.alert_id);
      await Notifications.scheduleNotificationAsync({
        content: {
          title: `[${msg.level.toUpperCase()}] ${msg.station_name ?? '펌프장 경보'}`,
          body: msg.message ?? '새 경보가 발생했습니다.',
          data: { stationId: msg.station_id, alertId: msg.alert_id },
        },
        trigger: null,
      });
    });
    realtime.start();

    return () => {
      unsub();
      realtime.stop();
    };
  }, []);

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Dashboard"
        screenOptions={{
          headerStyle: { backgroundColor: '#0b4a7a' },
          headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: 'bold' },
        }}
      >
        <Stack.Screen
          name="Dashboard"
          component={DashboardScreen}
          options={{ title: '펌프장 현황' }}
        />
        <Stack.Screen
          name="StationDetail"
          component={StationDetailScreen}
          options={({ route }) => ({ title: route.params?.name ?? '상세' })}
        />
        <Stack.Screen
          name="Alerts"
          component={AlertsScreen}
          options={{ title: '경보 이력' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
