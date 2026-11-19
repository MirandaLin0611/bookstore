# BookPebble：手機快速回訪與文字草稿

完整更新包來自 `0dc102eee52b6d5349dee7f0def2eb957943d960`，包含先前的書籍編輯、集氣文案、搜尋及篩選功能。

## 更新方式：這次不用 SQL

1. [下載完整網站 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-mobile-20261119.zip)。
2. [Cloudflare](https://dash.cloudflare.com/) → Workers & Pages → bookpebble → Deployments → New deployment → 上傳這份 ZIP 並部署。
3. 重新整理 https://bookpebble.yhlin06.workers.dev/ ，手機底部應出現「找書／記心得／我的書架」，首頁有「加入主畫面」說明。

## iPhone 放到手機桌面

1. 用 Safari 開啟 https://bookpebble.yhlin06.workers.dev/ 。如果從 Threads 或 LINE 進來，請先改用 Safari，或複製網址貼進 Safari。
2. 點分享按鈕（方框上有向上箭頭）→「加入主畫面」。找不到時往下滑或選「更多」。
3. 若出現「以網頁 App 開啟」，將它開啟，再按「加入」。
4. 從新出現的繪本圖示開啟。如需登入，可在主畫面版本輸入信中的驗證碼，確保登入的是這個入口。

Android 則用 Chrome → 右上角「⋮」→「新增至主畫面」或「安裝應用程式」。瀏覽器選單依系統版本略有不同，實際加入仍需在手機上操作。

## 隨手記錄

點底部「記心得」，登入後可先填書名和一點感想。文字及選項自動暫存在這個瀏覽器，關掉再開、同一帳號回來可續寫；按送出前不會公開。不同帳號使用各自的草稿。

照片不跨次保存，清除瀏覽器資料會移除草稿；不同手機、瀏覽器或主畫面版本可能不共用，尚未提供雲端草稿同步。書單讀取及投稿仍需網路。想先加入主畫面者，建議從主畫面版本開始記錄。

「我的書架」直接查看收藏，「找書」返回全部繪本，兩者都會清除先前搜尋及篩選，避免誤以為書籍不見。新版本未新增推播或自動寄送集單郵件。

隔離瀏覽器流程測試 70 項通過，另確認舊分頁關閉不覆蓋另一分頁的新草稿；8 種手機與桌面畫面通過 axe WCAG A/AA 檢查。未寫入正式資料庫、寄送登入信或代替使用者安裝手機主畫面。
