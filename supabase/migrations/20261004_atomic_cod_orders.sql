create or replace function public.create_cod_order(
  p_user_id uuid,
  p_shipping_address jsonb,
  p_items jsonb,
  p_coupon_code text default null
)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
  v_item record;
  v_product public.products%rowtype;
  v_coupon public.coupons%rowtype;
  v_order public.orders%rowtype;
  v_verified_items jsonb := '[]'::jsonb;
  v_subtotal numeric(12,2) := 0;
  v_discount numeric(12,2) := 0;
  v_total numeric(12,2) := 0;
  v_coupon_code text;
begin
  if p_user_id is null then raise exception 'User is required'; end if;
  if p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'Cart is empty';
  end if;

  for v_item in
    select product_id, sum(quantity)::integer as quantity
    from jsonb_to_recordset(p_items) as x(product_id uuid, quantity integer)
    group by product_id
  loop
    if v_item.product_id is null or v_item.quantity is null or v_item.quantity < 1 then
      raise exception 'Invalid cart item';
    end if;

    select * into v_product
    from public.products
    where id = v_item.product_id
    for update;

    if not found or not v_product.is_active then
      raise exception 'Product is no longer available';
    end if;

    if v_item.quantity > v_product.stock_quantity then
      raise exception 'Only % unit(s) of % are available', v_product.stock_quantity, v_product.name;
    end if;

    v_subtotal := v_subtotal + (v_product.price * v_item.quantity);
    v_verified_items := v_verified_items || jsonb_build_array(jsonb_build_object(
      'product_id', v_product.id,
      'product_name', v_product.name,
      'quantity', v_item.quantity,
      'unit_price', v_product.price,
      'total_price', v_product.price * v_item.quantity
    ));
  end loop;

  if p_coupon_code is not null and btrim(p_coupon_code) <> '' then
    v_coupon_code := upper(btrim(p_coupon_code));
    select * into v_coupon from public.coupons where code = v_coupon_code for update;
    if not found then raise exception 'Coupon not found'; end if;
    if not v_coupon.is_active then raise exception 'Coupon is inactive'; end if;
    if v_coupon.starts_at is not null and now() < v_coupon.starts_at then raise exception 'Coupon is not active yet'; end if;
    if v_coupon.expires_at is not null and now() > v_coupon.expires_at then raise exception 'Coupon has expired'; end if;
    if v_coupon.usage_limit is not null and v_coupon.used_count >= v_coupon.usage_limit then raise exception 'Coupon usage limit reached'; end if;
    if v_subtotal < v_coupon.minimum_order_value then raise exception 'Minimum order value not reached'; end if;
    if v_coupon.discount_type = 'percent' then
      v_discount := v_subtotal * v_coupon.discount_value / 100;
    else
      v_discount := v_coupon.discount_value;
    end if;
    if v_coupon.max_discount is not null then v_discount := least(v_discount, v_coupon.max_discount); end if;
    v_discount := least(v_discount, v_subtotal);
  end if;

  v_total := greatest(0, v_subtotal - v_discount);

  insert into public.orders (
    user_id, status, payment_method, payment_status, subtotal, discount,
    shipping_fee, total, shipping_address, coupon_code
  ) values (
    p_user_id, 'ordered', 'cod', 'pending', v_subtotal, v_discount,
    0, v_total, p_shipping_address, v_coupon.code
  ) returning * into v_order;

  insert into public.order_items (
    order_id, product_id, product_name, quantity, unit_price, total_price
  )
  select v_order.id, x.product_id, x.product_name, x.quantity, x.unit_price, x.total_price
  from jsonb_to_recordset(v_verified_items) as x(
    product_id uuid, product_name text, quantity integer,
    unit_price numeric(12,2), total_price numeric(12,2)
  );

  for v_item in
    select product_id, quantity
    from jsonb_to_recordset(v_verified_items) as x(product_id uuid, quantity integer)
  loop
    update public.products
    set stock_quantity = stock_quantity - v_item.quantity, updated_at = now()
    where id = v_item.product_id;
  end loop;

  insert into public.order_status_history(order_id, status, note)
  values (v_order.id, 'ordered', 'Order placed');

  insert into public.notifications(user_id, title, message, type, order_id)
  values (p_user_id, 'Order placed',
          'Your Seetharam order #' || left(v_order.id::text, 8) || ' has been placed.',
          'order', v_order.id);

  if v_coupon.code is not null then
    update public.coupons set used_count = used_count + 1 where id = v_coupon.id;
  end if;

  return jsonb_build_object('order', to_jsonb(v_order));
end;
$$;

revoke all on function public.create_cod_order(uuid, jsonb, jsonb, text) from public, anon, authenticated;
grant execute on function public.create_cod_order(uuid, jsonb, jsonb, text) to service_role;
