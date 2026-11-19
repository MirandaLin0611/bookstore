# BookPebble 關鍵字搜尋更新

本包來自程式碼版本 `cc8f058`，正式網址維持 https://bookpebble.yhlin06.workers.dev/ 。

支援直接搜尋「天馬行空」「腦洞大開」「有創意」等想法，或輸入「有創意 水彩」找同時符合的書。不需先打開篩選器。本次更新不需要執行 Supabase SQL。

1. [下載本次新版 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-keyword-search-20261119.zip)。
2. 登入 [Cloudflare](https://dash.cloudflare.com/) → **Workers & Pages** → **bookpebble** → **Deployments** → **New deployment**。
3. 上傳這份 ZIP 並部署，網站重新整理後，搜尋框應顯示「試試『天馬行空』、書名或作者」。
4. 輸入「腦洞大開」，可看到「也會找：想像與創作」。目前書庫沒有相應資料時顯示 0 本是正常結果。

ZIP 最外層包含 `index.html`、`styles.css`、`config.js` 和 `assets/reading-garden.svg`。請使用本次關鍵字搜尋版本，較早的篩選更新包沒有包含這項功能。

完整說明：[關鍵字搜尋](https://github.com/MirandaLin0611/bookstore/blob/cc8f058/docs/keyword-search.md)。
