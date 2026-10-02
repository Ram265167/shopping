import type { Category, Product } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  products: (params = "") => request<{ items: Product[]; count: number }>(`/products${params}`),
  product: (slug: string) => request<Product>(`/products/${encodeURIComponent(slug)}`),
  categories: () => request<{ items: Category[] }>("/categories"),
  health: () => request<{ status: string }>("/health"),
  createOrder: (body: unknown) => fetch(`${API_BASE}/orders`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) }).then(async res => { if(!res.ok) throw new Error((await res.json()).detail || "Order failed"); return res.json(); }),
  orders: (userId: string) => request<{ items: any[] }>(`/orders/user/${userId}`),
};
