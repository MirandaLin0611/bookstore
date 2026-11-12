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

## 本機預覽

在專案資料夾執行 `python -m http.server 8000`，開啟 `http://localhost:8000`。不需要安裝前端套件或編譯。資料讀取使用 `config.js` 指定的 Supabase；本機測試登入前，需在 Supabase 設定允許的重新導向網址。

部署至 GitHub Pages 時，請保留 `index.html`、`styles.css`、`config.js` 與 `assets/` 的相對位置。既有資料庫不需為這次介面改版重跑 SQL。

登入只需 Email，暱稱在登入後的帳號設定儲存。跨裝置驗證碼的信件模板設定及登入回歸測試，見 [Email 登入說明](docs/email-login.md)。

生活情境共六組、32 種，篩選與投稿共用相同選項。分類參考、別名對照及資料處理方式，見 [生活情境分類](docs/situation-filters.md)。

## 安全提醒

`config.js` 只能放 Publishable key。**Secret key（sb_secret_ 開頭）絕對不要放進任何檔案或上傳到 GitHub。**
