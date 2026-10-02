export type Product = {
  id: string; name: string; slug: string; description?: string | null;
  price: number; compare_at_price?: number | null; stock_quantity: number;
  rating: number; review_count: number; is_featured: boolean;
  is_new_arrival: boolean; is_best_seller: boolean;
  categories?: { name: string; slug: string } | null;
  brands?: { name: string; slug: string } | null;
  product_images?: { image_url: string; alt_text?: string | null; sort_order: number }[];
};

export type Category = {
  id: string; name: string; slug: string; image_url?: string | null; sort_order: number;
};

export type CartItem = { product: Product; quantity: number };
