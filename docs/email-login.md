# Email 登入、不同裝置與暱稱

## 使用方式

登入只需要 Email。暱稱在登入後的帳號設定中儲存，之後從 `profiles` 讀回，不需要每次重填。新帳號尚未設定時使用「匿名家長」。

登入連結會登入「實際開啟連結的瀏覽器」。手機點擊不會使電腦登入，不同裝置也不會自動交換憑證。同一個瀏覽器的相同網站分頁，則透過 `storage` 事件、返回分頁或視窗的檢查來更新登入及登出狀態。

## 啟用在電腦輸入信中驗證碼

Supabase 的 Email OTP 與 Magic Link 使用同一個發信 API。信件模板需包含 `{{ .Token }}`，收到的信才會顯示數字驗證碼；前端無法用 Publishable key 修改信件模板。

1. 開啟 Supabase 專案 → Authentication → Email Templates（部分介面在 Emails → Templates）。
2. 在 **Magic Link** 的信件本文加入 `<p>你的登入驗證碼：{{ .Token }}</p>`，保留原有的 `{{ .ConfirmationURL }}` 登入連結，然後儲存。
3. 在 **Confirm signup** 也加入相同的驗證碼區塊，保留原有連結並儲存，讓第一次註冊也能用驗證碼。
4. 可使用 [完整信件模板](../supabase/email-login.html) 替換這兩個模板的本文；請確認原本需要的內容已保留。
5. 兩個模板都完成後，把 `config.js` 的 `EMAIL_CODE_LOGIN` 設為 `true` 再發布。若尚未設定，保持 `false`，網站會維持登入連結方式，並清楚說明應在想登入的裝置開信。

不需要修改資料庫、重跑 SQL 或更換公開連線金鑰。

啟用後的操作是：電腦填 Email → 手機看信中的驗證碼 → 回電腦輸入。請勿先在手機點登入連結，因為同封信的連結及驗證碼擇一使用。已使用、過期或輸入錯誤會顯示提示，可重新寄信。

網站在成功寄信後提供 60 秒的重寄倒數。真正的驗證、到期及寄送頻率限制仍由 Supabase 執行；前端不會儲存數字驗證碼，也不會將登入 token 放入跨裝置共享資料表。

登入與登出切換時，舊的使用者查詢或 token 更新不能覆寫較新的狀態；同頁面多個請求同時遇到 token 到期，只會共用一次更新請求。

## 驗證

瀏覽器回歸測試完全攔截驗證與資料庫請求，使用測試金鑰及測試使用者，不會寄送真實信件或寫入正式資料庫。

```sh
python -m pip install playwright
python -m playwright install chromium
python -m unittest discover -s tests -v
```

已有 Chromium 時也可設定 `PLAYWRIGHT_CHROMIUM_EXECUTABLE`。測試涵蓋 Email 請求、暱稱儲存及還原、正確與錯誤驗證碼、重寄及改 Email、連結回呼清除 token、同瀏覽器登入／登出同步、不同瀏覽器隔離、token 更新併發及登出競態。

模板啟用後，仍需用真實信箱各測試一次既有帳號與新帳號，確認登入信確實顯示驗證碼，且未點擊連結時可在電腦完成驗證。

參考：[Supabase Passwordless email sign-in](https://supabase.com/docs/guides/auth/auth-email-passwordless)、[Email templates](https://supabase.com/docs/guides/auth/auth-email-templates)。
