create database if not exists ironx_gym;
use ironx_gym;

create table if not exists users (
  id bigint unsigned not null auto_increment primary key,
  name varchar(120) not null,
  email varchar(255) not null unique,
  password_hash varchar(255) not null,
  phone varchar(40) not null default '',
  created_at timestamp not null default current_timestamp
);

create table if not exists leads (
  id bigint unsigned not null auto_increment primary key,
  user_id bigint unsigned null,
  name varchar(120) not null,
  age smallint unsigned not null,
  location varchar(160) not null,
  email varchar(255) not null,
  phone varchar(40) not null,
  height varchar(20) not null,
  weight varchar(20) not null,
  body_type varchar(60) not null,
  preferred_date date null,
  preferred_time time null,
  created_at timestamp not null default current_timestamp,
  constraint leads_user_fk foreign key (user_id) references users(id) on delete set null
);

-- Upgrade an older leads table created before member accounts were added.
set @has_leads_user_id = (
  select count(*) from information_schema.columns
  where table_schema = database() and table_name = 'leads' and column_name = 'user_id'
);
set @add_leads_user_id = if(
  @has_leads_user_id = 0,
  'alter table leads add column user_id bigint unsigned null after id',
  'select 1'
);
prepare add_leads_user_id from @add_leads_user_id;
execute add_leads_user_id;
deallocate prepare add_leads_user_id;

set @has_leads_user_fk = (
  select count(*) from information_schema.table_constraints
  where table_schema = database() and table_name = 'leads' and constraint_name = 'leads_user_fk'
);
set @add_leads_user_fk = if(
  @has_leads_user_fk = 0,
  'alter table leads add constraint leads_user_fk foreign key (user_id) references users(id) on delete set null',
  'select 1'
);
prepare add_leads_user_fk from @add_leads_user_fk;
execute add_leads_user_fk;
deallocate prepare add_leads_user_fk;

set @has_preferred_date = (select count(*) from information_schema.columns where table_schema = database() and table_name = 'leads' and column_name = 'preferred_date');
set @add_preferred_date = if(@has_preferred_date = 0, 'alter table leads add column preferred_date date null after body_type', 'select 1');
prepare add_preferred_date from @add_preferred_date;
execute add_preferred_date;
deallocate prepare add_preferred_date;

set @has_preferred_time = (select count(*) from information_schema.columns where table_schema = database() and table_name = 'leads' and column_name = 'preferred_time');
set @add_preferred_time = if(@has_preferred_time = 0, 'alter table leads add column preferred_time time null after preferred_date', 'select 1');
prepare add_preferred_time from @add_preferred_time;
execute add_preferred_time;
deallocate prepare add_preferred_time;

create table if not exists orders (
  id bigint unsigned not null auto_increment primary key,
  order_ref varchar(36) not null,
  user_id bigint unsigned not null,
  product_name varchar(160) not null,
  category varchar(40) not null default 'store',
  quantity int unsigned not null default 1,
  total_amount decimal(10,2) not null default 0,
  status varchar(40) not null default 'Received',
  created_at timestamp not null default current_timestamp,
  constraint orders_user_fk foreign key (user_id) references users(id) on delete cascade
);

set @has_order_ref = (select count(*) from information_schema.columns where table_schema = database() and table_name = 'orders' and column_name = 'order_ref');
set @add_order_ref = if(@has_order_ref = 0, 'alter table orders add column order_ref varchar(36) not null default ''legacy'' after id', 'select 1');
prepare add_order_ref from @add_order_ref;
execute add_order_ref;
deallocate prepare add_order_ref;

set @has_quantity = (select count(*) from information_schema.columns where table_schema = database() and table_name = 'orders' and column_name = 'quantity');
set @add_quantity = if(@has_quantity = 0, 'alter table orders add column quantity int unsigned not null default 1 after category', 'select 1');
prepare add_quantity from @add_quantity;
execute add_quantity;
deallocate prepare add_quantity;

set @has_total_amount = (select count(*) from information_schema.columns where table_schema = database() and table_name = 'orders' and column_name = 'total_amount');
set @add_total_amount = if(@has_total_amount = 0, 'alter table orders add column total_amount decimal(10,2) not null default 0 after quantity', 'select 1');
prepare add_total_amount from @add_total_amount;
execute add_total_amount;
deallocate prepare add_total_amount;

create table if not exists products (
  id bigint unsigned not null auto_increment primary key,
  name varchar(160) not null,
  category varchar(40) not null default 'store',
  description text not null,
  price decimal(10,2) not null default 0,
  image_url varchar(500) not null default '',
  available boolean not null default true,
  created_at timestamp not null default current_timestamp
);

set @has_product_category = (select count(*) from information_schema.columns where table_schema = database() and table_name = 'products' and column_name = 'category');
set @add_product_category = if(@has_product_category = 0, 'alter table products add column category varchar(40) not null default ''store'' after name', 'select 1');
prepare add_product_category from @add_product_category;
execute add_product_category;
deallocate prepare add_product_category;