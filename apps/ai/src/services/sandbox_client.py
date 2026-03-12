"""
SandboxClient — async client for the sandbox service.
Every agent that needs computation or charts calls this.
"""
from __future__ import annotations
import os
import base64
import httpx
from dataclasses import dataclass

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://saarathi-sandbox:5000")
SANDBOX_SECRET = os.getenv("SANDBOX_SECRET", "saarathi-local")


@dataclass
class SandboxResult:
    success: bool
    output: str
    chart_b64: str | None
    error: str | None

    def chart_bytes(self) -> bytes | None:
        return base64.b64decode(self.chart_b64) if self.chart_b64 else None


class SandboxClient:
    async def run(self, code: str, timeout: int = 10) -> SandboxResult:
        """Execute Python code in the isolated sandbox."""
        async with httpx.AsyncClient(timeout=timeout + 5) as c:
            try:
                r = await c.post(
                    f"{SANDBOX_URL}/execute",
                    json={"code": code, "timeout": timeout},
                    headers={"X-Sandbox-Secret": SANDBOX_SECRET},
                )
                d = r.json()
                return SandboxResult(
                    success=d.get("success", False),
                    output=d.get("output", ""),
                    chart_b64=d.get("chart"),
                    error=d.get("error"),
                )
            except Exception as e:
                return SandboxResult(False, "", None, str(e))

    async def profit_trend_chart(
        self,
        months: list[str],
        profits: list[int],
        title: str = "Your Profit — Last 6 Months",
    ) -> SandboxResult:
        """Pre-built chart: profit bar chart with ₹ formatting."""
        code = f"""
months  = {months!r}
profits = {profits!r}
title   = {title!r}

fig, ax = plt.subplots(figsize=(8, 4))
colors  = ['#22c55e' if p >= 0 else '#ef4444' for p in profits]
bars    = ax.bar(months, profits, color=colors, alpha=0.85, width=0.6)

for bar, val in zip(bars, profits):
    ypos = bar.get_height() + max(abs(v) for v in profits) * 0.02
    ax.text(bar.get_x() + bar.get_width() / 2, ypos,
            f'₹{{val:,}}', ha='center', va='bottom',
            fontsize=9, fontweight='bold')

ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
ax.set_ylabel('Profit (₹)', fontsize=10)
ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax.spines[['top', 'right']].set_visible(False)
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f'₹{{int(x):,}}'))
plt.tight_layout()
"""
        return await self.run(code, timeout=8)

    async def loan_model_chart(
        self,
        loan: int,
        emi: int,
        months: int = 24,
        purpose: str = "this purchase",
    ) -> SandboxResult:
        """Pre-built chart: loan repayment curve + plain-language summary."""
        code = f"""
loan    = {loan}
emi     = {emi}
months  = {months}
purpose = {purpose!r}

balance  = [max(loan - emi * i, 0) for i in range(months + 1)]
total    = emi * months
interest = total - loan
payoff   = next((i for i, b in enumerate(balance) if b == 0), months)

print(f"Loan amount:     ₹{{loan:,}}")
print(f"Monthly payment: ₹{{emi:,}}")
print(f"Total you pay:   ₹{{total:,}}")
print(f"Interest cost:   ₹{{interest:,}}")
print(f"Paid off after:  {{payoff}} months")
print()
print(f"For this to make sense, {{purpose!r}} should generate")
print(f"more than ₹{{emi:,}} extra per month.")

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(range(months + 1), balance, color='#3b82f6', linewidth=2.5)
ax.fill_between(range(months + 1), balance, alpha=0.12, color='#3b82f6')
ax.set_title(f'Loan Balance Over {{months}} Months',
             fontsize=13, fontweight='bold')
ax.set_xlabel('Month')
ax.set_ylabel('Amount Still Owed (₹)')
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f'₹{{int(x):,}}'))
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
"""
        return await self.run(code, timeout=8)

    async def cash_flow_chart(
        self,
        months: list[str],
        credits: list[int],
        debits: list[int],
    ) -> SandboxResult:
        """Pre-built chart: stacked cash flow — in vs out."""
        code = f"""
months  = {months!r}
credits = {credits!r}
debits  = {debits!r}
net     = [c - d for c, d in zip(credits, debits)]

x = range(len(months))
fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(x, credits, label='Money In',  color='#22c55e', alpha=0.8, width=0.35,
       align='edge')
ax.bar([i + 0.35 for i in x], debits, label='Money Out',
       color='#ef4444', alpha=0.8, width=0.35, align='edge')

for i, n in enumerate(net):
    color = '#15803d' if n >= 0 else '#b91c1c'
    ax.text(i + 0.175, max(credits[i], debits[i]) * 1.03,
            f'₹{{n:,}}', ha='center', fontsize=8,
            color=color, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(months)
ax.set_title('Money In vs Out', fontsize=13, fontweight='bold')
ax.legend()
ax.spines[['top', 'right']].set_visible(False)
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f'₹{{int(x):,}}'))
plt.tight_layout()
"""
        return await self.run(code, timeout=8)
