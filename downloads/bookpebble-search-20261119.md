# BookPebble：不限情境的關鍵字搜尋

此完整更新包來自 `17414cd`，包含先前的篩選、幼幼班、畫風與搜尋修正。

任意關鍵字都會比對書籍文字及自訂標籤，不限預設情境。搜尋範圍包含書名、作者、心得、孩子反應、陪讀建議、注意事項及書籍標示。新投稿或修改的文字會隨書庫載入自動納入搜尋，不必為新詞增加情境或改程式。

1. [下載本次完整 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-search-20261119.zip)。
2. Cloudflare → **Workers & Pages → bookpebble → Deployments → New deployment**，上傳這份 ZIP 並部署。
3. 重新整理網站，搜尋框應顯示「搜尋書名、作者或任意關鍵字」。可從已上架書籍挑一個未列在情境清單中的詞測試。

本次不需要改 Supabase，也不需要新增 AI 或後端服務。只需上傳本包一次；日後新增投稿內容不需重新部署。

ZIP 最外層為 `index.html`、`styles.css`、`config.js` 及 `assets/reading-garden.svg`。完整說明見 [關鍵字搜尋文件](https://github.com/MirandaLin0611/bookstore/blob/17414cd/docs/keyword-search.md)。
