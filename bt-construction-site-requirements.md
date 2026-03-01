# BT Construction LLC — Static Site Generator & Admin Panel
## EARS Requirements Specification
### Version 1.0 | February 2026

---

## 1. Project Overview

### 1.1 Purpose
A custom static site generator with a lightweight admin panel for BT Construction LLC (btconstructiontx.com), a 50-year family construction and remodeling business serving Dallas, Plano, and Carrollton, TX. The system replaces WordPress with a purpose-built solution that enables Calvin Berry to manage website content through a simple web interface while serving visitors a blazing-fast static HTML site.

### 1.2 Business Context
- **Company:** BT Construction LLC
- **Owner:** Calvin Berry (50 years experience)
- **Project Manager:** David Berry
- **Domain:** btconstructiontx.com
- **Tagline:** "Integrity with results!"
- **Process:** Design. Analyze. Estimate. Complete.
- **Service Area:** Dallas, Plano, Carrollton (DFW Metroplex)
- **Core Services:** Kitchen remodels, bathroom remodels, renovation/restoration
- **Design Direction:** Clean and professional — navy (#1B3A5C), white (#FFFFFF), gray (#F5F5F5), accent gold (#C8963E)

### 1.3 Architecture Summary
```
┌─────────────────────────────────────────────────────────┐
│                    Linode VPS ($5/mo)                    │
│                   Ubuntu 24.04 LTS                      │
│                                                         │
│  ┌──────────────┐    ┌──────────────────────────────┐   │
│  │    Nginx     │    │     Flask Admin Panel         │   │
│  │ (port 80/443)│    │     (port 5000, local)       │   │
│  │              │    │                              │   │
│  │ Serves:      │    │  • Content CRUD              │   │
│  │ /var/www/    │    │  • Image upload/optimize     │   │
│  │  btconst/    │    │  • Static site rebuild       │   │
│  │  site/       │    │  • Form submission viewer    │   │
│  │              │    │                              │   │
│  │ Proxies:     │    │  Stores:                     │   │
│  │ /admin/* ──────────▶ JSON/MD in /data/           │   │
│  └──────────────┘    └──────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Static Site Generator               │   │
│  │         (Python + Jinja2 templates)              │   │
│  │                                                  │   │
│  │  /data/ (JSON/MD) + /templates/ (Jinja2)         │   │
│  │        ──▶ /var/www/btconst/site/ (HTML)         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 1.4 Technology Stack
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| OS | Ubuntu 24.04 LTS | Long-term support, stable |
| Web Server | Nginx | Fast static file serving, reverse proxy |
| Admin Backend | Python 3.12 + Flask | Lightweight, easy to maintain |
| Templating | Jinja2 | Native Python, powerful, familiar syntax |
| Image Processing | Pillow | Resize, optimize, create thumbnails |
| CSS Framework | Tailwind CSS (CDN) | Utility-first, no build step needed |
| Forms | Self-hosted (Flask) | No external dependencies |
| Email | SMTP (Gmail/SendGrid) | Reliable, free tier |
| SSL | Let's Encrypt (Certbot) | Free, auto-renewing |
| Data Storage | JSON files + Markdown | No database, easy backup, git-friendly |

---

## 2. Requirements (EARS Format)

### 2.1 System-Level Requirements

#### SYS-001: Static Site Generation
**When** content is created, updated, or deleted via the admin panel, **the system shall** regenerate all affected static HTML pages and deploy them to the Nginx web root within 10 seconds.

#### SYS-002: Admin Panel Access
**The system shall** provide a password-protected web admin panel accessible at `btconstructiontx.com/admin` that requires authentication before any content modification.

#### SYS-003: No Database Dependency
**The system shall** store all content as JSON files and Markdown files in a `/data/` directory, with no relational database required for production operation.

#### SYS-004: Image Optimization
**When** an image is uploaded through the admin panel, **the system shall** automatically create:
- A full-size optimized version (max 1920px wide, 80% JPEG quality)
- A thumbnail version (400px wide, 70% JPEG quality)
- A WebP version for modern browsers

#### SYS-005: Mobile Responsive
**The system shall** generate HTML pages that render correctly on viewports from 320px to 2560px wide.

#### SYS-006: SEO Foundation
**The system shall** generate pages with proper meta titles, meta descriptions, Open Graph tags, structured data (LocalBusiness schema), and semantic HTML5 markup.

#### SYS-007: Performance Target
**The system shall** generate pages that achieve a Lighthouse performance score of 90+ on mobile, with First Contentful Paint under 1.5 seconds.

#### SYS-008: SSL/HTTPS
**The system shall** serve all pages over HTTPS with automatic HTTP-to-HTTPS redirect, using a Let's Encrypt certificate with auto-renewal.

#### SYS-009: Backup
**The system shall** support backup via simple directory copy of `/data/` and `/uploads/`, enabling full site restoration from filesystem backup.

---

### 2.2 Public Website Pages

#### PAGE-001: Homepage
**The system shall** generate a homepage containing:
- Hero section with background image, business name, tagline ("Integrity with results!"), and primary CTA ("Get a Free Estimate")
- Calvin Berry's years of experience callout (50 years)
- Featured services section (3 cards: Kitchen Remodels, Bathroom Remodels, Renovations)
- Recent portfolio projects (3 most recent, with photos)
- Testimonials carousel (3 most recent)
- Service area mention (Dallas, Plano, Carrollton)
- Contact/quote CTA section
- Phone number prominent in header and footer

#### PAGE-002: Services Landing Page
**The system shall** generate a services page listing all active services, each displaying:
- Service title
- Service description (supports Markdown formatting)
- Key features/bullet points
- Representative photo
- Link to relevant portfolio items
- CTA to request a quote for that service type

#### PAGE-003: Individual Service Pages
**When** a service is created in the admin panel, **the system shall** generate a dedicated page at `/services/{slug}` containing the full service description, photo gallery, related portfolio projects, and a quote request CTA.

#### PAGE-004: Portfolio/Gallery Page
**The system shall** generate a portfolio page displaying all published projects in a filterable grid layout with:
- Filter buttons by category (Kitchen, Bathroom, Commercial, Other)
- Project card showing primary photo, title, category, and brief description
- Click-through to individual project detail pages

#### PAGE-005: Individual Project Pages
**When** a project is created in the admin panel, **the system shall** generate a dedicated page at `/portfolio/{slug}` containing:
- Project title, category, and description
- Before/after photo comparison (side-by-side or slider)
- Full photo gallery with lightbox
- Scope of work details
- Related projects

#### PAGE-006: About Page
**The system shall** generate an about page containing:
- Calvin Berry's story and 50 years of experience
- "Design. Analyze. Estimate. Complete." process explanation
- Family-owned business narrative
- Licensing and registration information
- Team photo (optional)
- Company values

#### PAGE-007: Blog/News Page
**The system shall** generate a blog index page at `/blog/` displaying published posts in reverse chronological order, with title, date, excerpt, and featured image.

#### PAGE-008: Individual Blog Posts
**When** a blog post is published via the admin panel, **the system shall** generate a page at `/blog/{slug}` with the full post content, date, featured image, and navigation to previous/next posts.

#### PAGE-009: Contact Page
**The system shall** generate a contact page containing:
- Contact form (name, email, phone, message)
- Phone number (clickable on mobile)
- Email address
- Service area map or list
- Business hours

#### PAGE-010: Quote Request Page
**The system shall** generate a dedicated quote request page at `/get-a-quote` containing a structured form with:
- Customer name, email, phone
- Project type (dropdown: Kitchen Remodel, Bathroom Remodel, Renovation, Commercial, Other)
- Project description (textarea)
- Preferred timeline (dropdown: ASAP, 1-3 months, 3-6 months, Just exploring)
- Budget range (dropdown: Under $10K, $10K-$25K, $25K-$50K, $50K+, Not sure)
- How they heard about BT Construction
- Photo upload capability (up to 5 images)

---

### 2.3 Admin Panel Requirements

#### ADMIN-001: Authentication
**The system shall** require username/password authentication to access the admin panel, using bcrypt-hashed passwords stored in a server-side configuration file.

#### ADMIN-002: Admin Dashboard
**When** an authenticated user accesses `/admin`, **the system shall** display a dashboard with:
- 6 large, clearly labeled navigation cards (Portfolio, Testimonials, Services, Blog, Contact Submissions, Quote Requests)
- Count of items in each section
- Count of unread form submissions
- Last site rebuild timestamp
- One-click "Rebuild Site" button

#### ADMIN-003: Portfolio Management
**The system shall** provide a portfolio management interface allowing the admin to:
- **Create** a new project: title, category (Kitchen/Bathroom/Commercial/Other), description (Markdown), before photos (upload multiple), after photos (upload multiple), scope of work, featured flag, publish/draft status
- **Edit** any existing project field
- **Delete** a project (with confirmation prompt)
- **Reorder** projects via drag-and-drop or sort order number
- **Preview** the project page before publishing

#### ADMIN-004: Testimonial Management
**The system shall** provide a testimonial management interface allowing the admin to:
- **Create** a testimonial: customer first name, last initial, quote text, star rating (1-5, optional), project type, date, featured flag
- **Edit** any existing testimonial
- **Delete** a testimonial (with confirmation)
- **Toggle** visibility (show/hide on site)

#### ADMIN-005: Service Page Management
**The system shall** provide a service page editor allowing the admin to:
- **Edit** service title, description (Markdown), key features, representative photo
- **Add/remove** services
- **Reorder** services
- **Toggle** active/inactive status

#### ADMIN-006: Blog/News Management
**The system shall** provide a blog management interface allowing the admin to:
- **Create** a post: title, body (Markdown with simple rich text toolbar — bold, italic, headers, links, image insert), featured image upload, publish date, publish/draft status
- **Edit** existing posts
- **Delete** posts (with confirmation)

#### ADMIN-007: Contact Form Submissions
**When** a visitor submits the contact form, **the system shall**:
- Send an email notification to the configured business email address with all form fields
- Store the submission in `/data/submissions/contact/` as a JSON file
- Display submissions in the admin panel with read/unread status, newest first

#### ADMIN-008: Quote Request Submissions
**When** a visitor submits the quote request form, **the system shall**:
- Send an email notification to the configured business email address with all form fields and any uploaded photos as attachments or links
- Store the submission in `/data/submissions/quotes/` as a JSON file with uploaded images
- Display submissions in the admin panel with read/unread status, newest first, with inline image viewing

#### ADMIN-009: Image Upload
**When** the admin uploads an image in any content section, **the system shall**:
- Accept JPEG, PNG, and WebP formats up to 15MB per file
- Validate file type and size before processing
- Auto-rotate based on EXIF orientation
- Strip EXIF data (privacy)
- Generate optimized versions per SYS-004
- Display upload progress and preview
- Store originals in `/uploads/originals/` and processed versions in `/uploads/processed/`

#### ADMIN-010: Site Rebuild
**When** the admin clicks "Rebuild Site" or saves/publishes content, **the system shall**:
- Regenerate all static HTML pages from current data and templates
- Display rebuild status (building/complete/error)
- Log rebuild time and any errors
- Not disrupt the live site during rebuild (build to temp directory, then swap)

#### ADMIN-011: Basic Settings
**The system shall** provide a settings page allowing the admin to edit:
- Business phone number
- Business email address
- Business hours
- Service area cities
- Social media links (Facebook, Instagram)
- Google Business Profile link (when ready)

---

### 2.4 Form & Email Requirements

#### FORM-001: Form Validation
**The system shall** validate all form submissions both client-side (JavaScript) and server-side (Flask) before processing, requiring at minimum: name, email (valid format), and message/description.

#### FORM-002: Spam Prevention
**The system shall** implement spam prevention using a honeypot field and rate limiting (max 5 submissions per IP per hour), without requiring a CAPTCHA.

#### FORM-003: Email Delivery
**The system shall** send email notifications via SMTP (configurable — Gmail App Password or SendGrid API) with:
- Clear subject line indicating form type (e.g., "New Quote Request — Kitchen Remodel")
- All submitted fields formatted readably
- Reply-to set to the submitter's email address

#### FORM-004: Form Confirmation
**When** a form is successfully submitted, **the system shall** display a confirmation message to the visitor and optionally redirect to a thank-you page.

---

### 2.5 SEO & Analytics Requirements

#### SEO-001: Meta Tags
**For each** generated page, **the system shall** include:
- Unique `<title>` tag (format: "Page Title | BT Construction LLC — Dallas, TX")
- Unique `<meta name="description">` (150-160 characters)
- `<meta name="robots" content="index, follow">`
- Canonical URL

#### SEO-002: Open Graph Tags
**For each** generated page, **the system shall** include Open Graph tags (og:title, og:description, og:image, og:url, og:type) for social media sharing.

#### SEO-003: Structured Data
**The system shall** include JSON-LD structured data on the homepage for:
- LocalBusiness schema (name, address, phone, service area, hours, rating)
- Service schema for each service page
- Review schema for testimonials

#### SEO-004: Sitemap
**When** the site is rebuilt, **the system shall** generate an XML sitemap at `/sitemap.xml` listing all public pages with last-modified dates.

#### SEO-005: Robots.txt
**The system shall** generate a `/robots.txt` file that allows crawling of all public pages, disallows `/admin/`, and references the sitemap.

#### SEO-006: Analytics Integration
**The system shall** support optional Google Analytics 4 and/or Google Tag Manager integration via a configurable tracking ID in admin settings.

---

### 2.6 Non-Functional Requirements

#### NFR-001: Hosting
**The system shall** run on a single Linode Nanode ($5/mo, 1GB RAM, 1 CPU, 25GB storage) with Ubuntu 24.04 LTS.

#### NFR-002: Resource Usage
**The system shall** consume less than 512MB RAM during normal operation (Nginx + Flask admin panel idle).

#### NFR-003: Security — Admin Panel
**The system shall** protect the admin panel with:
- HTTPS-only access
- Bcrypt password hashing
- Session timeout after 30 minutes of inactivity
- Rate-limited login attempts (5 per minute)
- CSRF protection on all forms

#### NFR-004: Security — Static Site
**The system shall** configure Nginx with security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy` (appropriate for static site)
- `Strict-Transport-Security` (HSTS)

#### NFR-005: Maintainability
**The system shall** be structured as a single Python project with clear separation:
```
/opt/btconstruction/
├── app.py                  # Flask admin application
├── generator.py            # Static site generator
├── config.py               # Configuration (SMTP, paths, etc.)
├── requirements.txt        # Python dependencies
├── templates/
│   ├── admin/              # Admin panel templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── portfolio_edit.html
│   │   ├── testimonials.html
│   │   ├── services_edit.html
│   │   ├── blog_edit.html
│   │   ├── submissions.html
│   │   └── settings.html
│   └── site/               # Public site templates
│       ├── base.html
│       ├── home.html
│       ├── services.html
│       ├── service_detail.html
│       ├── portfolio.html
│       ├── project_detail.html
│       ├── about.html
│       ├── blog.html
│       ├── blog_post.html
│       ├── contact.html
│       └── quote.html
├── static/
│   ├── css/
│   ├── js/
│   └── img/                # Site design assets (logo, icons)
├── data/
│   ├── portfolio/          # Project JSON files
│   ├── testimonials/       # Testimonial JSON files
│   ├── services/           # Service JSON files
│   ├── blog/               # Blog post Markdown + frontmatter
│   ├── submissions/        # Form submissions
│   │   ├── contact/
│   │   └── quotes/
│   └── settings.json       # Site-wide settings
└── uploads/
    ├── originals/          # Unprocessed uploads
    └── processed/          # Optimized images + thumbnails
```

#### NFR-006: Deployment
**The system shall** be deployable via a single setup script (`setup.sh`) that:
- Installs system dependencies (Nginx, Python 3.12, Certbot)
- Creates Python virtual environment and installs packages
- Configures Nginx (static site + admin reverse proxy + SSL)
- Sets up systemd service for the Flask admin
- Initializes data directories with seed content
- Runs initial site build
- Configures SSL via Certbot

---

## 3. Data Schemas

### 3.1 Project (Portfolio)
```json
{
  "id": "uuid-string",
  "title": "Master Bathroom Renovation",
  "slug": "master-bathroom-renovation",
  "category": "bathroom",
  "description": "Markdown content here...",
  "scope_of_work": "Full gut renovation including...",
  "photos_before": ["uuid-1.jpg", "uuid-2.jpg"],
  "photos_after": ["uuid-3.jpg", "uuid-4.jpg"],
  "featured": true,
  "status": "published",
  "sort_order": 1,
  "created_at": "2026-02-28T12:00:00Z",
  "updated_at": "2026-02-28T12:00:00Z"
}
```

### 3.2 Testimonial
```json
{
  "id": "uuid-string",
  "customer_name": "Sarah M.",
  "quote": "The attention to detail was outstanding...",
  "rating": 5,
  "project_type": "kitchen",
  "date": "2026-01-15",
  "featured": true,
  "visible": true,
  "created_at": "2026-02-28T12:00:00Z"
}
```

### 3.3 Service
```json
{
  "id": "uuid-string",
  "title": "Kitchen Remodels",
  "slug": "kitchen-remodels",
  "description": "Markdown content...",
  "features": ["Custom cabinetry", "Countertop installation", "Lighting design"],
  "photo": "kitchen-hero.jpg",
  "active": true,
  "sort_order": 1
}
```

### 3.4 Blog Post
```markdown
---
id: uuid-string
title: "5 Signs Your Kitchen Needs a Remodel"
slug: 5-signs-kitchen-needs-remodel
date: 2026-02-28
featured_image: kitchen-signs.jpg
status: published
excerpt: "Is your kitchen showing its age? Here are five telltale signs..."
---

Full markdown content here...
```

### 3.5 Settings
```json
{
  "business_name": "BT Construction LLC",
  "tagline": "Integrity with results!",
  "phone": "(214) 555-0000",
  "email": "info@btconstructiontx.com",
  "address_city": "Dallas",
  "address_state": "TX",
  "service_areas": ["Dallas", "Plano", "Carrollton"],
  "business_hours": "Mon-Fri 8am-6pm, Sat 9am-2pm",
  "social_facebook": "https://facebook.com/btconstructiontx",
  "social_instagram": "https://instagram.com/btconstructiontx",
  "google_analytics_id": "",
  "google_tag_manager_id": "",
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_user": "",
  "smtp_password": "",
  "notification_email": "info@btconstructiontx.com"
}
```

### 3.6 Form Submission
```json
{
  "id": "uuid-string",
  "type": "quote_request",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "(972) 555-1234",
  "project_type": "kitchen",
  "description": "Looking to remodel our kitchen...",
  "timeline": "1-3 months",
  "budget": "$25K-$50K",
  "referral_source": "Google",
  "photos": ["upload-1.jpg", "upload-2.jpg"],
  "read": false,
  "submitted_at": "2026-02-28T14:30:00Z",
  "ip_address": "192.168.1.1"
}
```

---

## 4. Implementation Plan (Claude Code Phases)

### Phase 1: Project Scaffolding & Core Generator
**Effort:** ~1 session
- Initialize project structure per NFR-005
- Create `generator.py` with Jinja2 static site builder
- Create base site templates (base.html with nav/footer, home.html)
- Create seed data files for all content types
- Implement site rebuild command (`python generator.py build`)
- **Deliverable:** Running static site locally with homepage

### Phase 2: All Public Page Templates
**Effort:** ~1-2 sessions
- Build all page templates (services, portfolio, about, blog, contact, quote)
- Implement Tailwind CSS styling with navy/white/gray/gold palette
- Responsive design for all pages
- SEO meta tags and structured data
- Portfolio filtering (client-side JavaScript)
- Image lightbox for project galleries
- Before/after photo comparison component
- **Deliverable:** Complete static site with all pages, seed content, fully styled

### Phase 3: Admin Panel — Authentication & Dashboard
**Effort:** ~1 session
- Flask application setup with session management
- Login page with bcrypt authentication
- CSRF protection
- Admin dashboard with 6 navigation cards
- Admin base template (simple, large UI elements for Calvin)
- **Deliverable:** Secured admin panel with dashboard

### Phase 4: Admin Panel — Content CRUD
**Effort:** ~2 sessions
- Portfolio CRUD (create, read, update, delete with image upload)
- Testimonial CRUD
- Service page editor
- Blog post editor with Markdown toolbar
- Image upload handler with Pillow optimization
- Auto-rebuild on save/publish
- **Deliverable:** Full content management capability

### Phase 5: Forms & Email
**Effort:** ~1 session
- Contact form handler (validation, honeypot, rate limiting)
- Quote request form handler (with photo upload)
- SMTP email notifications
- Admin submission viewer (with read/unread)
- **Deliverable:** Working forms with email notifications

### Phase 6: Settings & Polish
**Effort:** ~1 session
- Admin settings page
- Sitemap.xml and robots.txt generation
- 404 page
- Favicon and touch icons
- Performance optimization (lazy loading, preconnect hints)
- Security headers in Nginx config
- **Deliverable:** Production-ready application

### Phase 7: Deployment
**Effort:** ~1 session
- Write `setup.sh` deployment script
- Nginx configuration file
- Systemd service file for Flask
- Certbot SSL setup
- Spin up Linode, run setup, deploy
- Update DNS A record at IONOS (74.208.236.53 → new Linode IP)
- Clean up Sintra TXT records
- Verify everything works
- **Deliverable:** Live site at btconstructiontx.com

---

## 5. DNS Cutover Checklist

**Current state (at IONOS registrar):**
| Record | Value | Action |
|--------|-------|--------|
| A @ | 74.208.236.53 | **Change to new Linode IP** |
| AAAA @ | 2607:f1c0:100f:f000:0:0:0:200 | **Delete** (unless new Linode has IPv6) |
| A www | 74.208.236.53 | **Change to new Linode IP** |
| AAAA www | 2607:f1c0:100f:f000:0:0:0:200 | **Delete** |
| TXT _dep_ws_mutex | (Sintra hash) | **Delete** |
| TXT _dep_ws_mutex.www | (Sintra hash) | **Delete** |
| MX @ | smtp.google.com | **Keep** (email routing) |

---

## 6. Acceptance Criteria

- [ ] Static site loads in under 2 seconds on 3G connection
- [ ] Lighthouse mobile score ≥ 90
- [ ] Calvin can add a new portfolio project with photos in under 3 minutes
- [ ] Calvin can add a testimonial in under 1 minute
- [ ] Contact form submission triggers email within 60 seconds
- [ ] Quote request with photos triggers email within 60 seconds
- [ ] Site rebuilds in under 10 seconds after content change
- [ ] All pages render correctly on iPhone, iPad, and desktop
- [ ] SSL certificate valid and auto-renewing
- [ ] Admin panel inaccessible without authentication
- [ ] Site survives Linode reboot (services auto-start)
