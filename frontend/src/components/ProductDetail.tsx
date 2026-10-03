import { useMemo, useState } from "react";
import type { Product } from "../types";

const money = (n:number) => "₹" + Number(n).toLocaleString("en-IN");

export default function ProductDetail({ p, add, back, wished, onWish }: {
  p: Product; add: (p: Product) => void; back: () => void; wished?: boolean; onWish?: () => void;
}) {
  const images = useMemo(() => (p.product_images ?? []).slice().sort((a,b) => a.sort_order - b.sort_order), [p.product_images]);
  const [selected, setSelected] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const current = images[selected]?.image_url;
  const max = Math.max(1, p.stock_quantity);
  return <main className="page product-detail-page">
    <button className="back-button" onClick={back}>← Back to store</button>
    <div className="product-detail-layout">
      <section>
        <div className="product-main-image">{current ? <img src={current} alt={images[selected]?.alt_text || p.name} /> : <span>Seetharam</span>}</div>
        {images.length > 1 && <div className="product-thumbnails">{images.map((im, i) => <button className={i === selected ? "active" : ""} key={im.image_url + i} onClick={() => setSelected(i)}><img src={im.image_url} alt={im.alt_text || p.name} /></button>)}</div>}
      </section>
      <section className="product-detail-info">
        <p className="eyebrow">{p.brands?.name || "SEETHARAM ESSENTIALS"}</p><h1>{p.name}</h1>
        <div className="detail-rating">★ {Number(p.rating || 0).toFixed(1)} · {p.review_count || 0} reviews</div>
        <div className="detail-price">{money(p.price)} {p.compare_at_price ? <del>{money(p.compare_at_price)}</del> : null}</div>
        <p className="description">{p.description || "Quality fashion selected for everyday Seetharam shopping."}</p>
        <div className="detail-stock">{p.stock_quantity > 0 ? `${p.stock_quantity} available` : "Currently out of stock"}</div>
        <div className="quantity-control"><button onClick={() => setQuantity(q => Math.max(1, q - 1))}>−</button><b>{quantity}</b><button onClick={() => setQuantity(q => Math.min(max, q + 1))}>+</button></div>
        <div className="detail-actions"><button className="primary" disabled={!p.stock_quantity} onClick={() => { for (let i=0;i<quantity;i++) add(p); }}>Add to cart</button>{onWish && <button className="add-button" onClick={onWish}>{wished ? "♥ Wishlisted" : "♡ Wishlist"}</button>}</div>
        <div className="detail-benefits"><span>✓ COD available</span><span>✓ Easy returns</span><span>✓ Secure delivery</span></div>
      </section>
    </div>
  </main>;
}