-- 既有專案在 patch1.sql、patch2.sql 之後執行一次。
-- 投稿人及管理者可編輯書籍內容；不開放直接更新書籍狀態或擁有者。
begin;

create or replace function public.edit_book_content(
  p_book uuid, p_changes jsonb, p_original jsonb
) returns jsonb
language plpgsql security definer
set search_path = pg_catalog, public, pg_temp
as $$
declare
  actor uuid := auth.uid();
  current_book public.books%rowtype;
  edited_book public.books%rowtype;
  allowed_fields text[] := array[
    'title','author','lang','is_taiwan','themes','styles','review','kid_reaction',
    'warning','guide_before','guide_during','guide_after','photos'
  ];
  field_name text;
  photo_path text;
begin
  if actor is null then
    raise exception using errcode = '42501', message = '請先登入才能編輯。';
  end if;
  if jsonb_typeof(p_changes) is distinct from 'object'
     or jsonb_typeof(p_original) is distinct from 'object'
     or p_changes = '{}'::jsonb then
    raise exception using errcode = '22023', message = '編輯資料格式不正確。';
  end if;
  if exists (select 1 from jsonb_object_keys(p_changes) k where not (k = any(allowed_fields)))
     or exists (select 1 from jsonb_object_keys(p_original) k where not (k = any(allowed_fields))) then
    raise exception using errcode = '22023', message = '只能修改書籍內容。';
  end if;

  select * into current_book from public.books where id = p_book for update;
  if not found or (current_book.submitted_by <> actor and not public.is_admin()) then
    raise exception using errcode = '42501', message = '只有投稿人或管理者可以編輯這本書。';
  end if;

  for field_name in select jsonb_object_keys(p_changes) loop
    if not (p_original ? field_name)
       or (to_jsonb(current_book) -> field_name) is distinct from (p_original -> field_name) then
      raise exception using errcode = '40001', message = '這本書已被更新，請重新開啟編輯後再儲存。';
    end if;
  end loop;

  edited_book := jsonb_populate_record(current_book, p_changes);
  if edited_book.themes is null or edited_book.styles is null
     or coalesce(array_ndims(edited_book.themes),1) <> 1
     or coalesce(array_ndims(edited_book.styles),1) <> 1
     or array_position(edited_book.themes,null) is not null
     or array_position(edited_book.styles,null) is not null then
    raise exception using errcode = '22023', message = '主題與畫風請填寫文字標籤。';
  end if;
  if edited_book.photos is null or coalesce(array_ndims(edited_book.photos),1) <> 1 then
    raise exception using errcode = '22023', message = '照片資料格式不正確。';
  end if;
  foreach photo_path in array edited_book.photos loop
    if photo_path is null or photo_path = ''
       or (not coalesce(photo_path = any(current_book.photos), false)
           and (photo_path not like actor::text || '/%'
                or photo_path ~ '(^|/)\.\.?(/|$)')) then
      raise exception using errcode = '42501', message = '新增的照片必須由目前登入的帳號上傳。';
    end if;
  end loop;

  update public.books set
    title = edited_book.title, author = edited_book.author, lang = edited_book.lang,
    is_taiwan = edited_book.is_taiwan, themes = edited_book.themes,
    styles = edited_book.styles, review = edited_book.review,
    kid_reaction = edited_book.kid_reaction, warning = edited_book.warning,
    guide_before = edited_book.guide_before, guide_during = edited_book.guide_during,
    guide_after = edited_book.guide_after, photos = edited_book.photos
  where id = p_book returning * into edited_book;

  return to_jsonb(edited_book);
end;
$$;

revoke all on function public.edit_book_content(uuid,jsonb,jsonb) from public, anon;
grant execute on function public.edit_book_content(uuid,jsonb,jsonb) to authenticated;

notify pgrst, 'reload schema';

commit;
