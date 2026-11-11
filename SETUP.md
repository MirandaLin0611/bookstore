# 上線步驟

## 一、資料庫（Supabase）

1. SQL Editor 先執行 `db/schema.sql`，再執行 `db/patch1.sql`（兩份都要顯示 Success）。
2. 到網站用 Email 登入一次，再回 SQL Editor 執行下面這段（換成你的 Email），把自己設為管理者：

```sql
insert into public.admins (user_id)
select id from auth.users where email = 'you@example.com';
```

## 二、放上 GitHub 並開啟網站（全程用瀏覽器，不需要指令）

1. 登入 github.com → 右上角 `+` → New repository，取名（例如 picture-books），選 Public，建立。
2. 在新倉庫頁面點「uploading an existing file」，把這個資料夾裡的**所有檔案與 db 資料夾**拖進去，按 Commit changes。
3. 倉庫 Settings → Pages → Source 選 `Deploy from a branch`，Branch 選 `main`、資料夾選 `/ (root)` → Save。
4. 等 1～2 分鐘，頁面會顯示網站網址，格式像 `https://你的帳號.github.io/picture-books/`。

> 也可以不用 GitHub：把 `index.html` 和 `config.js` 直接拖到 Cloudflare Pages 或 Netlify 的上傳頁面，同樣會得到網址。

## 三、讓登入連結能導回你的網站

網站網址出來後，到 Supabase → Authentication → URL Configuration：

- **Site URL** 填你的網站網址
- **Redirect URLs** 也加入同一個網址

沒做這一步，家長點信箱裡的登入連結時會被導到錯誤的位置。

## 四、驗證

1. 開網站 → 登入／註冊 → 輸入 Email → 到信箱點連結。
2. 分享一本書（投稿）→ 到管理後台核准 → 回首頁確認有顯示。
3. 用另一個瀏覽器（或無痕視窗）確認沒登入也能瀏覽。
