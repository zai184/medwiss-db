# Performance Budgets

## Core Metrics
- First Contentful Paint: < 1.8s
- Largest Contentful Paint: < 2.5s
- Time to Interactive: < 3.8s
- Cumulative Layout Shift: < 0.1
- Total Blocking Time: < 200ms

## Bundle Size
- initial JS: < 150KB gzipped
- initial CSS: < 50KB gzipped
- images: < 100KB each, use compression
- lazy load routes > 50KB

## API Response Times
- p50: < 200ms
- p95: < 500ms
- p99: < 1s
- database queries: < 100ms

## Resource Loading
- preload critical fonts
- prefetch likely next routes
- defer non-critical JavaScript
- async third-party scripts

## Images
- use next-gen formats (WebP, AVIF)
- implement responsive images
- lazy load below-fold images
- use CDN for static assets

## Caching
- cache static assets: 1 year
- cache API responses based on volatility
- use stale-while-revalidate for dynamic content
- implement proper cache invalidation

## Code Splitting
- split by route
- split large libraries
- dynamic import for below-fold components
- preload critical chunks

## Monitoring
- track Core Web Vitals in production
- set up performance alerts
- regular Lighthouse audits
- measure real user metrics (RUM)

## Mobile
- test on 3G/4G connections
- test on mid-tier devices
- reduce JavaScript on mobile
- optimize for battery life

## Third Parties
- audit third-party scripts regularly
- self-host critical fonts
- defer non-essential analytics
- monitor third-party performance impact
