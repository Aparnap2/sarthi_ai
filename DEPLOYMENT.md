# Deployment Configuration

## Option 1: Railway (Recommended - Easiest)

Railway offers $5 free credits (no credit card required) which is plenty for a demo app.

### Steps:

1. **Sign up at [railway.app](https://railway.app)**
2. **Connect your GitHub repo**
3. **Create new project from repo**
4. **Add environment variables:**
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_DEPLOYMENT`
5. **Deploy!** Railway auto-detects Go and builds it

**Pros:**
- Easiest deployment (literally 2 clicks)
- Auto SSL
- Custom domain support
- $5 credits = ~1 month free

**Cons:**
- Requires credit card after trial for continued use

---

## Option 2: Render (Free Forever)

Render has a truly free tier that doesn't expire.

### Steps:

1. **Sign up at [render.com](https://render.com)**
2. **New Web Service**
3. **Connect GitHub repo**
4. **Settings:**
   - Build Command: `go build -o bin/demo_server ./apps/core/cmd/demo/main.go`
   - Start Command: `./bin/demo_server`
5. **Add environment variables**
6. **Deploy**

**Pros:**
- Free tier never expires
- Auto SSL
- Custom domain support

**Cons:**
- Spins down after 15 min idle (cold start ~30s)

---

## Option 3: Azure App Service (Free but Limited)

Azure F1 tier is free but limited to 60 minutes/day compute time.

### Steps:

1. **Create Azure account**
2. **Create App Service** (F1 Free tier)
3. **Configure deployment from GitHub**
4. **Add application settings** (env vars)
5. **Deploy**

**Pros:**
- Microsoft ecosystem
- Professional look

**Cons:**
- 60 min/day limit (app sleeps after)
- More complex setup
- SSL certificate issues on free tier

---

## Recommendation

For recruiter demos: **Use Render**
- Zero cost
- Never expires
- Recruiters can visit anytime
- Just warn them about cold start (30s)

For active pitching: **Use Railway**
- Faster
- Better performance
- Impressive auto-scaling demo

## What Recruiters Will See

Once deployed, share this URL: `https://your-app.onrender.com`

They can:
1. **Visit the dashboard** at `/`
2. **Test the API** at `/api/feedback`
3. **See live metrics** at `/api/stats`
4. **Watch it classify** bugs/features/questions with Azure AI

## Environment Variables Needed

```bash
AZURE_OPENAI_ENDPOINT=https://aparnaopenai.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_DEPLOYMENT=gpt-oss-120b
```

## Demo Script for Recruiters

"This is IterateSwarm - a production-grade AI feedback triage system. Watch this:"

1. **Show the dashboard** - "HTMX frontend, real-time updates"
2. **Submit a bug report** - "App crashes when I click login"
3. **Show the classification** - "It correctly identified this as a high-severity bug"
4. **Show the GitHub spec** - "Auto-generated with reproduction steps and acceptance criteria"
5. **Show the metrics** - "Circuit breaker status, rate limiting, processing times"
6. **Mention the stack** - "Go, Azure AI Foundry, production resilience patterns"

## Post-Deployment Checklist

- [ ] App is live at public URL
- [ ] Test classification works
- [ ] Take screenshots for README
- [ ] Record short demo video (optional)
- [ ] Update LinkedIn/projects page
- [ ] Add live URL to resume
