import { useEffect, useMemo, useState } from "react";
import { api } from "./lib/api";
import type { Category, Product } from "./types";
import "./styles.css";

const fallbackCategories = ["Men","Women","Kids","Sarees","Footwear","Accessories","Offers","New Arrivals","Best Sellers"];

function ProductCard({ product, onAdd, wished, onWish }: { product: Product; onAdd: () => void; wished: boolean; onWish: () => void }) {
  const image = product.product_images?.slice().sort((a,b) => a.sort_order-b.sort_order)[0]?.image_url;
  return (
    <article className="product-card">
      <button className="wish-button" onClick={onWish} aria-label="Toggle wishlist">{wished ? "♥" : "♡"}</button>
      <div className="product-image">
        {image ? <img src={image} alt={product.name} /> : <span>Seetharam</span>}
      </div>
      <div className="product-info">
        <small>{product.brands?.name ?? "Seetharam Essentials"}</small>
        <h3>{product.name}</h3>
        <div className="rating">★ {Number(product.rating || 0).toFixed(1)} <span>({product.review_count || 0})</span></div>
        <div className="price-row"><strong>₹{Number(product.price).toLocaleString("en-IN")}</strong>{product.compare_at_price && <del>₹{Number(product.compare_at_price).toLocaleString("en-IN")}</del>}</div>
        <button className="add-button" onClick={onAdd}>Add to cart</button>
      </div>
    </article>
  );
}

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("");
  const [cart, setCart] = useState<string[]>(() => JSON.parse(localStorage.getItem("seetharam-cart") || "[]"));
  const [wishlist, setWishlist] = useState<string[]>(() => JSON.parse(localStorage.getItem("seetharam-wishlist") || "[]"));
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.categories().then(r => setCategories(r.items)).catch(() => setCategories([])); }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (query.trim()) params.set("search", query.trim());
    if (activeCategory) params.set("category", activeCategory);
    api.products(params.toString() ? `?${params}` : "")
      .then(r => setProducts(r.items))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [query, activeCategory]);

  useEffect(() => { localStorage.setItem("seetharam-cart", JSON.stringify(cart)); }, [cart]);
  useEffect(() => { localStorage.setItem("seetharam-wishlist", JSON.stringify(wishlist)); }, [wishlist]);

  const visibleCategories = useMemo(() => categories.length ? categories : fallbackCategories.map((name, i) => ({id:String(i),name,slug:name.toLowerCase().replaceAll(" ","-"),sort_order:i})), [categories]);

  const addToCart = (id: string) => setCart(items => [...items, id]);
  const toggleWish = (id: string) => setWishlist(items => items.includes(id) ? items.filter(x => x !== id) : [...items, id]);

  return (
    <div className="app">
      <div className="topbar">Free delivery on eligible orders · COD available · Easy returns</div>
      <header className="header">
        <a className="logo" href="#">seetharam<span>.</span></a>
        <div className="search">
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search for products, brands and more" />
          <button aria-label="Search">⌕</button>
        </div>
        <nav className="header-actions"><button>Account</button><button>Wishlist ({wishlist.length})</button><button>Cart ({cart.length})</button></nav>
      </header>

      <nav className="category-nav">
        {visibleCategories.map(category => (
          <button key={category.id} className={activeCategory === category.slug ? "active" : ""} onClick={() => setActiveCategory(activeCategory === category.slug ? "" : category.slug)}>{category.name}</button>
        ))}
      </nav>

      <main>
        <section className="hero">
          <div><p className="eyebrow">SEETHARAM NEW SEASON</p><h1>Style that feels<br/><em>like you.</em></h1><p>Modern Indian fashion for every moment, with everyday prices and effortless delivery.</p><button className="primary" onClick={() => document.getElementById("products")?.scrollIntoView({behavior:"smooth"})}>Shop collection →</button></div>
          <div className="hero-art"><div className="hero-card">NEW<br/><strong>ARRIVALS</strong><small>MEN · WOMEN · KIDS</small></div></div>
        </section>

        <section className="section">
          <div className="section-heading"><div><p className="eyebrow">SHOP BY CATEGORY</p><h2>Find your style</h2></div><button className="text-button" onClick={() => setActiveCategory("")}>View all →</button></div>
          <div className="category-grid">{visibleCategories.slice(0,9).map((c,i) => <button key={c.id} className="category-tile" onClick={() => setActiveCategory(c.slug)}><span>{["M","W","K","S","F","A","%","N","★"][i]}</span><b>{c.name}</b></button>)}</div>
        </section>

        <section className="section" id="products">
          <div className="section-heading"><div><p className="eyebrow">{activeCategory ? activeCategory.replaceAll("-"," ").toUpperCase() : "CURATED FOR YOU"}</p><h2>Trending now</h2></div><span className="count">{products.length} products</span></div>
          {loading ? <div className="loading-grid">{[1,2,3,4].map(i => <div className="skeleton" key={i}/>)}</div> :
            products.length ? <div className="product-grid">{products.map(p => <ProductCard key={p.id} product={p} onAdd={() => addToCart(p.id)} wished={wishlist.includes(p.id)} onWish={() => toggleWish(p.id)}/>)}</div> :
            <div className="empty"><h3>No products found</h3><p>Try another search or category.</p><button className="primary" onClick={() => {setQuery("");setActiveCategory("")}}>Show all products</button></div>}
        </section>

        <section className="offer-banner"><div><p className="eyebrow">SEETHARAM OFFERS</p><h2>Fresh looks.<br/>Better prices.</h2><p>Discover new arrivals, best sellers and seasonal offers.</p></div><button className="primary" onClick={() => setActiveCategory("offers")}>Explore offers →</button></section>
      </main>

      <footer><div><a className="logo" href="#">seetharam<span>.</span></a><p>Your everyday fashion marketplace.</p></div><div><b>Shop</b><span>Men</span><span>Women</span><span>Kids</span></div><div><b>Help</b><span>Orders & tracking</span><span>Returns</span><span>Support</span></div><div><b>Coming soon</b><span>Online payments</span><span>Android app</span><span>Multi-vendor marketplace</span></div></footer>
    </div>
  );
}
