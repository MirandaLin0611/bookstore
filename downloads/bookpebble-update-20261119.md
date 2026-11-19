# BookPebble 篩選與書單更新

本包來自程式碼版本 `cbb9560`。網站正式網址維持 https://bookpebble.yhlin06.workers.dev/ 。

1. 先開啟 [資料庫補丁全文](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/patch2.sql)，複製全部內容。
2. 登入 [Supabase](https://supabase.com/dashboard) → 開啟原本專案 → **SQL Editor** → **New query** → 貼上 → **Run**，確認 **Success**。不需重跑 schema.sql。
3. [下載新版網站 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-update-20261119.zip)。
4. 登入 [Cloudflare](https://dash.cloudflare.com/) → **Workers & Pages** → **bookpebble** → **Deployments** → 選擇上傳靜態檔案／建立新部署，上傳這份 ZIP 並部署。
5. 網站重新整理後，確認情境篩選以視窗開啟、底部有「全部繪本」、階段有「幼幼班」，畫風與特色有多種選項。

ZIP 最外層只有 `index.html`、`styles.css`、`config.js` 和 `assets/reading-garden.svg`；沒有包入 SQL 或文件。先套用資料庫補丁，再上傳網站。

完整說明：[本次更新步驟](https://github.com/MirandaLin0611/bookstore/blob/cbb9560/docs/browse-update.md)。

ZIP SHA-256：`87089b4ef71ada8d4907a39c40e95983fce2ed7424ef804354295900d7a56acf`。
