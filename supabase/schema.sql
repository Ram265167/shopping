create extension if not exists pgcrypto;

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text, phone text,
  role text not null default 'customer' check (role in ('customer','admin','staff')),
  avatar_url text, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists categories (
  id uuid primary key default gen_random_uuid(), name text not null unique, slug text not null unique,
  image_url text, sort_order int not null default 0, is_active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists brands (
  id uuid primary key default gen_random_uuid(), name text not null unique, slug text not null unique,
  logo_url text, is_active boolean not null default true, created_at timestamptz not null default now()
);
create table if not exists products (
  id uuid primary key default gen_random_uuid(), category_id uuid references categories(id) on delete set null,
  brand_id uuid references brands(id) on delete set null, seller_id uuid references profiles(id) on delete set null,
  name text not null, slug text not null unique, description text, sku text unique,
  price numeric(12,2) not null default 0 check (price >= 0), compare_at_price numeric(12,2),
  stock_quantity int not null default 0 check (stock_quantity >= 0),
  rating numeric(2,1) not null default 0 check (rating between 0 and 5), review_count int not null default 0,
  is_featured boolean not null default false, is_new_arrival boolean not null default false,
  is_best_seller boolean not null default false, is_active boolean not null default true,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists product_images (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references products(id) on delete cascade,
  image_url text not null, alt_text text, sort_order int not null default 0
);
create table if not exists product_variants (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references products(id) on delete cascade,
  size text, color text, sku text unique, price numeric(12,2), stock_quantity int not null default 0 check (stock_quantity >= 0)
);
create table if not exists addresses (
  id uuid primary key default gen_random_uuid(), user_id uuid not null references profiles(id) on delete cascade,
  full_name text not null, phone text not null, line1 text not null, line2 text, city text not null,
  state text not null, postal_code text not null, country text not null default 'India', is_default boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists carts (
  id uuid primary key default gen_random_uuid(), user_id uuid not null unique references profiles(id) on delete cascade,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists cart_items (
  id uuid primary key default gen_random_uuid(), cart_id uuid not null references carts(id) on delete cascade,
  product_id uuid not null references products(id) on delete cascade, variant_id uuid references product_variants(id) on delete set null,
  quantity int not null default 1 check (quantity > 0), unique(cart_id, product_id, variant_id)
);
create table if not exists wishlists (
  id uuid primary key default gen_random_uuid(), user_id uuid not null unique references profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);
create table if not exists wishlist_items (
  id uuid primary key default gen_random_uuid(), wishlist_id uuid not null references wishlists(id) on delete cascade,
  product_id uuid not null references products(id) on delete cascade, created_at timestamptz not null default now(),
  unique(wishlist_id, product_id)
);
create table if not exists coupons (
  id uuid primary key default gen_random_uuid(), code text not null unique, description text,
  discount_type text not null check (discount_type in ('percent','fixed')), discount_value numeric(12,2) not null check (discount_value > 0),
  minimum_order_value numeric(12,2) not null default 0, max_discount numeric(12,2), usage_limit int, used_count int not null default 0,
  starts_at timestamptz, expires_at timestamptz, is_active boolean not null default true
);
create table if not exists orders (
  id uuid primary key default gen_random_uuid(), user_id uuid references profiles(id) on delete set null,
  seller_id uuid references profiles(id) on delete set null,
  status text not null default 'ordered' check (status in ('ordered','packed','shipped','out_for_delivery','delivered','cancelled','return_requested','returned','refunded')),
  payment_method text not null default 'cod' check (payment_method in ('cod','online')),
  payment_status text not null default 'pending' check (payment_status in ('pending','paid','failed','refunded')),
  subtotal numeric(12,2) not null default 0, discount numeric(12,2) not null default 0, shipping_fee numeric(12,2) not null default 0,
  total numeric(12,2) not null default 0, coupon_code text, shipping_address jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists order_items (
  id uuid primary key default gen_random_uuid(), order_id uuid not null references orders(id) on delete cascade,
  product_id uuid references products(id) on delete set null, variant_id uuid references product_variants(id) on delete set null,
  product_name text not null, quantity int not null check (quantity > 0), unit_price numeric(12,2) not null, total_price numeric(12,2) not null
);
create table if not exists order_status_history (
  id uuid primary key default gen_random_uuid(), order_id uuid not null references orders(id) on delete cascade,
  status text not null, note text, created_at timestamptz not null default now()
);
create table if not exists reviews (
  id uuid primary key default gen_random_uuid(), product_id uuid not null references products(id) on delete cascade,
  user_id uuid references profiles(id) on delete set null, order_id uuid references orders(id) on delete set null,
  rating int not null check (rating between 1 and 5), title text, body text,
  is_verified_buyer boolean not null default false, helpful_count int not null default 0, created_at timestamptz not null default now()
);
create table if not exists review_images (
  id uuid primary key default gen_random_uuid(), review_id uuid not null references reviews(id) on delete cascade, image_url text not null
);
create table if not exists notifications (
  id uuid primary key default gen_random_uuid(), user_id uuid references profiles(id) on delete cascade,
  title text not null, message text not null, type text not null default 'general',
  is_read boolean not null default false, created_at timestamptz not null default now()
);
create table if not exists support_tickets (
  id uuid primary key default gen_random_uuid(), user_id uuid references profiles(id) on delete set null,
  subject text not null, message text not null,
  status text not null default 'open' check (status in ('open','in_progress','resolved','closed')),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create index if not exists idx_products_category on products(category_id);
create index if not exists idx_products_brand on products(brand_id);
create index if not exists idx_products_active on products(is_active);
create index if not exists idx_orders_user on orders(user_id);
create index if not exists idx_order_items_order on order_items(order_id);
create index if not exists idx_reviews_product on reviews(product_id);
create index if not exists idx_notifications_user on notifications(user_id);

insert into categories (name, slug, sort_order) values
('Men','men',1),('Women','women',2),('Kids','kids',3),('Sarees','sarees',4),('Footwear','footwear',5),
('Accessories','accessories',6),('Offers','offers',7),('New Arrivals','new-arrivals',8),('Best Sellers','best-sellers',9)
on conflict (slug) do nothing;
insert into brands (name, slug) values ('Seetharam Essentials','seetharam-essentials') on conflict (slug) do nothing;

alter table categories enable row level security;
alter table brands enable row level security;
alter table products enable row level security;
alter table product_images enable row level security;
alter table product_variants enable row level security;

drop policy if exists "public read active categories" on categories;
create policy "public read active categories" on categories for select using (is_active = true);
drop policy if exists "public read active brands" on brands;
create policy "public read active brands" on brands for select using (is_active = true);
drop policy if exists "public read active products" on products;
create policy "public read active products" on products for select using (is_active = true);
drop policy if exists "public read product images" on product_images;
create policy "public read product images" on product_images for select using (true);
drop policy if exists "public read product variants" on product_variants;
create policy "public read product variants" on product_variants for select using (true);

-- Customer data protection: users can access only their own order/profile data.
alter table profiles enable row level security;
alter table addresses enable row level security;
alter table orders enable row level security;
alter table order_items enable row level security;
alter table order_status_history enable row level security;

drop policy if exists "users read own profile" on profiles;
create policy "users read own profile" on profiles for select using (auth.uid() = id);

drop policy if exists "users manage own addresses" on addresses;
create policy "users manage own addresses" on addresses for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "users read own orders" on orders;
create policy "users read own orders" on orders for select using (auth.uid() = user_id);

drop policy if exists "users read own order items" on order_items;
create policy "users read own order items" on order_items for select using (
  exists (select 1 from orders o where o.id = order_id and o.user_id = auth.uid())
);

drop policy if exists "users read own order status" on order_status_history;
create policy "users read own order status" on order_status_history for select using (
  exists (select 1 from orders o where o.id = order_id and o.user_id = auth.uid())
);
