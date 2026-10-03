-- Secure online-order creation for Seetharam.
-- The server receives product IDs/quantities; prices and stock are read from products.
create or replace function create_online_order(
  p_user_id uuid,
  p_shipping_address jsonb,
  p_items jsonb,
  p_coupon_code text default null
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_order_id uuid;
  v_subtotal numeric(12,2) := 0;
  v_discount numeric(12,2) := 0;
  v_total numeric(12,2) := 0;
  v_shipping numeric(12,2) := 0;
  v_coupon coupons%rowtype;
  v_item jsonb;
  v_product products%rowtype;
  v_qty int;
  v_line numeric(12,2);
begin
  if p_user_id is null then raise exception 'Sign-in required.'; end if;
  if jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'Cart is empty.';
  end if;

  for v_item in select * from jsonb_array_elements(p_items)
  loop
    v_qty := greatest(1, coalesce((v_item->>'quantity')::int, 0));
    select * into v_product from products where id = (v_item->>'product_id')::uuid and is_active = true for update;
    if not found then raise exception 'Product is no longer available.'; end if;
    if v_product.stock_quantity < v_qty then
      raise exception 'Only % of % is available.', v_product.stock_quantity, v_product.name;
    end if;
    v_line := v_product.price * v_qty;
    v_subtotal := v_subtotal + v_line;
  end loop;

  if p_coupon_code is not null and btrim(p_coupon_code) <> '' then
    select * into v_coupon from coupons
    where upper(code) = upper(btrim(p_coupon_code))
      and is_active = true
      and (starts_at is null or starts_at <= now())
      and (expires_at is null or expires_at >= now())
    for update;
    if not found then raise exception 'Coupon is invalid or expired.'; end if;
    if v_subtotal < v_coupon.minimum_order_value then
      raise exception 'Minimum order value is %.', v_coupon.minimum_order_value;
    end if;
    if v_coupon.usage_limit is not null and v_coupon.used_count >= v_coupon.usage_limit then
      raise exception 'Coupon usage limit reached.';
    end if;
    if v_coupon.discount_type = 'percent' then
      v_discount := round(v_subtotal * v_coupon.discount_value / 100, 2);
    else
      v_discount := v_coupon.discount_value;
    end if;
    if v_coupon.max_discount is not null then
      v_discount := least(v_discount, v_coupon.max_discount);
    end if;
    v_discount := least(v_discount, v_subtotal);
  end if;

  v_total := greatest(0, v_subtotal - v_discount + v_shipping);

  insert into orders(user_id,status,payment_method,payment_status,subtotal,discount,shipping_fee,total,coupon_code,shipping_address)
  values(p_user_id,'ordered','online','pending',v_subtotal,v_discount,v_shipping,v_total,nullif(upper(btrim(p_coupon_code)),''),coalesce(p_shipping_address,'{}'::jsonb))
  returning id into v_order_id;

  for v_item in select * from jsonb_array_elements(p_items)
  loop
    v_qty := greatest(1, coalesce((v_item->>'quantity')::int, 0));
    select * into v_product from products where id = (v_item->>'product_id')::uuid for update;
    insert into order_items(order_id,product_id,product_name,quantity,unit_price,total_price)
    values(v_order_id,v_product.id,v_product.name,v_qty,v_product.price,v_product.price*v_qty);
    update products set stock_quantity = stock_quantity - v_qty, updated_at = now() where id = v_product.id;
  end loop;

  if p_coupon_code is not null and btrim(p_coupon_code) <> '' then
    update coupons set used_count = used_count + 1 where id = v_coupon.id;
  end if;

  insert into order_status_history(order_id,status,note)
  values(v_order_id,'ordered','Online payment order created; awaiting payment.');

  insert into notifications(user_id,title,message,type,order_id)
  values(p_user_id,'Payment required','Complete payment for your Seetharam order #' || left(v_order_id::text,8) || '.','order',v_order_id);

  return jsonb_build_object(
    'order_id',v_order_id,
    'subtotal',v_subtotal,
    'discount',v_discount,
    'shipping_fee',v_shipping,
    'total',v_total,
    'payment_status','pending'
  );
end;
$$;
