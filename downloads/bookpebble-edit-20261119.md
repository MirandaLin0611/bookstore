# BookPebble：編輯已發布內容與集單管理入口

本完整更新包來自 `3b2b64a`，包含先前搜尋、篩選、幼幼班、畫風及移除購書導流的修正。

## 更新順序：先資料庫，再上傳網站

1. 開啟 [patch3.sql 全文](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/patch3.sql)，複製全部內容。
2. [Supabase](https://supabase.com/dashboard) → 原本專案 → **SQL Editor → New query** → 貼上 → **Run**，確認 **Success**。只執行這份補丁，不重跑 schema.sql 或先前補丁。
3. [下載本次完整網站 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-edit-20261119.zip)。
4. [Cloudflare](https://dash.cloudflare.com/) → **Workers & Pages → bookpebble → Deployments → New deployment**，上傳這份 ZIP 並部署。
5. 重新整理 https://bookpebble.yhlin06.workers.dev/ ，以原本投稿帳號登入。

## 更新後的入口

- 編輯：開啟書籍詳情 → 書名下方「編輯我的推薦」或「編輯繪本推薦」→ 修改 →「儲存修改」。投稿人可改自己的內容，管理者也能協助修改。
- 集單：管理者點右上角帳號 →「集單與開團管理」；或從書籍詳情點「管理集單與開團」。勾選「開放集氣」，達到目標人數後可發出開團通知。
- 舊入口「頁尾管理後台 → 集氣管理」保留。看不到管理入口時，請確認目前登入的帳號具有管理者資格。

編輯保留原本收藏、留言、閱讀、投票、集單與發布狀態；原有年齡、階段建議不在內容編輯表單修改。這次補丁不會授予新的管理者身分，也不會改寫既有書籍或會員資料。

完整說明：[編輯與集單操作](https://github.com/MirandaLin0611/bookstore/blob/3b2b64a/docs/editing-and-groups.md)。
