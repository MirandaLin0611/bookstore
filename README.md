# 繪本小聚場

家長分享、篩選繪本的網站：英文／中文繪本、家長投票決定適合的年齡與階段、陪讀指南、台灣作家標示、收藏與閱讀紀錄、部分書籍開放集氣開團（不處理金流）。

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `index.html` | 整個網站（單一檔案） |
| `config.js` | 資料庫連線設定（Project URL 與 Publishable key，可公開） |
| `db/schema.sql` | 資料庫結構與權限規則，先執行 |
| `db/patch1.sql` | 補丁，在 schema.sql 之後執行 |

## 安全提醒

`config.js` 只能放 Publishable key。**Secret key（sb_secret_ 開頭）絕對不要放進任何檔案或上傳到 GitHub。**
