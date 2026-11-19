# BookPebble 第一版：先累積共讀內容

本完整更新包來自 `b20c316`，移除書籍詳情的博客來、Amazon 購書連結，以及頁尾的購書、聯盟提示。保留分享、找書、收藏、閱讀紀錄、交流，以及主辦人針對特定書籍開放的集單與開團功能。

1. [下載完整新版 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-community-20261119.zip)。
2. Cloudflare → **Workers & Pages → bookpebble → Deployments → New deployment**，上傳這份 ZIP 並部署。
3. 重新整理網站，開啟書籍詳情，確認不再顯示外部書店購書按鈕。

本包已包含前面的搜尋、篩選、幼幼班與畫風修正，只需上傳這一份；不需修改 Supabase 或重跑 SQL，網址維持不變。

ZIP 最外層包含 `index.html`、`styles.css`、`config.js` 及 `assets/reading-garden.svg`。48 項既有測試通過，另以隔離流程確認集單、開團及跟團回覆；沒有寫入正式資料。
