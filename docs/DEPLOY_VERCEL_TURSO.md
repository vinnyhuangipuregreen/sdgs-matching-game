# Vercel 與 Turso 部署操作

本文件對應 Vercel `ipuregreen/sdgs-matching-game` 與 Turso 組織 `vinnyhuangipuregreen`。
程式修改完成不等於雲端已部署；需具備上述帳戶的專案權限與資料庫連線金鑰。

## 1. 準備 Turso 資料庫

開啟 [Turso 組織](https://app.turso.tech/vinnyhuangipuregreen)，選用資料庫或建立遊戲專用資料庫。
取得 Database URL（`libsql://…turso.io`、`turso://…turso.io` 或 `https://…turso.io`）及具備讀寫權限的 Database Auth Token。
請勿填入 `https://app.turso.tech/vinnyhuangipuregreen`，也不要使用 Turso 平台管理用 API Token。

在解壓縮後的專案根目錄執行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

在本機編輯 `.env`，填入：

```dotenv
TURSO_DATABASE_URL=從資料庫頁面複製的連線網址
TURSO_AUTH_TOKEN=從資料庫頁面取得的讀寫金鑰
SDGS_ADMIN_PASSWORD=自行設定的初始管理員密碼
```

程式會自動讀取 `.env`。此檔案已從 Git、Vercel 上傳及交付壓縮檔排除。

## 2. 初始化或移轉資料（擇一）

### 新資料庫

```powershell
.\.venv\Scripts\python migrate_to_turso.py
```

建立九張資料表、索引、17 項目標、169 項細項、17 個情境、計分設定及管理員。
管理員帳號為 `admin`，密碼為第一次初始化時設定的 `SDGS_ADMIN_PASSWORD`。
首次雲端初始化未設定密碼時會停止，不會建立公開預設密碼。

### 保留既有 SQLite 紀錄

先停止舊站的寫入並備份 `sdgs_game.db`。在原專案資料夾執行，或指定原資料庫的完整路徑：

```powershell
.\.venv\Scripts\python migrate_to_turso.py --from-sqlite 'C:\完整路徑\sdgs_game.db'
```

目的 Turso 資料庫的八張業務資料表必須全部為空；**不要先執行新資料庫初始化**。
工具以唯讀方式開啟來源 SQLite，保留所有 ID、挑戰者、對局、答題紀錄、題庫編輯、管理員密碼及計分設定。
匯入採單一交易，遇到目的資料表已有資料、SQL 錯誤或外鍵不一致即回復，不合併或清空雲端資料。
舊版程序記憶體中的登入憑證不移轉，管理員需重新登入。

匯入後補齊缺少的標準資料，不覆蓋現有題目、帳號或設定。若來源沒有任何管理員，仍需 `SDGS_ADMIN_PASSWORD`。
這個工具適用此遊戲的 SQLite 結構與一般大小的資料庫；大量歷史紀錄應改用 Turso 官方匯入工具，避免單次 HTTP 請求過大。

之後更新既有雲端版本，可再次執行不帶 `--from-sqlite` 的初始化以補建新資料表。

## 3. 設定 Vercel 專案

開啟 [Vercel 專案](https://vercel.com/ipuregreen/sdgs-matching-game)。

在 Settings → Environment Variables 新增：

| 名稱 | 值 | 環境 |
| --- | --- | --- |
| `TURSO_DATABASE_URL` | 步驟 1 的資料庫連線網址 | Production；需要時另設 Preview / Development |
| `TURSO_AUTH_TOKEN` | 相同資料庫的讀寫金鑰 | 同上 |

`SDGS_ADMIN_PASSWORD` 只供初始化工具建立新帳號，Vercel 執行網站時不需設定。
不要在 Vercel 設定 `SDGS_DB_PATH`。Vercel 會提供 `VERCEL=1`，程式據此要求完整 Turso 設定。
Preview 如需獨立測試資料，請使用另外的 Turso 測試資料庫並先初始化。

在 Settings → Build and Deployment 確認：

| 設定 | 值 |
| --- | --- |
| Framework Preset | FastAPI |
| Root Directory | 原始碼根目錄（有 `main.py` 與 `requirements.txt`） |
| Build Command / Output Directory / Install Command | 使用框架預設，不沿用舊前端或 Docker 指令 |
| Python | `.python-version` 指定 3.12 |

`pyproject.toml` 指定 `main:app`；`vercel.json` 設定 FastAPI 與 60 秒函式期限。
`app/main.py` 掛載 `/static`，保留既有前端相對 API 路徑。
不需要 SPA 全域 rewrite，也不需要將所有請求改寫至 `/api/index.py`。

## 4. 部署

若既有專案已連結 GitHub，在 Settings → Git 確認連結的是
`vinnyhuangipuregreen/sdgs-matching-game` 及實際 Production Branch，再將這份原始碼推送至該分支。
壓縮檔不含 `.git`，可將解壓縮內容複製至既有 Git checkout 後提交。

也可以從專案根目錄使用官方 CLI：

```powershell
npx vercel@latest login
npx vercel@latest link --scope ipuregreen --project sdgs-matching-game
npx vercel@latest deploy --prod --scope ipuregreen
```

先完成初始化及 Vercel 環境變數設定再部署。修改環境變數後，需要重新部署才會套用。

## 5. 上線驗證

使用 Vercel 實際提供的 Production URL，確認：

1. `/healthz` 回傳 `{"status":"ok","database":"turso"}`。
2. 首頁正常載入，學習手冊顯示 17 目標與 169 細項，四種模式均可開始。
3. 完成一局後，排行榜與後台可看到該筆紀錄。
4. `/admin` 能登入、查看統計、編輯題目與設定，匯出 CSV 具有正確資料欄位。
5. 重新部署後，排行榜與修改的設定仍存在；有效的管理員憑證可跨執行個體使用。

初始化不在冷啟動執行，啟動會檢查所需資料表。遇到 `no such table` 請執行步驟 2；
遇到 401 請確認 Database Auth Token 權限與有效期。雲端資料庫錯誤不會退回 SQLite。

## 驗證範圍

本地自動化測試涵蓋 SQLite 與模擬 Turso HTTP 協定、API、四種模式、CSV、管理員憑證、原子批次回復與 SQLite 移轉。
沒有雲端登入及金鑰時，這些測試無法取代 Vercel 建置與真實 Turso 的上線驗證。

官方參考：[Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi)、
[Vercel Python](https://vercel.com/docs/functions/runtimes/python)、
[Turso SQL over HTTP](https://docs.turso.tech/sdk/http/reference)。
