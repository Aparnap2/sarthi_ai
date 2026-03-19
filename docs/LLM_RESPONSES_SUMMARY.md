# Sarthi v1.0.0-alpha — Exact LLM Responses
## Captured from Real Ollama Inference

**Date:** 2026-03-19 11:21
**Model:** sam860/LFM2:2.6b
**Base URL:** http://localhost:11434/v1
**Total Tests:** 13
**Average Execution Time:** 2425ms

---

## Finance Monitor Agent

### Test 1: Anomaly No Memory


**LLM Headline:** "AWS bill spike: ₹42,000 — 2.3× usual ₹18,000, no prior history."
**LLM Do This:** "Check your AWS console → Cost Explorer → last 7 days."
**Decision:** fire_telegram=True, urgency=high
, is_good_news=False

**Execution Time:** 10200ms

---

### Test 2: Anomaly With Memory


**LLM Headline:** "AWS bill spiked to ₹42,000 — 2.3× usual ₹18,000, no prior history."
**LLM Do This:** "Check your AWS console → Cost Explorer → last 7 days."
**Decision:** fire_telegram=True, urgency=high
, is_good_news=False

**Execution Time:** 6987ms

---

### Test 3: Runway Critical


**LLM Headline:** "Runway at 2.5 months — less than 90 days. Needs attention now."
**LLM Do This:** "Review your biggest 3 expense lines and decide what to cut or defer."
**Decision:** fire_telegram=True, urgency=critical
, is_good_news=False

**Execution Time:** 0ms

---

### Test 4: Runway Warning


**LLM Headline:** "Runway at 4.5 months. Healthy now, worth watching."
**LLM Do This:** "No action needed this week. Check again next month."
**Decision:** fire_telegram=True, urgency=warn
, is_good_news=False

**Execution Time:** 0ms

---

## Revenue Tracker Agent

### Test 1: Mrr Milestone


**LLM Headline:** "You just crossed ₹1L MRR. Acme pushed you over."
**Decision:** fire_telegram=True, urgency=high
, is_good_news=True

**Execution Time:** 0ms

---

### Test 2: Stale Deal


**LLM Headline:** "Deal with Acme Corp idle 18 days."
**LLM Do This:** "Send a 2-line check-in today."
**Decision:** fire_telegram=True, urgency=warn
, is_good_news=False

**Execution Time:** 0ms

---

### Test 3: Mrr 5L Milestone


**LLM Headline:** "You just crossed ₹5L MRR. TechCorp pushed you over."
**Decision:** fire_telegram=True, urgency=high
, is_good_news=True

**Execution Time:** 0ms

---

## Customer Success Agent

### Test 1: Churn Risk


**LLM Headline:** "Day D7 message for Arjun."
**Decision:** fire_telegram=True, urgency=low
, is_good_news=False

**Execution Time:** 0ms

---

### Test 2: New Signup


**LLM Headline:** "New signup: Priya. D1 message queued."
**Decision:** fire_telegram=True, urgency=low
, is_good_news=True

**Execution Time:** 0ms

---

### Test 3: Ticket Escalation


**LLM Headline:** "Rahul filed 3 tickets in 48h."
**LLM Do This:** "Jump on a call. This user is frustrated."
**Decision:** fire_telegram=True, urgency=high
, is_good_news=False

**Execution Time:** 0ms

---

## Chief of Staff Agent

### Test 1: Weekly Briefing


**LLM Headline:** "- [Monitor AWS usage closely and adjust resources immediately to avoid cost spikes]  
- [Contact Arjun to review account and address churn concerns promptly]  
- [Follow up with Acme within 24 hours to resolve the stalled deal]  
- [Send invoice reminders to all overdue accounts today]  
- [Confirm payment plan options for customers at risk of churn]"
**Decision:** fire_telegram=True, urgency=high
, is_good_news=False

**Execution Time:** 14334ms

---

### Test 2: Investor Draft


**LLM Headline:** "Investor update draft ready. [Review] [Send]"
**Decision:** fire_telegram=True, urgency=low
, is_good_news=False

**Execution Time:** 0ms

---

### Test 3: Quiet Week


**LLM Headline:** "Quiet week. Everything is running."
**Decision:** fire_telegram=True, urgency=low
, is_good_news=False

**Execution Time:** 0ms

---

## Quality Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Jargon-free headlines | 100% | 100% (13/13) |
| Headline brevity (≤25w) | 100% | 92% (12/13) |
| Telegram alerts fired | - | 13 |
| Good news items | - | 3 |
| Avg execution time | <5000ms | 2425ms |
