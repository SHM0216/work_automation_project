# Pump Station Monitoring System

22개 빗물/우수 펌프장을 실시간으로 감시·경보하는 시스템입니다.
백엔드(FastAPI)와 모바일(React Native) 두 모듈로 구성되어 있으며,
현장 PLC/센서는 `field_bridge.py` 게이트웨이를 통해 백엔드에 데이터를 전송합니다.

---

## 구성

```
pump_system/
├── web/            정적 대시보드 (GitHub Pages / FastAPI에서 모두 서빙 가능)
├── backend/        FastAPI 서버 (REST + WebSocket)
│   ├── main.py
│   ├── database.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── stations.py
│   │   ├── sensors.py
│   │   └── alerts.py
│   ├── services/
│   │   └── alert_service.py
│   └── gateway/
│       └── field_bridge.py
└── mobile/         React Native 앱
    ├── App.js
    ├── services/api.js
    └── screens/
        ├── DashboardScreen.js
        ├── StationDetailScreen.js
        └── AlertsScreen.js
```

## 실행

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- OpenAPI 문서: `http://<host>:8000/docs`
- WebSocket(실시간 푸시): `ws://<host>:8000/ws`

### Field Bridge (현장 게이트웨이)

```bash
cd backend/gateway
python field_bridge.py --backend http://<host>:8000 --station-id 1
```

Modbus/OPC 장비가 없어도 `--simulate` 옵션으로 모의 데이터를 송신할 수 있습니다.

### Web Dashboard

정적 HTML 한 장으로 22개 펌프장을 실시간으로 볼 수 있습니다.

- **로컬 실행**: 백엔드 실행 후 `http://<host>:8000/` 로 접속하면 됩니다 (FastAPI가 `web/` 폴더를 그대로 서빙).
- **GitHub Pages 배포**: `pump_system/web/` 내용을 Pages 소스로 지정하면 즉시 게시됩니다. 첫 로드 시 데모(시뮬레이션) 모드로 동작하고, 우상단 **백엔드 설정** 버튼으로 실제 서버 URL을 입력하면 WebSocket 실시간 연결이 바뀝니다. URL 쿼리 `?api=http://server:8000` 으로도 지정 가능합니다.

### Mobile

```bash
cd mobile
npm install
npx expo start
```

`services/api.js` 상단의 `API_BASE_URL`을 실제 서버 주소로 바꿔주세요.

---

## API 목록

| Method | Path                                   | 설명                                         |
| ------ | -------------------------------------- | -------------------------------------------- |
| GET    | `/api/stations`                        | 22개 펌프장 목록 + 최신 상태                 |
| GET    | `/api/stations/{station_id}`           | 개별 펌프장 상세                             |
| GET    | `/api/stations/{station_id}/history`   | 최근 수위/유량 시계열 (기본 24시간)          |
| POST   | `/api/sensors/readings`                | 현장 게이트웨이가 센서 데이터 일괄 업로드    |
| GET    | `/api/alerts`                          | 경보 이력 조회 (level, station_id 필터 가능) |
| POST   | `/api/alerts/{alert_id}/acknowledge`   | 경보 확인 처리                               |
| POST   | `/api/alerts/{alert_id}/resolve`       | 경보 종료(해제) 처리                         |
| POST   | `/api/devices/push-token`              | 모바일 앱 푸시 토큰 등록                     |
| WS     | `/ws`                                  | 실시간 수위·경보 브로드캐스트                |

### WebSocket 메시지 형식

```json
{ "type": "reading",  "station_id": 3, "water_level_m": 2.31, "timestamp": "..." }
{ "type": "alert",    "alert_id": 12,  "station_id": 3, "level": "critical", ... }
{ "type": "resolved", "alert_id": 12 }
```

## 경보 기준 (기본값)

| 레벨      | 수위 조건                | 의미              |
| --------- | ------------------------ | ----------------- |
| info      | `≥ warn_level`           | 주의 수위 도달    |
| warning   | `≥ high_level`           | 고수위            |
| critical  | `≥ flood_level`          | 월류 위험         |
| offline   | 60초 이상 보고 없음      | 현장 장비 이상    |

각 펌프장의 임계값은 `database.py`의 초기 시드 데이터에 정의되어 있으며,
`PUT /api/stations/{id}/thresholds`(추후 확장)로 조정할 수 있도록 설계되었습니다.
