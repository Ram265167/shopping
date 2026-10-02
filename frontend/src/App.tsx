const categories = ["Men", "Women", "Kids", "Sarees", "Footwear", "Accessories"];

export default function App() {
  return (
    <div className="app">
      <div className="topbar">Free delivery on eligible orders · COD available</div>
      <header className="header">
        <div className="brand">Seetharam</div>
        <div className="search"><span>⌕</span><input placeholder="Search products, brands and categories" /><button>Search</button></div>
        <nav><a>Account</a><a>Wishlist</a><a>Cart (0)</a></nav>
      </header>
      <nav className="categories">{categories.map(c => <a key={c}>{c}</a>)}<a>Offers</a><a>New Arrivals</a><a>Best Sellers</a></nav>
      <main>
        <section className="hero"><div><p className="eyebrow">SEETHARAM COLLECTION</p><h1>Modern Indian fashion for every occasion.</h1><p>Discover curated styles across men, women, kids, sarees, footwear and accessories.</p><div><button className="primary">Shop now</button><button className="secondary">Explore new arrivals</button></div></div><div className="hero-card"><span>NEW</span><strong>Seasonal<br/>Edit</strong></div></section>
        <section className="section"><div className="section-head"><h2>Shop by category</h2><a>View all</a></div><div className="category-grid">{categories.map((c,i)=><article className="category-card" key={c}><span>0{i+1}</span><h3>{c}</h3><p>Explore collection →</p></article>)}</div></section>
        <section className="section"><div className="section-head"><h2>Featured collections</h2><a>View all</a></div><div className="product-grid">{["Everyday Essentials","Festive Edit","Premium Styles","Weekend Picks"].map((p,i)=><article className="product-card" key={p}><div className={"product-image p"+i}></div><div className="product-info"><span>Featured</span><h3>{p}</h3><p>Curated Seetharam collection</p><strong>Explore →</strong></div></article>)}</div></section>
      </main>
      <footer><strong>Seetharam</strong><span>Premium Indian shopping experience</span><span>© 2026 Seetharam</span></footer>
    </div>
  );
}
