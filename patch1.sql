-- 補丁 1：請在 schema.sql 成功執行之後，到 SQL Editor 再執行一次這份
-- 內容：投稿人建議的年齡／階段、核准時自動轉成第一票、管理者清除檢舉、資料表存取授權

-- 1) 投稿時填的建議年齡與階段（核准公開後，自動變成投稿人的那一票）
alter table public.books
  add column if not exists suggested_ages smallint[] not null default '{}'
    check (suggested_ages <@ array[0,1,2,3,4,5,6,7,8,9,10,11,12]::smallint[]),
  add column if not exists suggested_stages text[] not null default '{}'
    check (suggested_stages <@ array['小班','中班','大班','數字學習','ABC學習','同儕關係','情緒管理','睡前共讀','生活習慣','親子互動']);

create or replace function public.seed_vote_on_publish()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status = 'published' and old.status is distinct from 'published'
     and cardinality(new.suggested_ages) + cardinality(new.suggested_stages) >= 1 then
    insert into public.book_votes (book_id, user_id, ages, stages)
    values (new.id, new.submitted_by, new.suggested_ages, new.suggested_stages)
    on conflict do nothing;
  end if;
  return new;
end $$;

drop trigger if exists on_book_published on public.books;
create trigger on_book_published
  after update on public.books
  for each row execute function public.seed_vote_on_publish();

-- 2) 管理者可以清除檢舉紀錄
drop policy if exists "reports admin delete" on public.comment_reports;
create policy "reports admin delete" on public.comment_reports for delete to authenticated
  using (public.is_admin());

-- 3) 明確授權（資料安全仍由 RLS 規則把關，沒有規則允許的操作一律會被拒絕）
grant usage on schema public to anon, authenticated;
grant select on public.books, public.comments, public.group_buys, public.profiles to anon;
grant select, insert, update, delete on
  public.books, public.profiles, public.user_prefs, public.book_votes, public.comments,
  public.comment_reports, public.helpful, public.favorites, public.reading_log,
  public.group_buys, public.group_buy_interests, public.group_buy_responses
  to authenticated;
grant select on public.notification_outbox to authenticated;
grant execute on function public.is_admin() to anon, authenticated;
grant execute on function public.open_group_buy(uuid, text, date, text, text) to authenticated;
