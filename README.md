# 🌍 SDGs 17項目標 × 169項細項目標 配對挑戰賽 (SDGs Matching Challenge)

> 專為聯合國 2030 永續發展目標設計的配對遊戲系統，支援 Vercel 無伺服器部署、Turso 雲端 SQLite 永久存檔、全服即時排行榜、以及現代化數據管理後台。

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Turso](https://img.shields.io/badge/Database-Turso%20libSQL-00eb88.svg)](https://turso.tech/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-black.svg)](https://vercel.com/)
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
- **4 個模式獨立排行榜**：各模式成績獨立排行、公平競爭，並全面以中文名稱標記。
- **自動記憶挑戰者資料**：輸入暱稱與所屬組織後自動儲存於瀏覽器，重新整理或換題不需重複輸入。
- **完整 169 細項學習手冊**：內建教材導讀（「怎麼讀這份資料」）、5P 快速切換、1~17 號色票跳轉鈕與全文即時搜尋。
- **原生音效合成系統**：採用 HTML5 Web Audio API 原生音頻合成器，無須下載任何音效檔，100% 離線可用。

### 🛡️ 2. 專業後台管理系統 (Admin Dashboard)
- **視覺化 KPI 監控**：即時掌握全服挑戰總人次、累積對局數、全服平均得分與平均答對率。
- **學習盲點診斷**：**「最常配對錯誤之細項目標 Top 5」**分析，幫助教育推廣者一眼看清學員盲點。
- **分模式紀錄審查與獨立匯出**：依四大模式分頁審查挑戰日誌，並支援各別匯出 UTF-8 BOM CSV 報表。
- **169 項指標維護 CMS**：可依目標篩選指標、即時編輯條文說明、一鍵啟閉該題。
- **動態計分規則設定**：線上即時修改作答倒數秒數、基礎得分、連擊加權分與扣分懲罰。

---

## 🏗️ 專案目錄結構 (Directory Structure)

```text
sdgs-matching-game/
├── api/
│   ├── __init__.py
│   └── index.py              # 舊版入口相容模組；目前以 main:app 部署
├── app/                      # 後端核心模組 (FastAPI)
│   ├── __init__.py
│   ├── main.py               # FastAPI 應用入口與靜態資源託管
│   ├── database.py           # Turso HTTP / 本機 SQLite 資料庫介面
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
├── migrate_to_turso.py       # Turso 雲端資料庫一鍵初始化工具
├── main.py                   # Vercel ASGI 入口與本機啟動腳本
├── vercel.json               # Vercel 部署設定檔
├── requirements.txt          # Python 相依套件列表
├── Dockerfile                # Docker 映像檔建置檔
├── docker-compose.yml        # Docker Compose 一鍵啟動檔
├── .gitignore                # Git 忽略檔案清單
└── README.md                 # 專案說明書
```

---

## 部署至 Vercel + Turso

此版本採用 Vercel 原生 FastAPI 入口 `main:app`，資料儲存於 Turso。
保留原有 17 個目標、169 個細項、四種遊戲模式與後台功能。

- [Vercel 專案](https://vercel.com/ipuregreen/sdgs-matching-game)
- [Turso 組織](https://app.turso.tech/vinnyhuangipuregreen)
- **完整操作步驟：[docs/DEPLOY_VERCEL_TURSO.md](docs/DEPLOY_VERCEL_TURSO.md)**

1. 在 Turso 組織中選取或建立資料庫，取得 **Database URL** 及具有讀寫權限的 **Database Auth Token**。組織控制台網址不是資料庫網址。
2. 複製 `.env.example` 為 `.env`，填入 `TURSO_DATABASE_URL`、`TURSO_AUTH_TOKEN`，以及首次建立管理員所需的 `SDGS_ADMIN_PASSWORD`。
3. 安裝相依套件並初始化：

   ```powershell
   python -m pip install -r requirements.txt
   python migrate_to_turso.py
   ```

   若要保留既有 SQLite 的排行榜、管理員與題庫編輯，請改為對**尚未初始化的空資料庫**執行：

   ```powershell
   python migrate_to_turso.py --from-sqlite .\sdgs_game.db
   ```

   兩種初始化方式擇一。移轉保留既有管理員密碼，登入憑證需重新取得。
4. 在 Vercel 專案填入相同的 `TURSO_DATABASE_URL`、`TURSO_AUTH_TOKEN`，選用 FastAPI 框架，根目錄設為本專案根目錄。推送到專案所連接的 Git 分支，或使用文件中的 Vercel CLI 指令部署。
5. 確認 `/healthz` 回傳 `{"status":"ok","database":"turso"}`，測試遊戲、後台與重新部署後的排行榜。

設定缺漏或 Turso 連線失敗時，雲端服務會回報錯誤，不會改用 `/tmp` SQLite。
資料庫初始化獨立執行，避免每次冷啟動重建題庫。再次執行初始化不覆蓋現有條文、啟閉狀態、計分設定或管理員密碼。
實際費用、配額及資料保留政策以 Vercel / Turso 帳戶方案為準。

## 本機執行與測試

使用 VS Code 開啟本專案資料夾，選擇「執行與偵錯」中的 **SDGs 遊戲（Turso）** 並按 F5。
設定檔使用 `.venv` 的 Python，從 `.env` 載入資料庫連線；請先完成套件安裝及資料庫初始化。
首次雲端建立的管理員帳號為 `admin`，初始密碼請查看本機 `.env` 的 `SDGS_ADMIN_PASSWORD`。

需要 Python 3.12 以上；本次自動化測試使用 Python 3.13。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m unittest discover -v
node --test tests/test_game_client.cjs
.\.venv\Scripts\python main.py
```

- 前台：`http://localhost:8000`
- 後台：`http://localhost:8000/admin`
- 未設定 Turso 時，以本機 `sdgs_game.db` 運作；可用 `SDGS_DB_PATH` 指定檔案。
- 新建本機 SQLite 的預設帳密是 `admin` / `sdgs2030admin`；設定 `SDGS_ADMIN_PASSWORD` 可指定初始密碼。既有帳號不會因環境變數變更而重設。
- 設定 Turso 後，本機也會連線至該 Turso 資料庫，請先執行初始化。
- 測試使用隔離的暫存資料庫與 Turso HTTP 協定模擬，不會修改本機遊戲資料庫或連線至正式 Turso。

壓縮檔包含完整原始碼、`app/data.json`、設定範例、文件與測試；不含 `.env`、私人連線金鑰、本機對局資料庫、Git 歷史或虛擬環境。既有 `sdgs_game.db` 保留於原資料夾，可另行移轉。

---

## 📜 版權與致謝 (Attribution)
Pure Green Foundation 綠色公益基金會 © 2026. All Rights Reserved.
