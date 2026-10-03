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
  tracking: (orderId: string, userId: string) => request<{ order:any; history:any[] }>(`/orders/${orderId}/tracking?user_id=${encodeURIComponent(userId)}`),
  cancelOrder: (orderId: string, userId: string) => fetch(`${API_BASE}/orders/${orderId}/cancel?user_id=${encodeURIComponent(userId)}`, {method:"POST"}).then(async res=>{if(!res.ok)throw new Error((await res.json()).detail||"Unable to cancel order");return res.json();}),
  returnOrder: (orderId: string, userId: string) => fetch(`${API_BASE}/orders/${orderId}/return-request?user_id=${encodeURIComponent(userId)}`, {method:"POST"}).then(async res=>{if(!res.ok)throw new Error((await res.json()).detail||"Unable to request return");return res.json();}),
  notifications: (userId: string) => request<{items:any[];unread:number}>(`/notifications/user/${encodeURIComponent(userId)}`),
  markNotificationRead: (notificationId: string, userId: string) => fetch(`${API_BASE}/notifications/${notificationId}/read?user_id=${encodeURIComponent(userId)}`, {method:"PATCH"}).then(async res=>{if(!res.ok)throw new Error((await res.json()).detail||"Unable to mark notification");return res.json();}),
  validateCoupon: (code: string, subtotal: number) => fetch(`${API_BASE}/coupons/validate`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code,subtotal})}).then(async res=>{if(!res.ok)throw new Error((await res.json()).detail||"Coupon validation failed");return res.json();}),
  reviews: (productId: string) => request<{ items: any[] }>(`/reviews/product/${productId}`),
  createReview: (body: unknown, token: string) => fetch(`${API_BASE}/reviews`, {method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},body:JSON.stringify(body)}).then(async res=>{if(!res.ok)throw new Error((await res.json()).detail||"Review failed");return res.json();}),
  helpfulReview: (reviewId: string) => fetch(`${API_BASE}/reviews/${reviewId}/helpful`,{method:"POST"}).then(async res=>{if(!res.ok)throw new Error("Unable to vote");return res.json();}),\n  uploadReviewImage: async (reviewId: string, token: string, file: File) => { const form=new FormData(); form.append("file",file); const res=await fetch(`${API_BASE}/reviews/${reviewId}/images/upload`,{method:"POST",headers:{Authorization:`Bearer ${token}`},body:form}); if(!res.ok) throw new Error((await res.json()).detail||"Photo upload failed"); return res.json(); },
\n  adminUpload: async (path: string, token: string, file: File) => { const form=new FormData(); form.append("file",file); const res=await fetch(`${API_BASE}/admin${path}`,{method:"POST",headers:{Authorization:`Bearer ${token}`},body:form}); if(!res.ok) throw new Error((await res.json()).detail||"Upload failed"); return res.json(); },\n  admin: async (path: string, token: string, options: RequestInit = {}) => { const res = await fetch(`${API_BASE}/admin${path}`, { ...options, headers: {"Content-Type":"application/json", Authorization:`Bearer ${token}`, ...(options.headers||{})} }); if(!res.ok) throw new Error((await res.json()).detail || "Admin request failed"); return res.json(); },
};
