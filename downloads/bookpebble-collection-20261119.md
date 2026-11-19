# BookPebble：集氣說明更新

本完整更新包來自 `2673b450d593b62ff9fe6e00009c0244365a1f0e`，包含先前搜尋、篩選、幼幼班、畫風、移除購書導流及已發布推薦編輯功能。

## 更新順序

1. 開啟 [patch4.sql 全文](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/patch4.sql)，複製全部內容。
2. [Supabase](https://supabase.com/dashboard) → 原本專案 → **SQL Editor → New query** → 貼上 → **Run**，確認 **Success**。已完成上一版編輯功能更新者，本次只執行 patch4.sql，不要重跑 schema.sql。尚未套用 patch3.sql 者需先完成該補丁。
3. [下載完整網站 ZIP](https://raw.githubusercontent.com/MirandaLin0611/bookstore/cloudflare-download-20261119/downloads/bookpebble-collection-20261119.zip)。
4. [Cloudflare](https://dash.cloudflare.com/) → **Workers & Pages → bookpebble → Deployments → New deployment** → 上傳 ZIP 並部署。
5. 重新整理 https://bookpebble.yhlin06.workers.dev/ ，開啟《If you cry like a fountain》，確認集氣區塊出現以下兩段文字。

## 通用說明

> 集氣僅為意願登記，不保證成團。達到目標人數後，主辦人會與出版社洽詢供書及合作方式；有進一步消息時，將以電子郵件通知參與集氣的家長。

## 本書補充

> 本書英文版目前多處缺貨，我們將嘗試與國外出版社洽詢；能否取得書籍並順利成團，仍需等待對方回覆。

其他書共用通用說明，需要時再補上各自的供書情況。管理者登入 → 右上角帳號 →「集單與開團管理」→ 找到書籍 →「本書集氣補充說明」→「儲存集氣說明」。最多 600 字，留空即只顯示通用說明，之後不用再改程式或重部署。

說明只在集氣期間顯示；達標仍需洽談，不會自動開團。原書籍、會員、集氣人數、狀態及開團備註保留。補丁可重複執行，不會蓋掉後台已修改或清空的說明。

目前網站會建立站內開團資訊及通知紀錄，但尚未串接集單通知信的自動寄送；電子郵件需由主辦人另外寄送。登入信的 SMTP 設定不會自動寄出集單進度。
