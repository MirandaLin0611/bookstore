# 編輯推薦與集單開團

## 編輯已發布的推薦

1. 使用原本投稿的帳號登入；管理者也能協助修改其他投稿。
2. 開啟該書的推薦詳情，在書名下方點「編輯我的推薦」或「編輯繪本推薦」。
3. 修改書名、作者、語言、心得、孩子反應、主題與畫風、台灣作者標示、注意事項或陪讀建議。
4. 照片可保留、移除、新增或設為書封，最多四張。保留的照片不會重新上傳；移除照片不會刪除 Storage 原檔。
5. 按「儲存修改」後回到同一本書的詳情。

修改使用原書籍 ID，不會重建一筆投稿，因此收藏、閱讀紀錄、留言、其他家長投票與集單紀錄都保留。原發布狀態不變：已公開的仍公開，審核中或已下架的也不會被此功能自行公開。

年齡與階段建議由原先資料及家長投票保留，不在內容編輯表單修改。新推薦草稿與編輯表單彼此獨立；取消編輯會回到書籍詳情。儲存失敗會保留表單內容；若另一個視窗已更新，請先複製要保留的文字，再重新開啟編輯，避免覆蓋他人的修正。

## 集單與開團入口

- 管理者：點右上角已登入帳號 →「集單與開團管理」。也可在某本已公開書籍的詳情點「管理集單與開團」，直接定位到該書。
- 原本的「頁尾管理後台 → 集氣管理」入口保留。
- 在書籍旁勾選「開放集氣」，可調整目標人數。一般家長此時才會在該書詳情看到集氣入口。
- 達標後，由主辦人填寫團購價、取貨方式、截止日等資訊，再按「發出開團通知」。參與者可在「通知」分頁決定跟團與數量。
- 一般會員沒有管理入口；目前登入帳號需在 `public.admins` 名單裡。這次更新不會自動授予任何人管理權限。

## 已有網站的更新順序

1. [Supabase Dashboard](https://supabase.com/dashboard) → 原本的專案 → **SQL Editor → New query**。
2. 貼上 [patch3.sql](../patch3.sql) 全文 → **Run**，確認 **Success**。已完成先前更新的網站只需這份補丁，不要重跑 `schema.sql`。
3. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages → bookpebble → Deployments → New deployment**。
4. 上傳本次完整網站 ZIP 並部署，再重新整理 https://bookpebble.yhlin06.workers.dev/ 。

補丁只新增 `edit_book_content` 函式及執行權限，保留既有 33 條 RLS 政策；只有投稿人與管理者能呼叫。只接受明列的書籍內容欄位，拒絕變更擁有者、書籍 ID、發布狀態、建立時間、原始年齡與階段建議。新增照片需屬於目前帳號，也會檢查書籍是否已被其他視窗更新。補丁可重複執行，不改寫現有書籍或會員資料。

正式資料庫的補丁需由具備 Supabase 後台權限的帳號執行；GitHub 與 Cloudflare 的前端更新本身不會新增資料庫函式。單純上傳新版前端而未執行補丁時，按儲存會提示編輯功能尚未啟用。

## 驗證

瀏覽器測試（使用隔離的模擬服務，不會寫入正式資料或寄信）：

    python -m unittest discover -s tests -v

SQL 權限與資料保留測試使用真正的 PostgreSQL 引擎 PGlite。開發者可將測試套件安裝在臨時資料夾，不影響靜態網站：

    npm install --prefix /tmp/bookpebble-db-tests --ignore-scripts --no-audit --no-fund @electric-sql/pglite@0.5.16
    PGLITE_MODULE=/tmp/bookpebble-db-tests/node_modules/@electric-sql/pglite/dist/index.js node tests/test_edit_book_sql.mjs

SQL 測試涵蓋投稿人、管理者、其他會員、未登入者、受保護欄位、照片歸屬、格式及長度限制、過期修改、重複套用補丁，以及收藏、留言、投票、閱讀與集單資料保留。
