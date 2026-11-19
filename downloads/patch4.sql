-- 新增每本書的集氣補充說明，不變更集氣人數、發布狀態或既有開團備註。
begin;

do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'books' and column_name = 'collection_note'
  ) then
    alter table public.books add column collection_note text not null default ''
      check (char_length(collection_note) <= 600);

    -- 這本現有英文繪本的初始補充文字；後續可在集單管理自由修改或清空。
    update public.books
    set collection_note = '本書英文版目前多處缺貨，我們將嘗試與國外出版社洽詢；能否取得書籍並順利成團，仍需等待對方回覆。'
    where id = '808d047c-ebb9-4974-a028-ce6d4142bd41';
  end if;
end;
$$;

notify pgrst, 'reload schema';
commit;
