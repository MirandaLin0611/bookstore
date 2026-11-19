// Run with PGLITE_MODULE pointing to an installed @electric-sql/pglite/dist/index.js.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const { PGlite } = await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const root = new URL('../', import.meta.url);
const sql = await Promise.all(['schema.sql','patch1.sql','patch2.sql','patch3.sql'].map(name => readFile(new URL(name, root), 'utf8')));
const db = new PGlite();
await db.exec(`
create role anon;
create role authenticated;
create schema auth;
create table auth.users (id uuid primary key, email text, raw_user_meta_data jsonb default '{}');
create function auth.uid() returns uuid language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
$$;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
create schema storage;
create table storage.buckets (id text primary key, name text, public boolean, file_size_limit bigint, allowed_mime_types text[]);
create table storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text, name text);
create function storage.foldername(name text) returns text[] language sql immutable as $$
  select (string_to_array(name, '/'))[1:greatest(cardinality(string_to_array(name, '/'))-1,0)];
$$;
`);
for (const source of sql.slice(0,3)) await db.exec(source);
const owner='00000000-0000-4000-8000-000000000001';
const other='00000000-0000-4000-8000-000000000002';
const admin='00000000-0000-4000-8000-000000000003';
const book='00000000-0000-4000-8000-000000000010';
const pending='00000000-0000-4000-8000-000000000011';
const hidden='00000000-0000-4000-8000-000000000012';
for (const id of [owner,other,admin]) await db.query('insert into auth.users (id,email) values ($1,$2)',[id,id+'@example.com']);
await db.query('insert into public.admins (user_id) values ($1)',[admin]);
for (const [id,status] of [[book,'published'],[pending,'pending'],[hidden,'hidden']]) {
  await db.query(`insert into public.books (id,title,author,lang,status,submitted_by,photos,suggested_ages,suggested_stages)
    values ($1,'原本的書名','作者','中文',$2,$3,$4,array[3]::smallint[],array['幼幼班'])`,[id,status,owner,[owner+'/original.jpg']]);
}
await db.query(`insert into public.book_votes (book_id,user_id,ages,stages) values
 ($1,$2,array[3]::smallint[],array['幼幼班']),($1,$3,array[4]::smallint[],array['小班'])`,[book,owner,other]);
await db.query('insert into public.favorites (book_id,user_id) values ($1,$2)',[book,other]);
await db.query("insert into public.comments (book_id,user_id,body) values ($1,$2,'原本的家長留言內容')",[book,other]);
await db.query('insert into public.helpful (book_id,user_id) values ($1,$2)',[book,other]);
await db.query('insert into public.reading_log (book_id,user_id) values ($1,$2)',[book,other]);
await db.query("insert into public.group_buys (book_id,target,status) values ($1,2,'open')",[book]);
await db.query('insert into public.group_buy_interests (book_id,user_id) values ($1,$2)',[book,other]);
await db.query("insert into public.group_buy_responses (book_id,user_id,decision,qty) values ($1,$2,'join',2)",[book,other]);
const policyQuery="select schemaname,tablename,policyname,roles,cmd,qual,with_check from pg_policies order by schemaname,tablename,policyname";
const policies=(await db.query(policyQuery)).rows;
const allBooks=(await db.query('select row_to_json(b) as row from public.books b order by id')).rows;
await db.exec(sql[3]);
assert.deepEqual((await db.query('select row_to_json(b) as row from public.books b order by id')).rows,allBooks);
assert.deepEqual((await db.query(policyQuery)).rows,policies);
const fields=['title','author','lang','is_taiwan','themes','styles','review','kid_reaction','warning','guide_before','guide_during','guide_after','photos'];
async function current(id=book) {
  await db.exec('reset role');
  return (await db.query('select * from public.books where id=$1',[id])).rows[0];
}
function original(row) {return Object.fromEntries(fields.map(field=>[field,row[field]]));}
async function edit(actor,id,changes,expected) {
  const snapshot=expected || original(await current(id));
  await db.exec('set role authenticated');
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[actor || '']);
  try {
    return (await db.query('select public.edit_book_content($1,$2::jsonb,$3::jsonb) as book',[id,JSON.stringify(changes),JSON.stringify(snapshot)])).rows[0].book;
  } finally {await db.exec('reset role');}
}
const childTables=['book_votes','favorites','comments','helpful','reading_log','group_buys','group_buy_interests','group_buy_responses','notification_outbox'];
async function relatedRows() {
  const result={};
  for (const table of childTables) result[table]=(await db.query(`select row_to_json(t) as row from public.${table} t order by row_to_json(t)::text`)).rows;
  return result;
}
const before=await current();
const related=await relatedRows();
const edited=await edit(owner,book,{title:'修正後的書名',review:'新增的共讀心得',themes:['自訂新主題'],styles:['水彩']});
assert.equal(edited.title,'修正後的書名');
assert.equal(edited.review,'新增的共讀心得');
for (const field of ['id','submitted_by','status','suggested_ages','suggested_stages']) assert.deepEqual(edited[field],before[field]);
assert.equal(new Date(edited.created_at).getTime(),new Date(before.created_at).getTime());
assert.deepEqual(await relatedRows(),related);
await assert.rejects(edit(other,book,{review:'他人嘗試修改'}),e=>e.code==='42501');
await assert.rejects(edit(null,book,{review:'未登入嘗試修改'}),e=>e.code==='42501');
await db.exec('set role anon');
await db.query("select set_config('request.jwt.claim.sub',$1,false)",[owner]);
await assert.rejects(db.query('select public.edit_book_content($1,$2::jsonb,$3::jsonb)',[book,'{}','{}']),e=>e.code==='42501');
await db.exec('reset role');
for (const field of ['id','status','submitted_by','created_at','suggested_ages','suggested_stages']) {
  await assert.rejects(edit(owner,book,{[field]:field==='status'?'hidden':null}),e=>e.code==='22023');
}
await db.exec('set role authenticated');
await db.query("select set_config('request.jwt.claim.sub',$1,false)",[owner]);
await db.query("update public.books set status='hidden',review='不應直接寫入' where id=$1",[book]);
await db.exec('reset role');
assert.equal((await current()).status,'published');
assert.equal((await current()).review,'新增的共讀心得');
await edit(admin,book,{review:'管理者協助修改'});
assert.equal((await current()).submitted_by,owner);
const stale=original(await current());
await edit(owner,book,{review:'另一個視窗已儲存的內容'});
await assert.rejects(edit(owner,book,{review:'過期視窗嘗試覆蓋'},stale),e=>e.code==='40001');
assert.equal((await current()).review,'另一個視窗已儲存的內容');
await assert.rejects(edit(owner,book,{review:'缺少原始值'},{}),e=>e.code==='40001');
await assert.rejects(edit(owner,book,{title:'字'.repeat(121),review:'不應部分儲存'}),e=>e.code==='23514');
assert.equal((await current()).review,'另一個視窗已儲存的內容');
await assert.rejects(edit(owner,book,{title:null}),e=>e.code==='23502');
await assert.rejects(edit(owner,book,{themes:[null]}),e=>e.code==='22023');
await assert.rejects(edit(owner,book,{styles:[['錯誤的巢狀標籤']]}),e=>e.code==='22023');
await assert.rejects(edit(owner,book,{photos:[[owner+'/nested.jpg']]}),e=>e.code==='22023');
await edit(owner,book,{photos:[owner+'/new.jpg',owner+'/original.jpg']});
await assert.rejects(edit(owner,book,{photos:[other+'/foreign.jpg']}),e=>e.code==='42501');
await assert.rejects(edit(owner,book,{photos:[owner+'/../foreign.jpg']}),e=>e.code==='42501');
await assert.rejects(edit(owner,book,{photos:[null]}),e=>e.code==='42501');
await assert.rejects(edit(owner,book,{photos:[1,2,3,4,5].map(i=>owner+'/'+i+'.jpg')}),e=>e.code==='23514');
await edit(admin,book,{photos:[owner+'/original.jpg',admin+'/admin-upload.jpg']});
await edit(owner,book,{photos:[]});
assert.deepEqual((await current()).photos,[]);
for (const [id,status] of [[pending,'pending'],[hidden,'hidden']]) {
  await edit(owner,id,{review:'更新內容但不變更狀態'});
  assert.equal((await current(id)).status,status);
}
await db.exec(sql[3]);
assert.deepEqual((await db.query(policyQuery)).rows,policies);
assert.deepEqual(await relatedRows(),related);
console.log(JSON.stringify({migrationIdempotent:true,ownerAndAdminCanEdit:true,otherUsersAndAnonymousDenied:true,
 protectedFieldsAndDirectUpdatesDenied:true,staleEditsRejected:true,photoOwnershipChecked:true,
 constraintsAndAtomicityPreserved:true,statusAndIdentityPreserved:true,relatedTablesUnchanged:childTables,
 existingPoliciesUnchanged:policies.length}));
await db.close();
