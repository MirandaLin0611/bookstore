# BookPebble 本次更新

## 使用者會看到的變化

1. 情境與詳細篩選改成獨立視窗，底部固定提供「查看 N 本繪本」及「全部繪本」，不用捲過整張選項清單才能找到書。
2. 書單上方新增「全部繪本」；首頁圖示、「探索繪本」及空收藏的探索按鈕也能清除篩選，回到所有已公開書籍。
3. 階段補上「幼幼班」，篩選、投稿和家長投票都可使用。
4. 畫風與特色提供 12 個固定選項及既有自訂標籤，投稿時也可勾選；沒有符合標籤的書會顯示 0 本，不會替既有書籍自動補分類。

## 已有網站的更新順序

必須先更新資料庫，再上傳網站，以免「幼幼班」投稿或投票被舊規則拒絕。

1. 登入 [Supabase Dashboard](https://supabase.com/dashboard)，開啟目前網站使用的專案（Project URL 為 `https://zqxgkzjotgjxvnarnrvf.supabase.co`）。
2. 左側 **SQL Editor** → **New query**，貼上根目錄 [patch2.sql](../patch2.sql) 全文 → **Run**，確認顯示 **Success**。只需這份補丁，不要重新執行 `schema.sql`。
3. 登入 [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **bookpebble** → **Deployments** → 選擇上傳新版靜態檔案／建立新部署。
4. 上傳新版網站 ZIP，部署至既有 Worker 的正式環境。ZIP 最外層須是 `index.html`、`styles.css`、`config.js` 和 `assets/`。
5. 開啟 `https://bookpebble.yhlin06.workers.dev/` 重新整理；若仍看到舊畫面，可使用無痕分頁確認。

補丁只擴充 `books.suggested_stages` 與 `book_votes.stages` 的合法值，不修改會員、書籍、收藏、投票紀錄、登入信或權限規則；重複執行仍可完成。僅更新 GitHub 程式碼不會自動部署至 Cloudflare。

## 驗證

- `python -m unittest discover -s tests -v`：使用模擬服務檢查登入、收藏、投稿、情境篩選、總覽返回、畫風別名和幼幼班投稿／投票。
- 手機直向、橫向及桌面：確認篩選底部操作持續可見、沒有整頁橫向溢出，Escape、背景及關閉按鈕可關閉視窗並恢復焦點。
- 遷移另在隔離的 PostgreSQL 引擎驗證：舊規則拒絕幼幼班、補丁後接受、核准投稿會建立幼幼班建議、錯誤階段仍拒絕、既有資料與 33 條權限政策不變。

自動測試不會寄出登入信，也不會寫入正式資料庫。正式環境的補丁和 Cloudflare 上傳需由具備後台存取權的帳號完成。
