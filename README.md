# Seetharam Ecommerce

Modern Indian ecommerce platform. Single-vendor first, with an API/database design ready for future multi-vendor expansion.

## Stack
- React + TypeScript + Vite
- Python FastAPI REST backend
- Supabase PostgreSQL, Auth and Storage
- Responsive web app with PWA-ready architecture\n- Razorpay-ready online payment checkout with server-side order creation and signature verification\n- Vercel frontend + Render backend deployment configuration

## Core catalog
Men, Women, Kids, Sarees, Footwear, Accessories, Offers, New Arrivals and Best Sellers.

## Customer features
Responsive banners, search, filters, sorting, product variants, cart, wishlist, COD checkout, orders, tracking, cancellation, returns/refunds, reviews, notifications, dark mode and support.

## Admin
Products, categories, images, customers, orders, inventory, coupons, reviews, reports, notifications and roles.

## Security
Never commit database passwords, Supabase service-role keys or other secrets. Use local environment variables and commit only safe placeholders.


## Run the Seetharam app locally

### 1. Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local` from `frontend/.env.example` and add your Supabase **project URL** and **anon/publishable key**. Never put the Supabase service-role key in the frontend or commit it to GitHub.

Then run:

```bash
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API normally runs at `http://localhost:8000`.

### Current customer milestone

- Responsive Seetharam storefront
- Supabase-backed product/category API
- Product detail page
- Local cart with quantities
- Wishlist page
- Email/password Supabase authentication
- COD-ready checkout entry point
- Responsive mobile layout

Google login and mobile OTP are available through Supabase Auth. COD and Razorpay-ready online checkout are implemented; production payment activation requires private Razorpay credentials and webhook/merchant configuration.

### Supabase database

Run `supabase/schema.sql` in the Supabase SQL editor before using the catalog API. Add product records and product image records to populate the storefront.


## Admin dashboard

The app now includes a protected admin route at `#admin` with:
- dashboard statistics for products, orders, customers and revenue
- inventory visibility
- product price/stock editing
- order list and status updates

For server-side admin operations, add `SUPABASE_SERVICE_ROLE_KEY` only to the **backend server environment**. Never put it in `frontend/.env.local` or commit it to GitHub.

After creating your first Supabase Auth account, create/update its profile role to `admin` in Supabase:

```sql
update profiles set role = 'admin' where id = 'YOUR_AUTH_USER_ID';
```

The admin API verifies the signed-in user's profile role before using the private server key.


## Production deployment

### Backend — Render
The repository includes `render.yaml`. Create the Render service from the repository and set the secret environment variables in Render, never in GitHub:
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CORS_ORIGINS`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`

### Frontend — Vercel
The repository includes `vercel.json`. Set these Vercel environment variables:
- `VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

After the Vercel URL is known, put that URL in the backend `CORS_ORIGINS` value.

### Online payments
Run `supabase/migrations/20261003_online_payments.sql` in the Supabase SQL editor. The payment flow creates the Seetharam order and calculates its amount on the server, creates a Razorpay order, opens Razorpay Checkout in the browser, and verifies the returned signature on the FastAPI backend. Razorpay's documentation recommends keeping API secrets out of version control and validating payment signatures server-side. 

Use Razorpay test credentials while developing. Do not put the key secret in `frontend/.env.local`, Vercel, browser code, or GitHub. Only the public key ID is returned to the browser. Before accepting real payments, configure the merchant account, production keys, HTTPS, and Razorpay webhook handling according to the current Razorpay documentation.
