# 🌍 SDGs 17項目標 × 169項細項目標 配對挑戰賽 (SDGs Matching Challenge)

> 專為聯合國 2030 永續發展目標設計的配對遊戲系統，具備挑戰者資料庫紀錄、全服即時排行榜、以及現代化數據管理後台。

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🌟 核心特色 (Key Features)

### 🎮 1. 前台沉浸式配對遊戲
- **完整納入 17 目標與 169 細項**：精確收錄 17 項核心大目標、全數 169 項具體指標（含數字編號之「成果目標」與英文字母編號之「執行方法」），並支援 5P 架構（人、地球、繁榮、和平、夥伴）與生活情境日常案例。
- **4 大特色遊玩模式**：
  1. 🏡 **生活情境入門模式**：日常生活案例（如惜食、節電、淨灘）與 17 目標配對。
  2. 🎯 **標準細項配對模式**：隨機抽取 169 細項，精準配對至所屬 17 大目標。
  3. 🃏 **翻牌記憶連連看**：經典 16 卡牌翻牌記憶模式，比速度與短時記憶。
  4. 👑 **169細項極限闖關**：30 題高壓極速挑戰，考驗對指標條文的透徹度。
- **動態計分與 Combo 連擊倍率**：連續答對觸發連擊額外加分，答錯重置連擊並扣除懲罰分數。
- **原生音效合成系統**：採用 HTML5 Web Audio API 原生音頻振盪器合成答對和弦、答錯低頻、連擊音效與勝利旋律，**無須下載任何音效檔，100% 離線可用**。
- **知識解析卡片彈窗**：答題後即時展示該指標之官方全文、條文編號、指標屬性與生活實踐範例。
- **挑戰者證書與榮譽榜**：依正確率頒發「永續傳教士」、「永續實踐家」、「永續探險者」或「永續種子」認證徽章，並即時登錄全服排行榜。

### 🛡️ 2. 專業後台管理系統 (Admin Dashboard)
- **視覺化 KPI 監控**：即時掌握全服挑戰總人次、累積對局數、全服平均得分與平均答對率。
- **學習盲點診斷**：**「最常配對錯誤之細項目標 Top 5」**分析，幫助教育推廣者一眼看清學員盲點。
- **挑戰對局日誌管理**：支援挑戰者暱稱/組織搜尋、依模式篩選、個別異常紀錄刪除。
- **一鍵匯出 CSV 報表**：支援 Excel 繁體中文 UTF-8 BOM 格式，方便匯出對局數據進行課堂評分或統計。
- **169 項指標維護 CMS**：可依目標篩選指標、即時編輯條文說明、一鍵啟閉該題是否在遊戲中出題。
- **動態計分規則設定**：線上即時修改作答倒數秒數、基礎得分、連擊加權分與扣分懲罰。

---

## 🏗️ 專案目錄結構 (Directory Structure)

```text
sdgs-matching-game/
├── app/                      # 後端核心模組 (FastAPI)
│   ├── __init__.py
│   ├── main.py               # FastAPI 應用入口與靜態資源託管
│   ├── database.py           # SQLite 連線池、自動建表、種子資料匯入
│   ├── models.py             # Pydantic 請求與回應資料結構
│   ├── auth.py               # 管理員 Token 驗證與 SHA-256 密碼雜湊
│   ├── game_routes.py        # 前台遊戲 API (抽題、對局、計分、排行榜)
│   ├── admin_routes.py       # 後台管理 API (數據統計、日誌審查、指標維護、匯出)
│   └── data.json             # 17 大目標與 169 細項繁體中文標準資料庫
├── static/                   # 前端客戶端靜態資源 (SPA)
│   ├── index.html            # 前台遊戲首頁 (HTML5)
│   ├── admin.html            # 後台管理儀表板 (HTML5)
│   ├── css/
│   │   └── style.css         # 聯合國官方色票與響應式 RWD 樣式庫
│   └── js/
│       ├── game.js           # 遊戲客戶端邏輯、音效合成、計時連擊引擎
│       └── admin.js          # 後台數據儀表板與 API 互動腳本
├── docs/
│   └── SYSTEM_ANALYSIS.md    # 完整系統分析與設計規格書 (SA/SD)
├── tests/
│   ├── __init__.py
│   └── test_api.py           # API 整合與單元測試套件
├── main.py                   # 本機一鍵啟動腳本
├── requirements.txt          # Python 相依套件列表
├── Dockerfile                # Docker 映像檔建置檔
├── docker-compose.yml        # Docker Compose 一鍵啟動檔
├── .gitignore                # Git 忽略檔案清單
└── README.md                 # 專案說明書
```

---

## 🚀 快速開始 (Quick Start)

### 方法一：本機 Python 直接啟動 (推薦)

#### 1. 安裝相依套件
```bash
pip install -r requirements.txt
```

#### 2. 啟動服務
```bash
python main.py
```
> 或使用 uvicorn 啟動：
> ```bash
> uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
> ```

#### 3. 開啟瀏覽器體驗
- **遊戲前台**：[http://localhost:8000](http://localhost:8000)
- **管理後台**：[http://localhost:8000/admin](http://localhost:8000/admin)
  - 預設管理員帳號：`admin`
  - 預設管理員密碼：`sdgs2030admin`
- **Swagger API 互動文件**：[http://localhost:8000/docs](http://localhost:8000/docs)

---

### 方法二：Docker 容器化一鍵啟動

```bash
# 建置並啟動容器
docker-compose up -d --build
```
啟動後即可直接瀏覽 `http://localhost:8000`。

---

## 🧪 執行自動化測試 (Run Automated Tests)

專案內建完整的單元測試套件，涵蓋目標讀取、169細項完整性、遊戲對局開立與計分結算、排行榜、管理員身分認證與數據監控端點：

```bash
python3 -m unittest tests/test_api.py
```

---

## 📤 如何將本專案上傳至 GitHub (GitHub Upload Guide)

依照以下五個標準步驟，即可將本專案發布至個人的 GitHub 儲存庫：

### 步驟 1：在 GitHub 建立新的 Repository
1. 登入 [GitHub](https://github.com/)。
2. 點選右上角 `+` -> **New repository**。
3. Repository name 輸入：`sdgs-matching-game`。
4. 設定為 **Public**（公開）或 **Private**（私人）。
5. **不要勾選** "Initialize this repository with a README"（專案內已具備完整 README）。
6. 點擊 **Create repository**。

### 步驟 2：在專案目錄初始化 Git
開啟命令列終端機（Terminal / CMD / PowerShell），進入 `sdgs-matching-game` 目錄：

```bash
cd sdgs-matching-game
git init
```

### 步驟 3：暫存並提交程式碼
```bash
git add .
git commit -m "feat: complete SDGs 17 goals & 169 targets matching game with database and admin dashboard"
```

### 步驟 4：關聯 GitHub 遠端儲存庫
將 `<YOUR_GITHUB_USERNAME>` 替換為您的 GitHub 帳號名稱：

```bash
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/sdgs-matching-game.git
```

### 步驟 5：推送到 GitHub
```bash
git push -u origin main
```
完成後，重新整理您的 GitHub 網頁即可看到完整的程式碼、檔案架構與漂亮的 README 文件！

---

## 📊 API 端點一覽 (RESTful Endpoints Summary)

| Method | Endpoint | 說明 | 權限要求 |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/game/goals` | 獲取 17 大目標代碼、全稱、顏色、5P 分類與標語 | 公開 |
| `GET` | `/api/game/targets` | 獲取 169 細項指標資料（支援關鍵字與目標篩選） | 公開 |
| `POST` | `/api/game/start` | 登錄挑戰者並創建對局，自動生成題目與干擾選項 | 公開 |
| `POST` | `/api/game/answer` | 提交作答、計算連擊加權分、記錄歷程並回傳解析卡 | 公開 |
| `POST` | `/api/game/finish` | 結算成績、計算全服排名並頒發認證徽章 | 公開 |
| `GET` | `/api/game/leaderboard` | 取得即時排行榜（支援依遊戲模式篩選） | 公開 |
| `POST` | `/api/admin/login` | 管理員登入驗證，回傳 Bearer Token | 公開 |
| `GET` | `/api/admin/stats` | 取得 KPI 數據、模式熱門度、Top 5 易錯細項分析 | 管理員 |
| `GET` | `/api/admin/records` | 分頁查詢挑戰對局日誌（支援關鍵字檢索） | 管理員 |
| `DELETE`| `/api/admin/records/{id}` | 刪除指定對局紀錄 | 管理員 |
| `GET` | `/api/admin/targets` | 查詢 169 細項指標狀態列表 | 管理員 |
| `PUT` | `/api/admin/targets/{id}` | 線上更新細項說明條文或啟閉題目 | 管理員 |
| `GET` | `/api/admin/settings` | 檢視系統計分與限時設定 | 管理員 |
| `PUT` | `/api/admin/settings/{key}` | 更新指定遊戲規則參數 | 管理員 |
| `GET` | `/api/admin/export/csv` | 匯出全服挑戰紀錄為 CSV 報表（附帶 UTF-8 BOM） | 管理員 |

---

## 📜 資料來源與致謝 (Attribution & References)
- **聯合國官方永續發展目標**：[sdgs.un.org/goals](https://sdgs.un.org/goals)
- **全球目標 Global Goals 台灣中文網**：[globalgoals.tw](https://globalgoals.tw)
- **行政院國家永續發展委員會**：[ncsd.ndc.gov.tw](https://ncsd.ndc.gov.tw)
- 佛光永續學院 × 佛光大學應用科技與設計學院 課程教材（戴慶華 Dr. ANDERSON）

---

## 📄 開源授權 (License)
本專案採用 [MIT License](LICENSE) 授權釋出，歡迎自由推廣、教學與二次開發。
