create database if not exists ironx_gym;
use ironx_gym;

create table if not exists leads (
  id bigint unsigned not null auto_increment primary key,
  name varchar(120) not null,
  age smallint unsigned not null,
  location varchar(160) not null,
  email varchar(255) not null,
  phone varchar(40) not null,
  height varchar(20) not null,
  weight varchar(20) not null,
  body_type varchar(60) not null,
  created_at timestamp not null default current_timestamp
);