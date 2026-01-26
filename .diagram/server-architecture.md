# 로매처 서버 구축 및 연계 다이어그램

## 1. 서버 구축 방법 (옵션 비교)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#f5f5f5', 'primaryColor': '#4a90d9', 'secondaryColor': '#82c91e'}}}%%
flowchart TB
    subgraph Option1["옵션 1: 서버 PC 직접 구매"]
        PC1[("🖥️ 물리 서버 PC")]
        PC1 --> IP1["고정 IP 할당"]
        PC1 --> PORT1["포트 개방<br/>(80, 443, 8000)"]
        PC1 --> FW1["방화벽 설정"]
    end

    subgraph Option2["옵션 2: 구청 서버 가상자원 할당"]
        VM1[("☁️ 가상머신 VM")]
        VM1 --> IP2["내부 IP 할당"]
        VM1 --> PORT2["포트 포워딩<br/>(80, 443, 8000)"]
        VM1 --> FW2["보안그룹 설정"]
    end

    Decision{{"서버 구축<br/>방법 선택"}}
    Decision --> Option1
    Decision --> Option2

    Option1 --> Deploy["로매처 배포<br/>(Docker/직접설치)"]
    Option2 --> Deploy

    style Option1 fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style Option2 fill:#dcfce7,stroke:#22c55e,stroke-width:2px
    style PC1 fill:#60a5fa,stroke:#2563eb,color:#fff
    style VM1 fill:#4ade80,stroke:#16a34a,color:#fff
    style IP1 fill:#fef3c7,stroke:#f59e0b
    style IP2 fill:#fef3c7,stroke:#f59e0b
    style PORT1 fill:#fce7f3,stroke:#ec4899
    style PORT2 fill:#fce7f3,stroke:#ec4899
    style FW1 fill:#fee2e2,stroke:#ef4444
    style FW2 fill:#fee2e2,stroke:#ef4444
    style Decision fill:#fbbf24,stroke:#d97706,color:#000
    style Deploy fill:#a855f7,stroke:#7c3aed,color:#fff
```

## 2. 로매처 - 새올 서버 연계 구조

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#fafafa'}}}%%
flowchart LR
    subgraph Saewol["🔴 새올 시스템"]
        SF["🖥️ 새올 프론트 서버<br/>(기존 시스템)"]
        SB["🗄️ 새올 백엔드"]
        SF <--> SB
    end

    subgraph LawMatcher["🔵 로매처 시스템"]
        LF["🖥️ 로매처 프론트<br/>(React)"]
        LB["⚙️ 로매처 백엔드<br/>(FastAPI)"]
        DB[("🗃️ PostgreSQL")]
        LF <--> LB
        LB <--> DB
    end

    SF -- "iframe 또는 링크<br/>좌측 하단 '조례개정' 메뉴" --> LF
    SB -- "REST API 호출<br/>/api/v1/ordinances<br/>/api/v1/law-changes" --> LB
    LB -- "조례 데이터 조회" --> SB

    style Saewol fill:#fef2f2,stroke:#dc2626,stroke-width:3px
    style LawMatcher fill:#eff6ff,stroke:#2563eb,stroke-width:3px
    style SF fill:#f87171,stroke:#dc2626,color:#fff
    style SB fill:#fca5a5,stroke:#ef4444,color:#000
    style LF fill:#60a5fa,stroke:#2563eb,color:#fff
    style LB fill:#3b82f6,stroke:#1d4ed8,color:#fff
    style DB fill:#8b5cf6,stroke:#6d28d9,color:#fff
```

## 3. API 연계 상세

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'actorBkg': '#60a5fa', 'actorTextColor': '#fff', 'actorBorder': '#2563eb', 'signalColor': '#1e293b', 'signalTextColor': '#1e293b', 'noteBkgColor': '#fef3c7', 'noteTextColor': '#000'}}}%%
sequenceDiagram
    participant User as 👤 사용자
    participant Saewol as 🔴 새올 프론트
    participant LawFront as 🔵 로매처 프론트
    participant LawAPI as 🔵 로매처 API
    participant SaewolAPI as 🔴 새올 API

    User->>Saewol: 좌측 메뉴 "조례개정" 클릭
    Saewol->>LawFront: iframe/새창으로 로매처 접속
    LawFront->>LawAPI: GET /api/v1/ordinances
    LawAPI-->>LawFront: 조례 목록 (JSON)

    User->>LawFront: 법령 변경사항 조회
    LawFront->>LawAPI: GET /api/v1/law-changes
    LawAPI-->>LawFront: 변경사항 목록 (JSON)

    Note over LawAPI,SaewolAPI: 데이터 동기화 (선택사항)
    LawAPI->>SaewolAPI: POST /sync/ordinances
    SaewolAPI-->>LawAPI: 동기화 결과
```

## 4. 데이터 교환 형식

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dbeafe', 'primaryTextColor': '#1e3a8a', 'primaryBorderColor': '#3b82f6', 'lineColor': '#64748b'}}}%%
classDiagram
    class OrdinanceRequest {
        +string title
        +string content
        +date enacted_date
        +string department
    }

    class OrdinanceResponse {
        +int id
        +string title
        +string content
        +date enacted_date
        +string department
        +datetime created_at
        +datetime updated_at
    }

    class LawChangeResponse {
        +int id
        +string law_name
        +string change_type
        +date effective_date
        +string[] affected_ordinances
        +string summary
    }

    OrdinanceRequest --> OrdinanceResponse : API 응답
```

## 5. 네트워크 구성도

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#f8fafc'}}}%%
flowchart TB
    subgraph External["🌍 외부 네트워크"]
        Internet["🌐 인터넷"]
    end

    subgraph DMZ["🛡️ DMZ 구간"]
        FW["🔥 방화벽"]
        LB["⚖️ 로드밸런서<br/>(선택사항)"]
    end

    subgraph Internal["🏢 내부 네트워크 (구청)"]
        subgraph ServerZone["💻 서버 존"]
            LM["🖥️ 로매처 서버<br/>IP: 192.168.x.x<br/>Port: 8000, 3000"]
            SW["🖥️ 새올 서버<br/>IP: 192.168.x.x<br/>Port: 80, 443"]
        end

        subgraph DBZone["🗄️ DB 존"]
            LMDB[("🗃️ 로매처 DB<br/>Port: 5432")]
            SWDB[("🗃️ 새올 DB")]
        end
    end

    Internet --> FW
    FW --> LB
    LB --> LM
    LB --> SW
    LM <--> LMDB
    SW <--> SWDB
    LM <-.-> SW

    style External fill:#e0e7ff,stroke:#6366f1,stroke-width:2px
    style DMZ fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style Internal fill:#dcfce7,stroke:#22c55e,stroke-width:2px
    style ServerZone fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style DBZone fill:#f3e8ff,stroke:#a855f7,stroke-width:2px
    style Internet fill:#818cf8,stroke:#4f46e5,color:#fff
    style FW fill:#f87171,stroke:#dc2626,color:#fff
    style LB fill:#fbbf24,stroke:#d97706,color:#000
    style LM fill:#60a5fa,stroke:#2563eb,color:#fff
    style SW fill:#f87171,stroke:#dc2626,color:#fff
    style LMDB fill:#8b5cf6,stroke:#6d28d9,color:#fff
    style SWDB fill:#fb7185,stroke:#e11d48,color:#fff
```

---

## 색상 범례

| 색상 | 의미 |
|------|------|
| 🔵 파랑 | 로매처 시스템 |
| 🔴 빨강 | 새올 시스템 |
| 🟡 노랑 | 네트워크 장비 / 설정 |
| 🟢 초록 | 가상자원 / 내부망 |
| 🟣 보라 | 데이터베이스 |

---

## 사용 방법

이 Mermaid 다이어그램은 다음에서 렌더링됩니다:
- **GitHub**: README나 .md 파일에서 자동 렌더링
- **VSCode**: Markdown Preview Enhanced 확장 사용
- **온라인**: [Mermaid Live Editor](https://mermaid.live/)에서 PNG/SVG 내보내기
