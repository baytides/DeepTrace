# Set Up Custom Domain: deeptrace.projectcivitas.com

## Prerequisites

- Cloudflare Pages project `deeptrace` is created ✓
- GitHub connected to Cloudflare Pages ✓
- `projectcivitas.com` is on Cloudflare (if not, we'll add it)

---

## Step 1: Verify projectcivitas.com is on Cloudflare

```bash
# Check if domain is on Cloudflare
wrangler pages project list
```

Or check in dashboard: https://dash.cloudflare.com → Websites

### If projectcivitas.com is NOT on Cloudflare:

1. Go to https://dash.cloudflare.com
2. Click "Add a site"
3. Enter `projectcivitas.com`
4. Follow the nameserver setup instructions
5. Come back here once DNS is active

---

## Step 2: Add Custom Domain via CLI

```bash
# Add deeptrace.projectcivitas.com to the Pages project
wrangler pages domain add deeptrace.projectcivitas.com --project-name=deeptrace
```

This will:
- Create DNS record automatically
- Provision SSL certificate
- Set up CDN routing

**Done!** Your site will be accessible at:
- `https://deeptrace.projectcivitas.com` (custom domain)
- `https://deeptrace-3nl.pages.dev` (still works as backup)

---

## Step 3: Add Custom Domain via Dashboard (Alternative)

If you prefer using the dashboard:

1. Go to https://dash.cloudflare.com
2. Click "Workers & Pages"
3. Click on your `deeptrace` project
4. Click "Custom domains" tab
5. Click "Set up a custom domain"
6. Enter: `deeptrace.projectcivitas.com`
7. Click "Continue"
8. Cloudflare will automatically:
   - Create the DNS record
   - Provision SSL certificate
   - Activate the domain

**Takes 1-2 minutes** for DNS to propagate.

---

## Step 4: Verify It Works

```bash
# Test the domain
curl -I https://deeptrace.projectcivitas.com
```

Or visit in browser: https://deeptrace.projectcivitas.com

---

## DNS Configuration (Automatic)

Cloudflare automatically creates this DNS record:

```
Type: CNAME
Name: deeptrace
Target: deeptrace-3nl.pages.dev
Proxy: Enabled (orange cloud)
```

You can verify in:
- Dashboard → DNS → Records for projectcivitas.com

---

## SSL Certificate (Automatic)

Cloudflare automatically provisions:
- **Universal SSL** (free)
- **Auto-renews** before expiration
- **Full encryption** (end-to-end)

No action needed!

---

## Update Documentation

Once the domain is live, update:

- README.md with new URL
- Any hardcoded links
- API documentation

---

## Troubleshooting

### "Domain not found"
- Ensure projectcivitas.com is on Cloudflare
- Wait 5 minutes for DNS propagation

### "SSL certificate pending"
- Normal! Takes 1-2 minutes
- Refresh page and check again

### "404 Not Found"
- Ensure Pages deployment succeeded
- Check GitHub Actions: https://github.com/baytides/DeepTrace/actions

---

## Next Steps

After domain is active:

1. Test the site: `https://deeptrace.projectcivitas.com`
2. Add environment variables (Carl AI integration)
3. Test case creation and switching
4. Announce the URL! 🎉
