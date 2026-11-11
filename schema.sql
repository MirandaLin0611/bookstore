-- 繪本小聚場：Supabase 資料庫結構（含權限規則 RLS）
-- 使用方式：Supabase 專案 → SQL Editor → 貼上整份 → Run
-- 注意：此檔案尚未在真實的 Supabase 專案上執行過，第一次執行若有錯誤訊息，請把訊息貼給我修正。

-- ============ 帳號與管理者 ============
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text not null default '匿名家長' check (char_length(nickname) <= 12),
  created_at timestamptz not null default now()
);

-- 管理者名單：只能在 SQL Editor 手動新增，網站前端無法寫入
create table public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, nickname)
  values (new.id, coalesce(left(new.raw_user_meta_data->>'nickname', 12), '匿名家長'));
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 通知偏好（想用哪些管道收到開團通知）
create table public.user_prefs (
  user_id uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  channels text[] not null default '{email}' check (channels <@ array['email','line','messenger']),
  line_user_id text,
  updated_at timestamptz not null default now()
);

-- ============ 書籍 ============
create table public.books (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) between 1 and 120),
  author text not null default '' check (char_length(author) <= 120),
  lang text not null check (lang in ('中文', '英文')),
  is_taiwan boolean not null default false,          -- 作者或繪者其中一位是台灣人
  themes text[] not null default '{}',
  styles text[] not null default '{}',
  review text not null default '' check (char_length(review) <= 2000),
  kid_reaction text not null default '' check (char_length(kid_reaction) <= 300),
  warning text not null default '' check (char_length(warning) <= 300),
  guide_before text not null default '' check (char_length(guide_before) <= 500),
  guide_during text not null default '' check (char_length(guide_during) <= 500),
  guide_after text not null default '' check (char_length(guide_after) <= 500),
  photos text[] not null default '{}' check (cardinality(photos) <= 4),  -- 存 Storage 檔案路徑
  status text not null default 'pending' check (status in ('pending', 'published', 'hidden')),
  submitted_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now()
);

-- ============ 年齡與階段投票（每人每本書一票，可複選） ============
create table public.book_votes (
  book_id uuid not null references public.books(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  ages smallint[] not null default '{}'
    check (ages <@ array[0,1,2,3,4,5,6,7,8,9,10,11,12]::smallint[]),
  stages text[] not null default '{}'
    check (stages <@ array['小班','中班','大班','數字學習','ABC學習','同儕關係','情緒管理','睡前共讀','生活習慣','親子互動']),
  created_at timestamptz not null default now(),
  primary key (book_id, user_id),
  check (cardinality(ages) + cardinality(stages) >= 1)
);

-- ============ 留言與檢舉 ============
create table public.comments (
  id uuid primary key default gen_random_uuid(),
  book_id uuid not null references public.books(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  nickname text not null default '匿名家長' check (char_length(nickname) <= 12),
  child_age text not null default '' check (char_length(child_age) <= 10),
  body text not null check (char_length(body) between 5 and 200),
  status text not null default 'visible' check (status in ('visible', 'hidden')),
  created_at timestamptz not null default now()
);

create table public.comment_reports (
  comment_id uuid not null references public.comments(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (comment_id, user_id)
);

-- 同一則留言被 3 位不同家長檢舉，自動隱藏，等管理者處理
create or replace function public.auto_hide_reported_comment()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from public.comment_reports where comment_id = new.comment_id) >= 3 then
    update public.comments set status = 'hidden' where id = new.comment_id;
  end if;
  return new;
end $$;

create trigger on_comment_report
  after insert on public.comment_reports
  for each row execute function public.auto_hide_reported_comment();

-- ============ 有幫助、收藏、閱讀紀錄（個人資料，只有本人看得到） ============
create table public.helpful (
  book_id uuid not null references public.books(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (book_id, user_id)
);

create table public.favorites (
  book_id uuid not null references public.books(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (book_id, user_id)
);

create table public.reading_log (
  book_id uuid not null references public.books(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  read_on date not null default current_date,
  rating text not null default '喜歡' check (rating in ('很愛', '喜歡', '普通')),
  note text not null default '' check (char_length(note) <= 80),
  primary key (book_id, user_id)
);

-- ============ 集氣開團（只有管理者開放的書才有；不處理金流） ============
-- 管理者在這張表新增一列 = 該書開放集氣
create table public.group_buys (
  book_id uuid primary key references public.books(id) on delete cascade,
  target int not null default 10 check (target between 2 and 500),
  status text not null default 'collecting' check (status in ('collecting', 'open', 'closed')),
  price_text text not null default '' check (char_length(price_text) <= 100),
  deadline date,
  pickup_text text not null default '' check (char_length(pickup_text) <= 200),
  note text not null default '' check (char_length(note) <= 300),
  opened_at timestamptz
);

create table public.group_buy_interests (            -- 集氣
  book_id uuid not null references public.group_buys(book_id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (book_id, user_id)
);

create table public.group_buy_responses (            -- 跟團或不跟
  book_id uuid not null references public.group_buys(book_id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  decision text not null check (decision in ('join', 'skip')),
  qty smallint not null default 1 check (qty between 1 and 5),
  created_at timestamptz not null default now(),
  primary key (book_id, user_id)
);

-- 待發送的通知佇列：之後用 Edge Function 讀取並透過 Email／LINE 寄出
create table public.notification_outbox (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  book_id uuid not null references public.books(id) on delete cascade,
  kind text not null,
  channel text not null check (channel in ('email', 'line', 'messenger')),
  payload jsonb not null default '{}',
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

-- 管理者按「發出開團通知」時呼叫：更新開團資訊並替每位集氣者排入通知
create or replace function public.open_group_buy(
  p_book uuid, p_price text, p_deadline date, p_pickup text, p_note text
) returns int language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if not public.is_admin() then raise exception 'not allowed'; end if;
  if coalesce(p_price, '') = '' and coalesce(p_pickup, '') = '' then
    raise exception '請至少填團購價或取貨方式';
  end if;
  update public.group_buys
     set status = 'open', price_text = p_price, deadline = p_deadline,
         pickup_text = p_pickup, note = p_note, opened_at = now()
   where book_id = p_book and status = 'collecting';
  if not found then raise exception '這個團不是集氣中的狀態'; end if;
  insert into public.notification_outbox (user_id, book_id, kind, channel, payload)
  select i.user_id, p_book, 'group_open', unnest(coalesce(up.channels, array['email'])),
         jsonb_build_object('price', p_price, 'deadline', p_deadline, 'pickup', p_pickup, 'note', p_note)
    from public.group_buy_interests i
    left join public.user_prefs up on up.user_id = i.user_id
   where i.book_id = p_book;
  get diagnostics n = row_count;
  return n;
end $$;

-- ============ 公開的統計檢視（只有數字，不含任何個人資料） ============
create view public.book_age_votes as
  select v.book_id, a::int as age, count(*)::int as votes
    from public.book_votes v
    join public.books b on b.id = v.book_id and b.status = 'published',
         unnest(v.ages) as a
   group by v.book_id, a;

create view public.book_stage_votes as
  select v.book_id, s as stage, count(*)::int as votes
    from public.book_votes v
    join public.books b on b.id = v.book_id and b.status = 'published',
         unnest(v.stages) as s
   group by v.book_id, s;

create view public.book_voter_counts as
  select v.book_id, count(*)::int as voters
    from public.book_votes v
    join public.books b on b.id = v.book_id and b.status = 'published'
   group by v.book_id;

create view public.book_helpful_counts as
  select h.book_id, count(*)::int as helpful
    from public.helpful h
    join public.books b on b.id = h.book_id and b.status = 'published'
   group by h.book_id;

create view public.group_buy_counts as
  select i.book_id, count(*)::int as interested
    from public.group_buy_interests i
   group by i.book_id;

create view public.group_buy_totals as
  select r.book_id, coalesce(sum(r.qty) filter (where r.decision = 'join'), 0)::int as join_qty
    from public.group_buy_responses r
   group by r.book_id;

grant select on public.book_age_votes, public.book_stage_votes, public.book_voter_counts,
                public.book_helpful_counts, public.group_buy_counts, public.group_buy_totals
  to anon, authenticated;

-- ============ 權限規則（RLS）：沒有明確允許的，一律拒絕 ============
alter table public.profiles            enable row level security;
alter table public.admins              enable row level security;
alter table public.user_prefs          enable row level security;
alter table public.books               enable row level security;
alter table public.book_votes          enable row level security;
alter table public.comments            enable row level security;
alter table public.comment_reports     enable row level security;
alter table public.helpful             enable row level security;
alter table public.favorites           enable row level security;
alter table public.reading_log         enable row level security;
alter table public.group_buys          enable row level security;
alter table public.group_buy_interests enable row level security;
alter table public.group_buy_responses enable row level security;
alter table public.notification_outbox enable row level security;

-- profiles：大家看得到暱稱，只能改自己的
create policy "profiles read" on public.profiles for select using (true);
create policy "profiles update own" on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

-- admins：前端完全不可讀寫（沒有任何 policy），只能在 SQL Editor 操作

-- user_prefs：只有本人
create policy "prefs own" on public.user_prefs for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

-- books：已發布的大家看得到；本人看得到自己投稿的；管理者看全部
create policy "books read" on public.books for select
  using (status = 'published' or submitted_by = auth.uid() or public.is_admin());
create policy "books submit" on public.books for insert to authenticated
  with check (submitted_by = auth.uid() and status = 'pending');
create policy "books admin update" on public.books for update to authenticated
  using (public.is_admin()) with check (public.is_admin());
create policy "books admin delete" on public.books for delete to authenticated
  using (public.is_admin());

-- book_votes：登入者可對已發布的書投票、修改自己的票
create policy "votes read own" on public.book_votes for select to authenticated
  using (user_id = auth.uid() or public.is_admin());
create policy "votes insert" on public.book_votes for insert to authenticated
  with check (user_id = auth.uid()
    and exists (select 1 from public.books b where b.id = book_votes.book_id and b.status = 'published'));
create policy "votes update own" on public.book_votes for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "votes delete own" on public.book_votes for delete to authenticated
  using (user_id = auth.uid());

-- comments：大家看得到正常留言；本人看得到自己的；管理者看全部
create policy "comments read" on public.comments for select
  using (status = 'visible' or user_id = auth.uid() or public.is_admin());
create policy "comments insert" on public.comments for insert to authenticated
  with check (user_id = auth.uid() and status = 'visible'
    and exists (select 1 from public.books b where b.id = comments.book_id and b.status = 'published'));
create policy "comments delete" on public.comments for delete to authenticated
  using (user_id = auth.uid() or public.is_admin());
create policy "comments admin update" on public.comments for update to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- comment_reports：登入者可檢舉；只有管理者看得到檢舉紀錄
create policy "reports insert" on public.comment_reports for insert to authenticated
  with check (user_id = auth.uid());
create policy "reports admin read" on public.comment_reports for select to authenticated
  using (public.is_admin());

-- helpful / favorites / reading_log：只有本人
create policy "helpful own" on public.helpful for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "favorites own" on public.favorites for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "log own" on public.reading_log for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

-- group_buys：大家看得到；只有管理者能新增、修改、刪除
create policy "gb read" on public.group_buys for select using (true);
create policy "gb admin write" on public.group_buys for all to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- 集氣：登入者只能在「集氣中」時加入或取消自己的；本人與管理者可看
create policy "interest read" on public.group_buy_interests for select to authenticated
  using (user_id = auth.uid() or public.is_admin());
create policy "interest insert" on public.group_buy_interests for insert to authenticated
  with check (user_id = auth.uid()
    and exists (select 1 from public.group_buys g where g.book_id = group_buy_interests.book_id and g.status = 'collecting'));
create policy "interest delete" on public.group_buy_interests for delete to authenticated
  using (user_id = auth.uid()
    and exists (select 1 from public.group_buys g where g.book_id = group_buy_interests.book_id and g.status = 'collecting'));

-- 跟團回覆：只有集氣過的人、在開團中才能回覆；本人與管理者可看
create policy "resp read" on public.group_buy_responses for select to authenticated
  using (user_id = auth.uid() or public.is_admin());
create policy "resp write" on public.group_buy_responses for insert to authenticated
  with check (user_id = auth.uid()
    and exists (select 1 from public.group_buys g where g.book_id = group_buy_responses.book_id and g.status = 'open')
    and exists (select 1 from public.group_buy_interests i where i.book_id = group_buy_responses.book_id and i.user_id = auth.uid()));
create policy "resp update" on public.group_buy_responses for update to authenticated
  using (user_id = auth.uid()
    and exists (select 1 from public.group_buys g where g.book_id = group_buy_responses.book_id and g.status = 'open'))
  with check (user_id = auth.uid());

-- 通知佇列：本人與管理者可讀；寫入只能透過 open_group_buy()
create policy "outbox read" on public.notification_outbox for select to authenticated
  using (user_id = auth.uid() or public.is_admin());

-- ============ 照片儲存（Storage） ============
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('book-photos', 'book-photos', true, 2097152, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;

create policy "photos public read" on storage.objects for select
  using (bucket_id = 'book-photos');
create policy "photos upload own folder" on storage.objects for insert to authenticated
  with check (bucket_id = 'book-photos' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "photos delete own or admin" on storage.objects for delete to authenticated
  using (bucket_id = 'book-photos'
    and ((storage.foldername(name))[1] = auth.uid()::text or public.is_admin()));

-- ============ 設定自己為管理者（註冊完網站帳號後，把 Email 換成你的再執行） ============
-- insert into public.admins (user_id)
-- select id from auth.users where email = 'you@example.com';
