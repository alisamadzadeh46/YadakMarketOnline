# YadakMarket Online

A multi-vendor marketplace for automotive spare parts. Independent suppliers
sell through one storefront to two kinds of buyers: retail customers, and
auto-parts shops that buy wholesale, on credit if the site owner allows it.
Every sale is split automatically between the supplier and the marketplace,
using a commission rate that is not fixed. The revenue-share partner can
change it within limits, set different rates for different buyer types, and
override it per category.

The backend is Django REST Framework and the storefront is Next.js. The whole
stack runs in Docker. The user interface is in Persian (right-to-left, Jalali
calendar). This documentation is in English.

![Storefront](docs/screenshots/storefront-shop.png)

## Contents

- [Highlights](#highlights)
- [Screenshots](#screenshots)
- [Features](#features)
  - [Roles](#roles)
  - [Multi-vendor marketplace](#multi-vendor-marketplace)
  - [Floating commission and revenue split](#floating-commission-and-revenue-split)
  - [Catalogue and storefront](#catalogue-and-storefront)
  - [Cart and checkout](#cart-and-checkout)
  - [Payments](#payments)
  - [Shop credit and settlement reminders](#shop-credit-and-settlement-reminders)
  - [Accounts, sign-in and KYC](#accounts-sign-in-and-kyc)
  - [Supplier panel](#supplier-panel)
  - [Site owner panel](#site-owner-panel)
  - [Revenue-share partner panel](#revenue-share-partner-panel)
  - [Blog and SEO](#blog-and-seo)
  - [Notifications](#notifications)
  - [Price comparison feeds](#price-comparison-feeds)
  - [Catalogue import tools](#catalogue-import-tools)
  - [Security](#security)
- [Architecture](#architecture)
- [Project layout](#project-layout)
- [Getting started](#getting-started)
- [Production deployment](#production-deployment)
- [Configuration](#configuration)
- [Management commands](#management-commands)
- [Background jobs](#background-jobs)
- [Testing and code quality](#testing-and-code-quality)
- [Protecting sensitive data](#protecting-sensitive-data)

## Highlights

- **Multi-vendor**: each supplier manages its own products, orders, coupons,
  reports and earnings. The site owner sees and controls the whole
  marketplace.
- **Floating commission**: a default rate that can move inside a min/max
  band, separate rates for shops and retail customers, and per-category
  overrides. The rate used for each order is saved with the order, so later
  changes never alter past orders.
- **Automatic revenue split**: every successful order records the
  marketplace's commission and each supplier's net share, line by line. VAT,
  shipping and supplier-specific coupons are handled correctly.
- **Wholesale features**: tiered volume pricing, minimum order quantities,
  carton sizes, KYC-approved shop accounts, credit limits with settlement
  deadlines and SMS reminders.
- **Three ways to pay**: card-to-card transfer with receipt upload and a
  payment countdown, online payment (ZarinPal or BitPay), and credit
  purchases.
- **Built-in blog and SEO tools**: a rich-text editor, a content analyzer
  similar to Yoast, a sitemap, structured data, and feeds for Iranian
  price-comparison sites.
- **Operations**: Celery workers with schedules you can edit in the admin
  panel, a rate-limited SMS queue, Flower, optional Sentry, and nginx with
  TLS and request limits.

## Screenshots

All screenshots use generated demo data.

### Storefront

| Home page | Product page |
| --- | --- |
| ![Home](docs/screenshots/storefront-home.png) | ![Product](docs/screenshots/storefront-product.png) |
| **Blog** | **Rare-part request** |
| ![Blog](docs/screenshots/storefront-blog.png) | ![Rare part](docs/screenshots/storefront-rare-part.png) |

<p align="center"><img src="docs/screenshots/storefront-mobile.png" alt="Mobile storefront" width="300"></p>

### Buying

| Cart | Checkout |
| --- | --- |
| ![Cart](docs/screenshots/customer-cart.png) | ![Checkout](docs/screenshots/customer-checkout.png) |
| **Card-to-card payment with countdown** | **Order history** |
| ![Order payment](docs/screenshots/customer-order-payment.png) | ![Orders](docs/screenshots/customer-orders.png) |
| **Shop dashboard** | **Shop credit and invoices** |
| ![Shop panel](docs/screenshots/shop-panel.png) | ![Shop credit](docs/screenshots/shop-credit.png) |

### Supplier panel

| Dashboard | Orders (with new-order alert) |
| --- | --- |
| ![Supplier dashboard](docs/screenshots/supplier-dashboard.png) | ![Supplier orders](docs/screenshots/supplier-orders.png) |
| **Products** | **Sales report** |
| ![Products](docs/screenshots/supplier-products.png) | ![Reports](docs/screenshots/supplier-reports.png) |
| **Earnings after commission** | **Supplier coupons** |
| ![Earnings](docs/screenshots/supplier-earnings.png) | ![Coupons](docs/screenshots/supplier-coupons.png) |

### Site owner panel

| Shop KYC review | Credit accounts and invoices |
| --- | --- |
| ![KYC](docs/screenshots/admin-kyc.png) | ![Credit](docs/screenshots/admin-credit.png) |
| **Settlement reminders** | **Categories and brands** |
| ![Settings](docs/screenshots/admin-settings.png) | ![Categories](docs/screenshots/admin-categories.png) |
| **Blog with SEO scores** | **SMS log and messages** |
| ![Blog admin](docs/screenshots/admin-blog-seo.png) | ![SMS](docs/screenshots/admin-sms.png) |
| **Online gateway** | **Payment methods per supplier** |
| ![Gateway](docs/screenshots/admin-gateway.png) | ![Payment methods](docs/screenshots/admin-payment-methods.png) |
| **VAT and shipping** | |
| ![Checkout costs](docs/screenshots/admin-checkout-costs.png) | |

### Revenue-share partner panel

| Revenue dashboard | Commission settings |
| --- | --- |
| ![Partner dashboard](docs/screenshots/partner-dashboard.png) | ![Commission settings](docs/screenshots/partner-commission-settings.png) |
| **Commission ledger** | |
| ![Ledger](docs/screenshots/partner-ledger.png) | |

## Features

### Roles

| Role | Who | What they can do |
| --- | --- | --- |
| `admin` | Site owner (superuser) | Everything: approves shops, grants credit, manages categories, blog, slider, payment settings and every supplier's orders. |
| `supplier` | A vendor | Manages their own products, orders, coupons and customers' rare-part requests. Sees their own reports and earnings. |
| `shopkeeper` | An auto-parts shop | Buys at wholesale once KYC is approved. Can buy on credit when the site owner opens a credit account for them. |
| `customer` | A retail buyer | Buys straight away, no approval needed. |
| `partner` | Revenue-share partner | Receives the marketplace commission and sets the commission rates from their own panel. |

The site owner can also be the commission beneficiary. In that case the
partner panel appears in the owner's menu as well.

### Multi-vendor marketplace

- Every product belongs to a supplier. Products without an owner show a
  configurable default seller name.
- Suppliers only ever see and change their own data. This covers products,
  orders that contain their products, coupons, the dashboard, sales reports
  and earnings. The access rules are covered by tests.
- An order can mix products from several suppliers. Only the site owner can
  move a shared order through its stages. Each supplier is notified by SMS
  about the lines that belong to them.
- Order status changes follow a fixed path: `pending payment → receipt
  uploaded → confirmed → processing → shipped → delivered`, plus `canceled`
  and `credit`. Transitions that skip steps are rejected.
- The marketplace collects every payment and pays suppliers their share,
  so buyers always pay into the marketplace's own card or gateway, never to
  an individual supplier.
- The site owner decides, per supplier, whether card-to-card payment is
  allowed. The option appears at checkout only if every supplier in the cart
  allows it, because one order has one payment method.
- A coupon created by the site owner applies to the whole marketplace. A
  coupon created by a supplier discounts only that supplier's products, and
  the discount comes out of that supplier's share only.

### Floating commission and revenue split

The marketplace commission is managed by the revenue-share partner from the
**Commission settings** page. Nothing is hard-coded.

**Choosing the rate.** For each order line, the most specific rule wins:

1. **Category rate.** Example: 15% on brake parts, 6% on oils.
2. **Buyer-type rate.** One rate for wholesale shops and another for retail
   customers.
3. **Default rate.** Set with a slider.

The default rate and the buyer-type rates must stay within a **min/max
band**, which is 5% to 20% by default and can also be changed. That is what
makes the rate "floating": it can move, but only inside limits both sides
have agreed to.

**The commission base.** Commission is charged on goods only. VAT and
shipping are part of the order total but are never included. A coupon
discount is spread across the lines it applies to, in proportion to their
value: every line for a site-wide coupon, or only the issuing supplier's
lines for a supplier coupon.

**Saved records.** When an order is confirmed, the platform saves:

- one `CommissionEntry` per order for the beneficiary: the base amount, the
  effective (blended) rate, the commission amount and the buyer type;
- one `OrderSupplierShare` per supplier in the order: the gross sales, the
  marketplace commission and the supplier's net amount.

These records are never recalculated when rates change, just as order line
prices are not.

**Status of a commission.**

| Status | Meaning |
| --- | --- |
| `earned` | The order is paid or confirmed. |
| `pending` | A credit order waiting for the shop to settle. Used only when *"recognise credit sales immediately"* is off. The record switches to `earned` automatically when the invoice is settled. |
| `paid` | The beneficiary has been paid. Marked from the ledger. |
| `void` | The order was canceled. |

**Worked example.** A retail customer checks out with:

| Line | Supplier | Goods | Rule used | Rate | Commission | Supplier net |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Brake pads | A | 2,000,000 − 10% supplier-A coupon = 1,800,000 | category | 15% | 270,000 | 1,530,000 |
| Spark plugs | B | 1,000,000 | customer rate | 12% | 120,000 | 880,000 |
| **Total** | | **2,800,000** | | **13.93% effective** | **390,000** | |

VAT and shipping are added to the customer's bill but do not appear in any
of these numbers. Supplier B's share is not reduced by supplier A's coupon.

**Reporting.**

- Partner dashboard: amount available to withdraw, this month's income
  (by Jalali month), total income, settled and pending amounts, a 14-day
  income chart, income by buyer type, and a table of sales and commission
  per supplier.
- Commission ledger: filter by status, buyer type and period, search by
  order number, mark rows as paid, and export to CSV.
- Supplier earnings page: gross sales, commission deducted and net payout
  for the current Jalali month and all time.
- Optional SMS to the partner whenever a new commission is recorded.

### Catalogue and storefront

- Brands, a two-level category tree, car makers and models for fitment,
  colours and sizes as fast filters, and any number of free-form
  specifications per product.
- Wholesale pricing: a base unit price, **tiered volume pricing** (a lower
  unit price from N pieces up), a **minimum order quantity**, the unit of
  sale, and the **carton size**.
- Product variants: different builds of the same part are linked together
  and shown as buttons on the product page. Each variant has its own SKU,
  price and stock.
- Stock tracking, compare-at (was) prices, featured products, authenticity
  and warranty labels, and a sales counter.
- Photo gallery with a zoom and pinch lightbox. Oversized uploads are
  resized.
- Shop filters: brand, category, colour, size, compatible car, carton size,
  price range, minimum rating, in stock and featured. Sorting by price,
  newest, rating and best-selling. Search suggestions appear as you type.
- A "find parts for my car" selector on the home page, a hero slider, and
  store statistics.
- Reviews with star ratings, published after the site owner approves them.
  Average ratings are stored on the product so listings load quickly.
- Favourites (wishlist).
- **Rare-part requests**: a buyer describes a part they cannot find
  (optionally with a photo). Suppliers are notified and answer from their
  panel.
- Static pages: buying guide, supplier cooperation, shipping, terms, privacy
  and contact. Contact form and newsletter sign-up.

### Cart and checkout

- The cart is stored on the server. Items added before signing in are kept
  and restored after login.
- The cart flags lines below the minimum order quantity or above the
  available stock, and checkout enforces both on the server.
- An address book with a map picker (Leaflet and OpenStreetMap by default)
  and one default address.
- Coupons (percentage or fixed amount, validity period, usage limits) are
  checked against the cart on the server. The client never sends the amount
  to discount.
- VAT rate and flat shipping cost are set by the site owner. Credit
  purchases carry no shipping charge.
- Stock is reserved when the order is placed. The product rows are locked
  during checkout, so two buyers cannot both buy the last item.
- A printable invoice for every order, and "order again" from the order
  history.

### Payments

- **Card-to-card**: the buyer is shown the marketplace's bank card and a
  countdown (default 30 minutes, set with
  `PAYMENT_RECEIPT_WINDOW_MINUTES`). They upload a photo of the bank
  receipt, and the supplier or site owner confirms it. Receipt images are
  stored privately. The option is offered only after the site owner has
  entered the card on the settings page.
- **Online payment**: ZarinPal or BitPay. The site owner chooses the active
  gateway and enters the merchant credentials in the panel. They are stored
  in the database, not in environment files. Both gateways support sandbox
  mode.
- **Credit**: available to approved shops that have an active credit
  account and enough remaining credit. The account row is locked during
  checkout, so two orders placed at the same moment cannot both use the
  same credit.
- **Automatic expiry**: unpaid orders are canceled when their payment time
  runs out, and their stock goes back on sale. If an online payment is
  confirmed after the order has expired, the order is reopened when the
  stock is still available. If it is not, the payment is logged for a
  refund and the site owner is notified.
- Trust badges (eNamad, ZarinPal, BitPay) are shown in the footer only when
  they are configured.

### Shop credit and settlement reminders

- The site owner opens a **credit account** for an approved shop, with a
  credit limit and a number of days to settle (for example 7 or 30).
- Every credit order creates a **credit invoice** with a due date. The shop
  sees its open and settled invoices, its outstanding balance and its next
  due dates in the shop panel.
- The site owner marks invoices as settled. Settling an invoice also moves
  its commission and supplier shares from `pending` to `earned`.
- **SMS reminders** are sent a configurable number of days before the due
  date. The owner edits the lead time and the message template in the panel
  (placeholders: shop name, amount, Jalali due date, days left and site
  name). The time of day is a periodic task that can be changed in the
  Django admin. A reminder can also be sent immediately with one click.

### Accounts, sign-in and KYC

- Users register with a mobile number and password. Passwords are hashed
  with Argon2.
- JWT tokens are kept in **HttpOnly cookies**, never in `localStorage`.
  Refresh tokens rotate and old ones are blacklisted. Requests that change
  data are protected against CSRF.
- Password reset works through a 6-digit SMS code or an e-mailed link.
  Codes expire quickly, work once, and are limited per phone number to stop
  guessing. Codes are hidden in the SMS log.
- **KYC for shops**: a shop registers, adds its business details, and
  uploads its national card, business licence and shop photos. The site
  owner reviews and approves or rejects the documents. Documents are stored
  privately and opened through short-lived signed links.

### Supplier panel

- **Dashboard**: product count, order count, receipts waiting for approval,
  credit receivables, a 7-day sales chart, and a low-stock forecast based on
  sales over the last 30 days.
- **New-order alert**: while orders are waiting for confirmation, the panel
  plays a chime, shows a notice and flashes the browser tab title. SMS
  reminders repeat until the order is handled.
- **Orders**: filters, search and pagination. Confirm receipts, then process,
  ship, deliver or cancel. Order details include the buyer's address pinned
  on a map.
- **Products**: create and edit products with photo gallery, price tiers,
  specifications, colours, compatible cars and variants.
- **Sales report**: choose a period (last 7, 30 or 90 days) and see revenue, orders,
  average order value, cancellations, a daily chart, best-selling products
  and a breakdown by status. Exports to CSV.
- **Earnings**: sales, commission deducted and net payout.
- **Coupons** for the supplier's own products, **rare-part requests**, and
  the supplier's profile.

### Site owner panel

The site owner uses the same panel with extra pages:

- Shop KYC review and approval.
- Credit accounts, credit invoices and settlement reminders.
- Categories, brands and blog categories. Deleting a category or brand that
  products still use is refused with a clear message.
- The blog editor with SEO analysis, and the home page slider.
- Communication: SMS log, contact form messages and newsletter subscribers.
- Settings: the marketplace bank card for card-to-card payments, settlement
  reminder and new-order SMS templates, the active online gateway and its
  credentials, card-to-card on or off per supplier, VAT rate and shipping
  cost.
- The full Django admin at a configurable, non-default URL.

### Revenue-share partner panel

- Revenue dashboard, commission ledger with CSV export, and commission
  settings. Details are in
  [Floating commission and revenue split](#floating-commission-and-revenue-split).
- The partner can see sales and commission per supplier, but cannot reach
  the site owner's payment settings or other site-wide settings.

### Blog and SEO

- Blog posts with categories, cover images, a rich-text editor with image
  upload, reading time, search and sorting.
- Views are counted once per visitor.
- Newsletter subscribers are e-mailed when a post is published.
- **Yoast-style analyzer** (understands Persian text) with a 0–100 score and a
  checklist: focus keyword in the title, meta description, slug and first
  paragraph, keyword density, title and meta description length, content
  length, headings, links, image alt text, and readability. It also
  suggests fixes for the meta title, meta description and slug.
- Storefront SEO: server-rendered pages, a generated `sitemap.xml` and
  `robots.txt`, canonical URLs, Open Graph tags, and JSON-LD for products,
  the organisation and breadcrumbs.

### Notifications

- SMS goes through a swappable backend. It prints to the console in
  development and uses Niazpardaz in production. Adding another provider
  means writing one class.
- All SMS go through a dedicated queue that sends them at a configured rate
  (`SMS_RATE_LIMIT`), so large batches of reminders never overload the
  provider. Failed sends are retried.
- Every SMS is recorded in a log with its type: order, settlement reminder,
  verification code, commission or other.
- HTML e-mails (password reset, new blog posts). Values inside them are
  escaped, and branding comes from settings.

### Price comparison feeds

- `GET /api/catalog/feed/`: a paginated JSON feed in the Emalls format. It
  contains only public data (no stock levels, supplier details or cost
  prices) and limits the page size.
- Product pages include the meta tags that Torob and IranMarket read.

### Catalogue import tools

Management commands for loading and cleaning catalogue data:

- Import or refresh products from an Excel price list.
- Attach photos by SKU.
- Convert Arabic letters to their Persian forms.
- Move fitment lists and bracketed specifications out of product names.
- Resize oversized images.
- Remove demo data.

See [Management commands](#management-commands).

### Security

- Permissions are checked by role, and data is filtered so each user only
  sees their own records. Site-wide settings are limited to the site owner.
  Tests cover these rules.
- Row-level locking and atomic updates protect stock, credit, coupons and
  order status when requests happen at the same time.
- Private files (KYC documents, receipts) are never served directly by nginx.
  They are opened through signed links that expire.
- API requests are throttled per client, with stricter limits per phone
  number and e-mail for password-reset codes. In production, nginx adds
  tighter request limits on sign-in, registration and password reset.
- Redirects after login only go to pages on this site.
- Production settings: HTTPS redirect, HSTS, secure cookies, `nosniff`,
  `X-Frame-Options: DENY`, and a secret admin path (`ADMIN_URL`). The API
  schema and Swagger UI are not published in production.
- All secrets come from environment variables or the database. None are in
  the code.

## Architecture

```
                 ┌──────────────── nginx (TLS, rate limits, static/media) ────────────────┐
                 │                                                                        │
          Next.js 16 (SSR, RTL)  ── /api ──▶  Django 5.2 + DRF (gunicorn)                 │
                                                   │                                      │
             ┌──────────────┬──────────────┬───────┴───────┬───────────────┐              │
        PostgreSQL 17     Redis 8      RabbitMQ 4*    Celery workers    Celery beat       │
          (data)      (cache, results)  (broker)     (default + sms)  (DB scheduler)      │
                                                                                          │
        * development only; production uses Redis as the broker to save memory ───────────┘
```

| Layer | Technology |
| --- | --- |
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework 3.17, SimpleJWT, django-filter, drf-spectacular |
| Tasks | Celery 5.6, django-celery-beat (schedules stored in the database and editable in the admin), Flower |
| Data | PostgreSQL 17, Redis 8 |
| Frontend | Next.js 16 (App Router), React 19, TypeScript 5, Leaflet |
| Infrastructure | Docker Compose, nginx, gunicorn, WhiteNoise, optional Sentry |

Django stays on the 5.2 LTS line, which has security support until 2028,
because django-celery-beat does not support Django 6 yet. Fonts and scripts
are bundled with the app, so the storefront does not depend on third-party
CDNs.

## Project layout

```
backend/
  config/            settings (base, dev, prod), URLs, Celery app
  apps/
    accounts/        users, roles, KYC, addresses, cookie JWT auth, password reset
    catalog/         products, pricing tiers, facets, reviews, favourites, rare parts, feeds
    orders/          cart, checkout, orders, receipts, VAT/shipping, expiry sweep
    payments/        ZarinPal / BitPay gateways, transactions, callbacks
    suppliers/       dashboards, reports, earnings, credit accounts, invoices, reminders
    commissions/     floating commission engine, ledger, per-supplier shares
    discounts/       coupons and redemptions
    blog/            posts, categories, unique view counting
    seo/             content analyzer
    cms/             slider, contact messages, newsletter
    notifications/   SMS backends, SMS log, e-mails
    core/            shared models, Jalali date helpers, protected media
frontend/
  app/               storefront, account, and the supplier / shop / partner panels
  components/        UI components (lightbox, rich editor, map picker, Jalali picker, ...)
  lib/               API client, site configuration, formatting helpers
nginx/               development config and production config template
tools/repo_guard/    pre-commit / pre-push scanner for sensitive data
docs/screenshots/    images used in this README
```

## Getting started

Requirements: Docker with the Compose plugin. Python 3.9 or newer is needed
only for the git hooks.

```bash
git clone https://github.com/alisamadzadeh46/YadakMarketOnline.git
cd YadakMarketOnline

cp .env.example .env                       # set at least DJANGO_SECRET_KEY and POSTGRES_PASSWORD
python -m tools.repo_guard install-hooks   # enable the sensitive-data checks

docker compose up --build
docker compose exec web python manage.py createsuperuser   # the site owner (mobile number + password)
docker compose exec web python manage.py seed_demo         # optional demo catalogue
```

| Service | URL |
| --- | --- |
| Storefront | http://localhost:3010 |
| API | http://localhost:8020/api/ |
| API documentation (Swagger) | http://localhost:8020/api/docs/ |
| Django admin | http://localhost:8020/admin/ (or your `ADMIN_URL`) |
| Everything through nginx | http://localhost:8090 |
| RabbitMQ management | http://localhost:15672 |
| Flower | http://localhost:5555 |

To set up the first supplier and the revenue-share partner:

```bash
docker compose exec web python manage.py create_supplier --phone 09xxxxxxxxx --name "Supplier name"
docker compose exec web python manage.py setup_partner --phone 09xxxxxxxxx --email partner@example.com --rate 10
```

## Production deployment

```bash
cp .env.example .env.prod          # production values: DEBUG=False, strong secrets, real domain
# place the TLS certificate at nginx/certs/fullchain.pem and nginx/certs/privkey.pem
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Set `ADMIN_URL` in `.env.prod` to a random path such as `x7k2p9q4/`. The
same value configures Django and is filled into `nginx/prod.conf.template`
when nginx starts. The default `/admin/` path answers 404.

The production stack exposes only nginx on ports 80 and 443. PostgreSQL,
Redis and the application containers are reachable only on the internal
Docker network. Redis is the Celery broker, and a separate single-slot
worker sends SMS from the `sms` queue.

## Configuration

All settings come from environment variables. `.env.example` lists each one
with an explanation. The main groups:

| Group | Variables |
| --- | --- |
| Django | `DJANGO_SECRET_KEY`, `DJANGO_SETTINGS_MODULE`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `ADMIN_URL`, `FRONTEND_URL` |
| Branding (backend) | `SITE_NAME`, `SITE_SHORT_NAME`, `SITE_TAGLINE`, `SITE_ADDRESS`, `DEFAULT_SELLER_NAME` |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` |
| Cache and tasks | `REDIS_URL`, `REDIS_PASSWORD`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Orders | `PAYMENT_RECEIPT_WINDOW_MINUTES` |
| SMS | `SMS_PROVIDER`, `NIAZPARDAZ_USERNAME`, `NIAZPARDAZ_PASSWORD`, `NIAZPARDAZ_LINE_NUMBER`, `SMS_RATE_LIMIT`, `DEFAULT_SETTLEMENT_REMINDER_DAYS` |
| E-mail | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` |
| Security and monitoring | `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `JWT_COOKIE_DOMAIN`, `SENTRY_DSN` |
| Storefront (build time) | `PUBLIC_ORIGIN`, `NEXT_PUBLIC_SITE_NAME`, `NEXT_PUBLIC_SITE_SHORT_NAME`, `NEXT_PUBLIC_SITE_TAGLINE`, `NEXT_PUBLIC_SELLER_NAME`, `NEXT_PUBLIC_MAP_TILES` |
| Contact details | `NEXT_PUBLIC_CONTACT_PHONES`, `NEXT_PUBLIC_CONTACT_CITY`, `NEXT_PUBLIC_CONTACT_ADDRESS`, `NEXT_PUBLIC_CONTACT_HOURS`, `NEXT_PUBLIC_TELEGRAM_URL`, `NEXT_PUBLIC_BALE_URL` |
| Trust badges | `NEXT_PUBLIC_ENAMAD_ID`, `NEXT_PUBLIC_ENAMAD_CODE`, `NEXT_PUBLIC_ENAMAD_META`, `NEXT_PUBLIC_BITPAY_TRUST_URL`, `NEXT_PUBLIC_ZARINPAL_TRUST_URL` |

Some settings are changed in the panel rather than in environment
variables. They are stored in the database, so changing them needs no
redeploy:

- online gateway choice and merchant credentials;
- card-to-card on or off per supplier;
- VAT and shipping;
- commission rates;
- settlement reminder template and schedule;
- slider content.

Business data such as sellers, shops, addresses and phone numbers lives only
in the database. It is never in the source code, fixtures or migrations.

## Management commands

| Command | Purpose |
| --- | --- |
| `create_supplier --phone … [--name …]` | Create or update a supplier account and set up its order notifications. |
| `setup_partner --phone … --email … [--rate 10 --min-rate 5 --max-rate 20]` | Create the revenue-share partner and set up the commission settings. |
| `seed_demo` | Add a demo catalogue: brands, cars, categories and about 40 products. |
| `import_pricelist <file.xlsx> [--dry-run]` | Import or refresh products from a supplier's Excel price list. |
| `import_venda --supplier …` | Import a parsed brake-parts list for a given supplier. |
| `import_part_images` | Attach photos to products by SKU, using a manifest. |
| `normalize_text` | Replace Arabic letters with their Persian forms in all catalogue text. |
| `clean_product_names`, `tidy_names` | Move fitment lists and bracketed specifications out of product names. |
| `resize_images` | Shrink oversized product images and save them again. |
| `cleanup_demo`, `purge_catalog` | Remove demo products, or clear the catalogue completely. |

Run them with `docker compose exec web python manage.py <command>`.

## Background jobs

These periodic tasks are created automatically. Their schedules can be
changed in the Django admin (*Periodic tasks*).

| Task | Default schedule | What it does |
| --- | --- | --- |
| `close_expired_orders` | every minute | Cancels unpaid orders whose payment time is over and puts their stock back on sale. |
| `send_settlement_reminders` | daily at 10:00 | Sends SMS reminders for credit invoices that are almost due. |
| `remind_pending_orders` | every 15 minutes | Sends the new-order SMS again for orders nobody has confirmed. |

Tasks that run when something happens: notifying suppliers of new orders
and rare-part requests, notifying newsletter subscribers of new posts,
sending password-reset e-mails, and sending SMS through the `sms` queue.

## Testing and code quality

```bash
# Backend: access rules, checkout, payments, credit, commissions, SEO and more
docker compose exec web python manage.py test

# Backend lint and format (configured in ruff.toml)
ruff check backend && ruff format --check backend

# Frontend
cd frontend && npm run typecheck && npm run lint && npm run build
```

Code, comments and docstrings are in English. Comments explain *why*
something is done; the code itself should make *what* obvious.

## Protecting sensitive data

This repository is public. The following must never be committed:

- `.env` files, credentials, API keys, private keys and certificates;
- payment gateway merchant IDs and SMS panel usernames, passwords or keys;
- trust badge (eNamad) IDs and codes;
- real phone numbers, e-mail addresses, postal addresses and server
  addresses;
- database files, dumps, exports and backups;
- uploaded media (product photos, KYC documents, receipts);
- personal data of customers and sellers.

### How it is enforced

1. **`.gitignore`** keeps the usual sensitive files out of `git add`.
2. **Git hooks** in `.githooks/`, enabled with
   `python -m tools.repo_guard install-hooks`:
   - `pre-commit` scans staged files and their content;
   - `commit-msg` scans the commit message;
   - `pre-push` scans every commit about to be pushed again.
3. **CI** (`.github/workflows/repo-guard.yml`) runs the same checks on every
   push and pull request.

The hooks look for Python in `venv/` or `.venv/` inside the repository, then
on the `PATH`. If neither works (for example, a broken `python` alias on
Windows), set the interpreter explicitly:

```bash
git config repo-guard.python "C:/path/to/python.exe"
```

The rules are in `tools/repo_guard/rules.py`. Each rule is a small
declarative object. To add a check, append it to `PATH_RULES` or
`CONTENT_RULES`.

### Project-specific values

Generic patterns cannot recognise a shop name or a street address. List such
values, one per line, in `.repo-guard.local` at the repository root. The file
is git-ignored and only read on your machine:

```text
# Real values that must never appear in the repository
<shop phone number>
<shop address>
<server IP address>
<payment gateway merchant ID>
<SMS panel username or key>
<seller or shop names>
```

Numbers match regardless of spacing, dashes, Persian digits or a `+98`
prefix. Text matches regardless of case.

### Importing existing code

To publish code written before the guard existed, copy it into a clone of
this repository and run:

```bash
python -m tools.repo_guard prepare
```

The command shows a plan and applies it only after you confirm:

- sensitive values are replaced with `__REDACTED__`, and the original values
  are saved to `.redactions.local` (git-ignored) so you can move them into
  `.env`;
- files that must not be published, and data files such as fixtures or CSV
  exports, are held back for manual review;
- virtual environments not covered by `.gitignore` are excluded;
- everything else is staged, ready for `git commit` and `git push`.

### Useful commands

```bash
python -m tools.repo_guard all              # check every file that would be committed
python -m tools.repo_guard history          # check every commit in the local history
python -m tools.repo_guard range main..HEAD
python -m unittest discover -s tools -t .   # run the guard's own tests
```

If a match is a confirmed false positive, add a comment containing
`repo-guard: allow` to that line. Never bypass the hooks with `--no-verify`.

### If something leaks

1. First revoke or rotate the exposed value (merchant key, SMS password,
   server password, secret key). Rewriting history does not remove copies
   that were already fetched or cached.
2. Remove the value from the code and load it from `.env` or the database.
3. Rewrite the affected commits before pushing again.
