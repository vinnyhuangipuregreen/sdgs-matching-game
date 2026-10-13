# SDGs 17項目標 × 169項細項目標 配對遊戲系統
## 完整系統分析與設計規格書 (System Analysis & Design Specification)

---

### 版本資訊 (Document Revision History)
- **文件版本**：v1.0.0
- **系統名稱**：SDGs 17項目標 × 169項細項配對挑戰賽 (SDGs Matching Challenge)
- **參考依據**：
  - 聯合國 2030 永續發展目標（UN SDGs 2015-2030）
  - 《SDGs 17項目標 × 169項細項目標》教材（佛光大學永續學院教材）
  - 《課前看一看｜SDGs 17個目標》核心教材（5P 框架與生活情境指標）
  - 全球目標 Global Goals 台灣中文網（globalgoals.tw）與行政院國家永續發展委員會規範

---

## 1. 專案背景與目標 (Project Overview & Objectives)

### 1.1 專案背景
2015年聯合國大會通過《2030年永續發展議程》，提出 17 項核心永續發展目標（Sustainable Development Goals, SDGs）以及 169 項具體細項目標（Targets），涵蓋貧窮、飢餓、健康、教育、氣候、生態等多面向重大議題，核心精神在於「不遺漏任何人」（Leave no one behind）。

然而，在教育與推廣現場，大眾往往僅熟知 17 個大目標的標題，對於具體可檢核的「169項細項承諾」缺乏深入理解。本專案旨在透過「互動配對遊戲化學習」（Gamified Matching Challenge），將 17 項核心目標、169 項細項（含成果目標與執行方法）、以及日常生動案例緊密融合，提供寓教於樂、激發挑戰動機的數位學習平台。

### 1.2 專案核心目標
1. **精準對齊官方知識庫**：完整納入 17 項核心目標與全數 169 項細項目標，區分「數字編號成果目標（如 13.1）」與「英文字母執行方法（如 13.a）」，並融入 5P 架構（人、地球、繁榮、和平、夥伴）與生活案例。
2. **沉浸式多模式配對機制**：提供「生活情境入門」、「標準細項配對」、「翻牌記憶連連看」與「169極限大師」等多元玩法，結合動態倒數、連擊（Combo）加乘機制與語音音效反饋。
3. **挑戰者履歷與全服排行榜**：記錄挑戰者之暱稱、所屬組織/學校、遊戲模式、得分、連擊數與用時，建立即時競技排行榜與永續徽章制度。
4. **現代化數據監控後台**：提供管理員數據儀表板、全服參與度統計、最常配對錯誤之細項 Top 5 分析（掌握學習盲點）、對局紀錄審查與 CSV 報表匯出、169 細項題庫線上啟閉維護功能。
5. **開源標準化架構**：符合 GitHub 開源交付規範，支援 SQLite 零設定本機直接啟動、Docker / Docker Compose 容器化部署與全自動單元測試。

---

## 2. 利害關係人與使用者角色 (Stakeholders & Personas)

| 角色名稱 | 角色定位 | 核心關注點與使用情境 |
| :--- | :--- | :--- |
| **學生 / 挑戰者 (Challenger)** | 參與配對遊戲的終端玩家 | 直覺好玩的遊戲體驗、即時配對音效反饋、答案解說學習卡片、累積連擊高分、爭取排行榜名次與永續徽章。 |
| **永續教育師資 / 評量員 (Teacher)** | 課堂活動帶領者或比賽主辦方 | 學生參與人數統計、課堂分組競技、最常答錯之細項弱點診斷、一鍵匯出全班挑戰成效 CSV 報表。 |
| **系統管理員 (Admin)** | 平台維護與題庫管理者 | 系統參數調整（每題秒數、基礎分、連擊倍率）、指標內容文字維護、題庫啟閉、無效紀錄清理。 |

---

## 3. 系統功能需求 (Functional Requirements)

### 3.1 挑戰者前台遊戲端 (Frontend Game Engine)
- **[FR-01] 挑戰者資料登錄**：支援輸入暱稱、學校/組織單位，以及選擇個人特色虛擬頭像（🌱、🌟、🌍、🐬、🌳 等）。
- **[FR-02] 多元挑戰模式選取**：
  1. *生活情境入門模式 (Scenario Mode)*：依生活日常案例（如惜食、節電、淨灘）配對 17 目標。
  2. *標準細項配對模式 (Standard Mode)*：自 169 細項隨機抽取 10 題，判斷所屬之 SDGs 大目標。
  3. *翻牌記憶連連看 (Card Memory Mode)*：16 張覆蓋卡牌進行短時記憶配對，細項與目標兩兩成對。
  4. *169細項極限闖關 (Master 169 Mode)*：30 題連續高壓答題，測驗對成果目標與執行方法的透徹度。
- **[FR-03] 即時配對反饋與音效合成**：
  - 答對時給予悅耳和弦反饋，觸發連續答對 Combo 加分。
  - 答錯時給予低頻提示並重置連擊數，標示正確答案。
  - 內建 HTML5 Web Audio API 原生音頻合成器，無須載入任何外部音效檔案，100% 離線運行。
- **[FR-04] 知識卡片即時解析**：配對後彈出詳細解析卡，顯示該細項指標之官方條文、類別屬性（成果目標 vs 執行方法）以及 5P 領域歸屬。
- **[FR-05] 挑戰結算與徽章頒授**：結算總分、正確率、最高連擊、作答秒數，根據成績授予「永續傳教士」、「永續實踐家」、「永續探險者」或「永續種子」榮譽證書。
- **[FR-06] 即時全服排行榜與 SDGs 學習手冊**：提供分模式排行榜查閱，並內建 17 目標與 169 細項線上百科。

### 3.2 後台管理系統 (Admin Dashboard & CMS)
- **[FR-07] 管理員身分安全認證**：支援 Bearer Token / Session 驗證機制，防止未授權存取。
- **[FR-08] 數據分析 KPI 儀表板**：
  - 全服挑戰總人次、累積對局數、平均得分、平均答對率。
  - 各遊戲模式參與熱度分佈統計。
  - **最常配對錯誤之細項目標 Top 5**（提供精準之學習成效盲點分析）。
- **[FR-09] 挑戰對局紀錄審查**：分頁列出全服挑戰紀錄，支援暱稱/單位關鍵字搜尋、模式篩選、個別異常紀錄刪除。
- **[FR-10] 一鍵匯出 CSV 報表**：將全服挑戰數據（含 UTF-8 BOM 支援 Excel 正常開啟不亂碼）匯出為 CSV 試算表。
- **[FR-11] 169 細項目標線上維護**：支援依照 17 目標篩選細項、關鍵字檢索、線上編輯細項說明與一鍵啟閉該題。
- **[FR-12] 遊戲規則與計分參數自訂**：後台可動態設定作答限時（秒）、基礎答對得分、連擊加乘分、答錯扣分懲罰等。

---

## 4. 非功能性需求 (Non-Functional Requirements)

| 維度 | 需求標準 | 具體實現策略 |
| :--- | :--- | :--- |
| **效能與回應 (Performance)** | API 端點 95% 回應時間 < 50ms | 採用高效非同步 Python FastAPI 框架搭配 SQLite 記憶體映射索引。 |
| **可攜性與相容性 (Portability)** | 零配置一鍵啟動 | 資料庫內建自動遷移與初始種子匯入機制；同時提供 Docker 容器封裝。 |
| **跨裝置相容 (RWD)** | 支援 Mobile、Tablet、Desktop | 前端 CSS 採用 Fluid Flexbox/Grid 響應式佈局與移動端觸控優化。 |
| **離線自我封閉性 (Self-contained)** | 無對外網路依賴 | 音效採用 Web Audio API 振盪器直接合成；不依賴外部 CDN，斷網亦可全功能運作。 |
| **安全性 (Security)** | 憑證防護與防注入 | 管理員密碼採用 SHA-256 加鹽雜湊，SQL 查詢嚴格採用參數化防護 SQL Injection。 |

---

## 5. 系統架構設計 (System Architecture)

### 5.1 整體系統分層架構
```
+-------------------------------------------------------------------------------+
|                       前端客戶端展示層 (Presentation Layer)                    |
|  - 前台遊戲 SPA (index.html / game.js) : 角色登記、模式選擇、配對核心、音效引擎  |
|  - 後台管理 SPA (admin.html / admin.js) : 數據監控、日誌審查、指標維護、匯出 CSV |
+---------------------------------------+---------------------------------------+
                                        | HTTP / JSON RESTful APIs
+---------------------------------------v---------------------------------------+
|                       後端應用服務層 (Application Layer)                      |
|  - FastAPI Web 框架 (main.py) : CORS、靜態資源路由、例外處理過濾器              |
|  - Game 業務路由器 (game_routes.py) : 對局創建、隨機抽題、答案檢驗、計分結算   |
|  - Admin 業務路由器 (admin_routes.py) : 身分認證、儀表板聚合、指標維護、報表匯出|
|  - Auth 模組 (auth.py) : Token 驗證與過期管理                                 |
+---------------------------------------+---------------------------------------+
                                        | Python sqlite3 / Row Factory
+---------------------------------------v---------------------------------------+
|                       資料持久化儲存層 (Persistence Layer)                    |
|  - SQLite 關聯式資料庫 (sdgs_game.db / 具備自動容錯跨檔案系統機制)             |
|  - 預置種子數據庫 (data.json) : 17 目標標準色彩、169 細項繁體中文標準條文     |
+-------------------------------------------------------------------------------+
```

---

## 6. 資料庫綱要設計 (Database Schema Design)

### 6.1 實體關聯圖 (Entity-Relationship Conceptual Diagram)
```
[goals] 1 <---- N [targets]
   1                 1
   |                 |
   v                 v
[scenarios]      [game_details] N ---- 1 [game_sessions] N ---- 1 [challengers]
```

### 6.2 資料表結構與資料字典 (Data Dictionary)

#### 1. `goals` (SDGs 17項核心目標表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY | 目標編號 (1 至 17) |
| `code` | TEXT | NOT NULL, UNIQUE | 目標代碼 (例如 "SDG 1") |
| `name` | TEXT | NOT NULL | 目標簡稱 (例如 "消除貧窮") |
| `full_name` | TEXT | NOT NULL | 目標官方全文 |
| `category` | TEXT | NOT NULL | 5P 分類英文 (People, Planet, Prosperity, Peace, Partnership) |
| `category_zh` | TEXT | NOT NULL | 5P 分類中文 (人、地球、繁榮、和平、夥伴) |
| `color` | TEXT | NOT NULL | 聯合國官方標準色票 HEX (例如 #E5243B) |
| `icon` | TEXT | NULL | 圖示符號或 Emoji |
| `slogan` | TEXT | NULL | 生活化核心標語 (課前看一看) |
| `example` | TEXT | NULL | 日常生活對照範例 |
| `is_active` | INTEGER | DEFAULT 1 | 啟用狀態 (1: 啟用, 0: 停用) |

#### 2. `targets` (SDGs 169項具體細項目標表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 細項唯一識別碼 (1 至 169) |
| `code` | TEXT | NOT NULL, UNIQUE | 細項編號 (例如 "1.1", "1.a", "13.2") |
| `goal_id` | INTEGER | FOREIGN KEY (`goals.id`) | 所屬核心目標 ID (1 至 17) |
| `type` | TEXT | NOT NULL | 指標類型 ("成果目標" 或 "執行方法") |
| `description` | TEXT | NOT NULL | 細項目標完整規範條文 |
| `is_means` | INTEGER | DEFAULT 0 | 是否為執行方法 (字母編號為 1，數字為 0) |
| `is_active` | INTEGER | DEFAULT 1 | 是否納入遊戲題庫 (1: 是, 0: 否) |

#### 3. `scenarios` (生活情境案例表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 情境編號 |
| `goal_id` | INTEGER | FOREIGN KEY (`goals.id`) | 所屬核心目標 ID |
| `scenario_text` | TEXT | NOT NULL | 核心日常生活情境標語 |
| `real_life_example` | TEXT | NOT NULL | 具體行動範例 (如：三好校園、惜食) |
| `is_active` | INTEGER | DEFAULT 1 | 啟用狀態 |

#### 4. `challengers` (挑戰者資料表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 挑戰者流水號 |
| `nickname` | TEXT | NOT NULL | 挑戰者暱稱 |
| `organization`| TEXT | DEFAULT '一般挑戰者' | 學校、班級或所屬組織機構 |
| `avatar` | TEXT | DEFAULT '🌱' | 挑戰者頭像代碼 |
| `created_at` | DATETIME| DEFAULT CURRENT_TIMESTAMP | 首次註冊/建立時間 |

#### 5. `game_sessions` (挑戰遊戲對局紀錄表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 對局代碼 |
| `challenger_id`| INTEGER | FOREIGN KEY (`challengers.id`) | 關聯挑戰者 |
| `mode` | TEXT | NOT NULL | 遊戲模式 (scenario, standard, cards, master169) |
| `difficulty` | TEXT | DEFAULT 'medium' | 難度級別 |
| `total_score` | INTEGER | DEFAULT 0 | 最終結算總得分 |
| `total_questions`| INTEGER | DEFAULT 0 | 總配對題數 |
| `correct_count`| INTEGER | DEFAULT 0 | 答對題數 |
| `combo_max` | INTEGER | DEFAULT 0 | 該局最高連續答對數 |
| `time_taken_seconds` | REAL | DEFAULT 0 | 總耗費作答秒數 |
| `completed_at`| DATETIME| DEFAULT CURRENT_TIMESTAMP | 完成結算時間 |

#### 6. `game_details` (每題作答歷程日誌表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 明細流水號 |
| `session_id` | INTEGER | FOREIGN KEY (`game_sessions.id`) | 關聯對局 ID |
| `target_id` | INTEGER | NULL | 關聯細項 ID |
| `goal_id` | INTEGER | NOT NULL | 正確所屬之目標 ID |
| `selected_goal_id` | INTEGER | NOT NULL | 挑戰者點選之目標 ID |
| `is_correct` | INTEGER | NOT NULL | 是否正確 (1: 對, 0: 錯) |
| `time_spent_ms`| INTEGER | DEFAULT 0 | 該題作答耗時 (毫秒) |

#### 7. `admin_users` (管理員帳號表)
| 欄位名稱 | 型態 | 限制 | 說明 |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 管理員序號 |
| `username` | TEXT | NOT NULL, UNIQUE | 管理員登入帳號 |
| `password_hash`| TEXT | NOT NULL | SHA-256 密碼雜湊值 |
| `role` | TEXT | DEFAULT 'admin' | 管理角色 |

#### 8. `system_settings` (系統動態參數表)
| 鍵名 (`key`) | 預設值 (`value`) | 說明 |
| :--- | :--- | :--- |
| `time_limit_per_question` | `20` | 每題作答倒數限制秒數 |
| `points_base` | `100` | 基礎答對得分 |
| `points_combo_bonus` | `25` | 連擊額外遞增得分 (第 N 連擊額外 +(N-1)*25) |
| `points_penalty_wrong` | `20` | 答錯懲罰扣分 |
| `questions_per_game` | `10` | 標準模式每局出題數 |
| `leaderboard_display_limit` | `20` | 前台排行榜顯示筆數 |

---

## 7. RESTful API 規格書 (API Specification)

### 7.1 前台遊戲端點 (Game APIs)
- **`GET /api/game/goals`**
  - 功能：獲取 17 項 SDGs 目標之完整資訊（代碼、名稱、全文、顏色、5P 分類、標語）。
- **`GET /api/game/targets`**
  - 參數：`goal_id` (選填)、`q` (搜尋字串)
  - 功能：取得 169 細項列表，供學習手冊與練習模組查閱。
- **`POST /api/game/start`**
  - 請求本體：`{ nickname, organization, avatar, mode, question_count }`
  - 功能：建立挑戰者與遊戲對局，隨機抽取題目並動態生成 4 個候選目標（1 正解 + 3 干擾項）。
- **`POST /api/game/answer`**
  - 請求本體：`{ session_id, question_index, target_id, selected_goal_id, correct_goal_id, time_spent_ms, current_combo }`
  - 功能：檢驗答案、計算連擊與即時得分、記錄至作答日誌，並回傳目標詳細知識卡。
- **`POST /api/game/finish`**
  - 請求本體：`{ session_id, total_score, total_questions, correct_count, combo_max, time_taken_seconds }`
  - 功能：結算成績、計算全服名次並頒發永續榮譽徽章。
- **`GET /api/game/leaderboard`**
  - 參數：`mode` (選填)、`limit` (預設 20)
  - 功能：取得排行榜名單。

### 7.2 後台管理端點 (Admin APIs)
- **`POST /api/admin/login`**
  - 請求本體：`{ username, password }`
  - 回應：`{ status: "success", token: "...", username: "admin" }`
- **`GET /api/admin/stats`** [需認證]
  - 功能：取得全服核心 KPI、各模式佔比、**Top 5 易錯細項分析**。
- **`GET /api/admin/records`** [需認證]
  - 參數：`page`, `page_size`, `search`, `mode`
  - 功能：分頁檢索挑戰者之對局歷史紀錄。
- **`DELETE /api/admin/records/{id}`** [需認證]
  - 功能：刪除指定遊戲紀錄。
- **`GET /api/admin/targets`** [需認證]
  - 功能：取得 169 指標管理清單。
- **`PUT /api/admin/targets/{id}`** [需認證]
  - 請求本體：`{ description, is_active }`
  - 功能：線上更新指標條文或切換啟用狀態。
- **`GET /api/admin/settings` & `PUT /api/admin/settings/{key}`** [需認證]
  - 功能：檢視與修改系統計分與倒數規則。
- **`GET /api/admin/export/csv`** [需認證]
  - 功能：下載包含 UTF-8 BOM 之 CSV 挑戰紀錄報表。

---

## 8. 遊戲機制與配對演算法設計 (Game Mechanics & Algorithm)

### 8.1 計分與連擊公式 (Scoring & Combo Formula)
設第 $i$ 題基礎分為 $P_{base}$（預設 100 分），連擊獎勵係數為 $P_{combo}$（預設 25 分），目前連續答對次數為 $C$（當前連擊數）：
$$\Delta S_{correct} = P_{base} + (C - 1) \times P_{combo} \quad (C \ge 1)$$
若答錯，則連擊數歸零（$C = 0$），並倒扣懲罰分數：
$$\Delta S_{wrong} = - P_{penalty} \quad (\text{最低總分保護 } S \ge 0)$$

### 8.2 智能干擾項生成演算法 (Distractor Generation)
在生成 4 選 1 目標選項時：
1. 目標 $G_{correct}$ 為正確目標。
2. 系統從其餘 16 個目標中，隨機且非重複抽取 3 個目標作為干擾項 $\{G_{d1}, G_{d2}, G_{d3}\}$。
3. 利用 Fisher-Yates Shuffle 演算法將 4 個選項打亂排序，防止固定選項位置記憶。

### 8.3 永續榮譽徽章體系
- **永續傳教士 (SDGs Champion)**：正確率 $\ge 90\%$
- **永續實踐家 (SDGs Practitioner)**：正確率 $70\% \sim 89\%$
- **永續探險者 (SDGs Explorer)**：正確率 $50\% \sim 69\%$
- **永續種子 (Eco Seed)**：正確率 $< 50\%$

---

## 9. GitHub 上傳與部署指南 (Deployment Guide)

### 9.1 Git 儲存庫結構規範
```
sdgs-matching-game/
├── app/                      # 後端核心模組
│   ├── __init__.py
│   ├── main.py               # FastAPI 啟動入口
│   ├── database.py           # 資料庫連線、自動建表與遷移
│   ├── models.py             # Pydantic 資料綱要
│   ├── auth.py               # 身分驗證與 Session 管理
│   ├── game_routes.py        # 遊戲前台 API 路由
│   ├── admin_routes.py       # 後台管理 API 路由
│   └── data.json             # 17 目標與 169 細項完整種子資料庫
├── static/                   # 前端客戶端靜態資源
│   ├── index.html            # 遊戲主頁 SPA
│   ├── admin.html            # 後台管理 SPA
│   ├── css/
│   │   └── style.css         # 聯合國官方色票與響應式樣式
│   └── js/
│       ├── game.js           # 遊戲客戶端邏輯與音效合成
│       └── admin.js          # 後台儀表板與數據操作邏輯
├── docs/                     # 專案文件目錄
│   └── SYSTEM_ANALYSIS.md    # 系統分析與設計規格書
├── tests/                    # 自動化測試模組
│   ├── __init__.py
│   └── test_api.py           # API 單元測試案例
├── main.py                   # 本機一鍵啟動入口腳本
├── requirements.txt          # Python 相依套件列表
├── Dockerfile                # Docker 映像檔建置檔
├── docker-compose.yml        # Docker Compose 服務編排檔
├── .gitignore                # Git 忽略清單
└── README.md                 # 專案說明書與快速指引
```

### 9.2 GitHub 上傳步驟指引
在終端機進入專案目錄後執行：
```bash
# 1. 初始化 Git 儲存庫
git init

# 2. 加入所有程式與資源檔案
git add .

# 3. 提交初始版本 Commit
git commit -m "feat: initial commit of SDGs 17 goals & 169 targets matching game with admin backend"

# 4. 綁定個人 GitHub 遠端儲存庫 (請替換為您在 GitHub 建立的 repo 網址)
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/sdgs-matching-game.git

# 5. 推送至 GitHub main 分支
git branch -M main
git push -u origin main
```
