# 上線步驟

## 一、資料庫（Supabase）

1. **全新資料庫**：SQL Editor 依序執行專案根目錄的 `schema.sql`、`patch1.sql`、`patch2.sql`、`patch3.sql`、`patch4.sql`，各自顯示 Success。
   **已經正常運作且已完成書籍編輯更新的資料庫**：本次只執行 `patch4.sql`，新增每本書的集氣補充說明；不要重跑 `schema.sql`。若尚未套用 `patch3.sql`，先完成該補丁。
2. 到網站用 Email 登入一次，再回 SQL Editor 執行下面這段（換成你的 Email），把自己設為管理者：

```sql
insert into public.admins (user_id)
select id from auth.users where email = 'you@example.com';
```

## 二、放上 GitHub 並開啟網站（全程用瀏覽器，不需要指令）

1. 登入 github.com → 右上角 `+` → New repository，取名（例如 picture-books），選 Public，建立。
2. 在新倉庫頁面點「uploading an existing file」，上傳專案檔案，保留 `assets` 資料夾，按 Commit changes。SQL 檔案位於根目錄，沒有 `db` 資料夾。
3. 倉庫 Settings → Pages → Source 選 `Deploy from a branch`，Branch 選 `main`、資料夾選 `/ (root)` → Save。
4. 等 1～2 分鐘，頁面會顯示網站網址，格式像 `https://你的帳號.github.io/picture-books/`。

### 現行正式站：Cloudflare Workers

目前網址為 `https://bookpebble.yhlin06.workers.dev/`，使用靜態檔案直接上傳。更新此站時：

1. 先完成本版需要的資料庫補丁。
2. 準備 ZIP：最外層須有 `index.html`、`styles.css`、`config.js` 及 `assets/reading-garden.svg`；不要再包一層專案資料夾。
3. 登入 [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → 開啟既有的 **bookpebble** → **Deployments** → **Upload assets / New deployment**（按鈕文字依介面版本可能不同）。
4. 上傳 ZIP、確認並部署到正式環境。使用既有 Worker，不需重新建立專案或更改網址。

只更新 GitHub 不會同步更新這個 Workers 網址。也可將這四個檔案／路徑部署至 Cloudflare Pages 或其他靜態網站服務。

## 三、讓登入連結能導回你的網站

網站網址出來後，到 Supabase → Authentication → URL Configuration：

- **Site URL** 填你的網站網址
- **Redirect URLs** 也加入同一個網址

現行正式站兩處都應包含 `https://bookpebble.yhlin06.workers.dev/`。

沒做這一步，家長點信箱裡的登入連結時會被導到錯誤的位置。

### 在電腦輸入 Email 驗證碼

若要用手機收信、在電腦完成登入，需先讓 Supabase 信件模板顯示驗證碼，再開啟網站端的驗證碼入口。完整設定見 [Email 登入說明](docs/email-login.md)。未完成模板設定時，請保留 `config.js` 的 `EMAIL_CODE_LOGIN: false`。

## 四、驗證

1. 開網站 → 登入／註冊 → 輸入 Email → 在原本裝置輸入信件內的驗證碼；或在想登入的裝置開啟信件連結。
2. 分享一本書（投稿）→ 到管理後台核准 → 回首頁確認有顯示。
3. 用另一個瀏覽器（或無痕視窗）確認沒登入也能瀏覽。
4. 開啟「看全部生活情境」→ 選條件 →「查看 N 本繪本」→「全部繪本」，確認可回到所有已公開書籍。
5. 確認階段有「幼幼班」，投稿與書籍詳情的家長建議也能選；畫風與特色有多種選項。沒有符合標籤的書顯示 0 本是正常結果。
6. 以投稿人或管理者登入，開啟書籍詳情 → 編輯推薦 → 儲存，確認修改後仍是同一本書，原有收藏與投票保留。集單管理可從管理者帳號視窗或書籍詳情進入，詳見 [編輯與集單操作](docs/editing-and-groups.md)。
7. 管理者到「集單與開團管理」，填寫某本書的「本書集氣補充說明」並儲存。以未登入瀏覽器查看已開放集氣的書，確認通用說明及該書補充文字都出現；其他書不應顯示這段補充。留空則只顯示通用說明。

目前開團會建立站內通知及寄信待辦紀錄，但尚無集單通知信的自動寄送程式，通知信需由主辦人另行寄送。
