// 資料庫連線設定
// Project URL 與 Publishable key 是設計給網頁前端公開使用的，資料安全由資料庫的權限規則（RLS）保護。
// 注意：絕對不要把 Secret key（sb_secret_ 開頭）放在這裡。
window.APP_CONFIG = {
  // Supabase 的 Magic Link 與 Confirm signup 信件模板都加入 {{ .Token }} 後，才改為 true。
  EMAIL_CODE_LOGIN: false,
  SUPABASE_URL: "https://zqxgkzjotgjxvnarnrvf.supabase.co",
  SUPABASE_KEY: "sb_publishable_Yys_iAqYgBIVzxNNxae6AA_sX4JMgKY"
};
