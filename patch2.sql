-- 補丁 2：既有資料庫執行一次，讓投稿與家長投票都接受「幼幼班」。
-- 在 schema.sql 與 patch1.sql 已成功執行的專案上使用。
-- 只擴充兩個檢查條件，不修改既有書籍、投票、權限或登入設定。
begin;

alter table public.books
  drop constraint if exists books_suggested_stages_check,
  add constraint books_suggested_stages_check
    check (suggested_stages <@ array[
      '幼幼班','小班','中班','大班','數字學習','ABC學習',
      '同儕關係','情緒管理','睡前共讀','生活習慣','親子互動'
    ]);

alter table public.book_votes
  drop constraint if exists book_votes_stages_check,
  add constraint book_votes_stages_check
    check (stages <@ array[
      '幼幼班','小班','中班','大班','數字學習','ABC學習',
      '同儕關係','情緒管理','睡前共讀','生活習慣','親子互動'
    ]);

commit;
