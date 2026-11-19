# 繪本小聚場

家長分享、篩選繪本的網站：英文／中文繪本、家長投票決定適合的年齡與階段、陪讀指南、台灣作家標示、收藏與閱讀紀錄、部分書籍開放集氣開團（不處理金流）。

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `index.html` | 網站頁面與互動邏輯 |
| `styles.css` | 網站排版、手機版與介面樣式 |
| `assets/reading-garden.svg` | 首頁共讀插畫（本地檔案，不依賴外部圖床） |
| `config.js` | 資料庫連線設定（Project URL 與 Publishable key，可公開） |
| `schema.sql` | 資料庫結構與權限規則，新資料庫先執行 |
| `patch1.sql` | 補丁，在 schema.sql 之後執行 |
| `patch2.sql` | 擴充「幼幼班」階段，既有資料庫也需執行一次 |

## 本機預覽

在專案資料夾執行 `python -m http.server 8000`，開啟 `http://localhost:8000`。不需要安裝前端套件或編譯。資料讀取使用 `config.js` 指定的 Supabase；本機測試登入前，需在 Supabase 設定允許的重新導向網址。

部署時保留 `index.html`、`styles.css`、`config.js` 與 `assets/` 的相對位置；不需上傳 SQL、文件或測試。現行正式站是 [BookPebble](https://bookpebble.yhlin06.workers.dev/)，使用 Cloudflare Workers 靜態檔案上傳；GitHub 程式碼更新不會自動更新這個網址。啟動、資料庫與上傳步驟見 [SETUP.md](SETUP.md)。

「幼幼班」投稿及投票需要 `patch2.sql`；既有資料庫若尚未執行，請先套用這份補丁，不要重跑 `schema.sql`。已執行者不需重跑。本次關鍵字搜尋更新不需新增 SQL。階段更新說明見 [篩選與書單更新步驟](docs/browse-update.md)。

登入只需 Email，暱稱在登入後的帳號設定儲存。跨裝置驗證碼的信件模板設定及登入回歸測試，見 [Email 登入說明](docs/email-login.md)。

生活情境共六組、32 種，篩選與投稿共用相同選項。分類參考、別名對照及資料處理方式，見 [生活情境分類](docs/situation-filters.md)。

篩選使用獨立視窗，底部固定提供結果數及「全部繪本」入口。階段包含幼幼班；畫風與特色提供 12 種固定選項，另保留既有自訂標籤，投稿也能勾選。

搜尋也接受家長常用的想法，例如「天馬行空／腦洞大開／有創意」都會找想像與創作相關內容；「有創意 水彩」則找同時符合兩者的書。不需先操作篩選器。搜尋範圍、同義詞與上傳新版的步驟見 [關鍵字搜尋說明](docs/keyword-search.md)。

## 安全提醒

`config.js` 只能放 Publishable key。**Secret key（sb_secret_ 開頭）絕對不要放進任何檔案或上傳到 GitHub。**
