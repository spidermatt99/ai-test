"""Build reproducible tables, charts and a standard Markdown research note.
Run fetch_anthropic.py first. Only Python's standard library is required here.
"""
import csv
import datetime as dt
import html
import json
from pathlib import Path
import xml.etree.ElementTree as ET

DATA = Path('data')
SHARES = 17_498_334_025  # Entropy's published provisional transition share count, NOT final issuer count.
SCALAR = SHARES / 1e9
BASIC_SHARES = 7_427_991_791 + 5_658_680_800  # Nov 10 S-1/A, economic classes only, no greenshoe.
COLORS = {'xyz:ANT':'#2563eb','para:ANTH':'#ea580c','io:ANTH':'#059669','vntl:ANTHROPIC':'#9333ea'}
LABELS = {'xyz:ANT':'XYZ','para:ANTH':'Paragon','io:ANTH':'Entropy','vntl:ANTHROPIC':'Ventuals (delisted)'}

snapshot = json.loads((DATA/'snapshot.json').read_text())
history = {x['market']['name']: json.loads((DATA/(x['market']['name'].replace(':','_')+'_1d.json')).read_text()) for x in snapshot}

def date(ms):
    return dt.datetime.fromtimestamp(ms/1000, dt.timezone.utc).strftime('%Y-%m-%d')

def factor(coin):
    return SCALAR if coin in ('xyz:ANT','para:ANTH') else 1

def fmt(value):
    return f'{value:,.2f}'

summary=[]
normalized=[]
for item in snapshot:
    coin=item['market']['name']; ctx=item['context']; rows=history[coin]; f=factor(coin)
    mark=float(ctx['markPx']); first=float(rows[0]['o']); last=float(rows[-1]['c'])
    summary.append(dict(market=coin,delisted=item['market'].get('isDelisted',False),snapshot_retrieval_started_utc=item['observed_at'],mark=mark,mid=ctx['midPx'],oracle=float(ctx['oraclePx']),valuation_bn_on_entropy_estimate=mark*f,share_equivalent_on_entropy_estimate=mark*f/SCALAR,change_24h_pct=(mark/float(ctx['prevDayPx'])-1)*100,volume_24h_usd=float(ctx['dayNtlVlm']),open_interest_usd=float(ctx['openInterest'])*mark,first_candle_date=date(rows[0]['t']),last_candle_date=date(rows[-1]['t']),daily_candles=len(rows),first_trade_open=first,last_trade_close=last,history_low=min(float(r['l']) for r in rows),history_high=max(float(r['h']) for r in rows),first_open_to_last_close_pct=100*(last/first-1)))
    for r in rows:
        normalized.append(dict(market=coin,date_utc=date(r['t']),open=float(r['o']),high=float(r['h']),low=float(r['l']),close=float(r['c']),normalization_multiplier=f,normalized_open_bn=float(r['o'])*f,normalized_high_bn=float(r['h'])*f,normalized_low_bn=float(r['l'])*f,normalized_close_bn=float(r['c'])*f,volume_contract_units=float(r['v']),trades=r['n']))
for name,rows in [('market_summary.csv',summary),('daily_normalized.csv',normalized)]:
    with (DATA/name).open('w',newline='',encoding='utf-8') as fp:
        w=csv.DictWriter(fp,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# Standalone SVGs, readable in Markdown viewers and browsers; hover points for exact values.
def chart(filename,title,coins,normalized_values=True,start=None):
    series={c:[r for r in history[c] if start is None or date(r['t'])>=start] for c in coins}
    allrows=[(c,r) for c,rows in series.items() for r in rows]
    xmin=min(r['t'] for c,r in allrows); xmax=max(r['t'] for c,r in allrows)
    val=lambda c,r:float(r['c'])*(factor(c) if normalized_values else 1)
    vals=[val(c,r) for c,r in allrows]; ymin=min(vals); ymax=max(vals)
    pad=(ymax-ymin)*.12 or 1; ymin-=pad; ymax+=pad
    W,H=1100,520; L,R,T,B=100,35,90,75; pw=W-L-R; ph=H-T-B
    xp=lambda t:L+(t-xmin)/(xmax-xmin or 1)*pw
    yp=lambda v:T+(ymax-v)/(ymax-ymin)*ph
    esc=html.escape
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"><title>{esc(title)}</title>', '<rect width="100%" height="100%" fill="#ffffff"/>', '<g font-family="Arial,sans-serif" fill="#172033">', f'<text x="{L}" y="30" font-size="20" font-weight="bold">{esc(title)}</text>', f'<text x="{L}" y="52" font-size="12">Daily trade closes; last day partial. No mark-price history. Hover points for details.</text>']
    for i in range(6):
        v=ymin+(ymax-ymin)*i/5; y=yp(v)
        s += [f'<path d="M {L} {y:.1f} H {W-R}" stroke="#e5e7eb"/>',f'<text x="{L-12}" y="{y+4:.1f}" text-anchor="end" font-size="12">{v:,.0f}</text>']
    for i in range(6):
        t=xmin+(xmax-xmin)*i/5; x=xp(t)
        s += [f'<text x="{x:.1f}" y="{H-B+23}" text-anchor="middle" font-size="12">{date(t)}</text>']
    legend_x=L
    for c,rows in series.items():
        color=COLORS[c]
        s += [f'<text x="{legend_x}" y="74" fill="{color}" font-size="13">{esc(LABELS[c])}</text>']
        legend_x+=220
        pts=' '.join(f'{xp(r["t"]):.2f},{yp(val(c,r)):.2f}' for r in rows)
        s.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.3"/>')
        for r in rows:
            tip=f'{c} | {date(r["t"])} | close {float(r["c"]):,.3f} | '+('normalized valuation $'+fmt(val(c,r))+'B' if normalized_values else 'raw contract price')
            s.append(f'<circle cx="{xp(r["t"]):.2f}" cy="{yp(val(c,r)):.2f}" r="3" fill="{color}"><title>{esc(tip)}</title></circle>')
    axis='USD billions; share contracts normalized using Entropy provisional 17.498334025B shares' if normalized_values else 'Raw contract price (not company valuation)'
    s.append(f'<text x="{L}" y="{H-20}" font-size="12">{esc(axis)}</text></g></svg>')
    output='\n'.join(s); ET.fromstring(output); Path(filename).write_text(output,encoding='utf-8')

chart('anthropic_valuation_history.svg','Anthropic perpetuals: available valuation-comparison history',list(history))
chart('anthropic_active_comparison.svg','Anthropic active perpetuals: common-period comparison',['xyz:ANT','para:ANTH','io:ANTH'],start='2026-10-27')
for c in history:
    chart(c.replace(':','_')+'_price_history.svg',c+' — raw trade-price history',[c],False)

current_table=['| Market | Status | API mark | Comparable valuation* | 24h mark change | 24h volume | Open interest |','|---|---|---:|---:|---:|---:|---:|']
for r in summary:
    status='**Delisted**' if r['delisted'] else 'Active'
    current_table.append(f"| `{r['market']}` | {status} | ${fmt(r['mark'])} | ${r['valuation_bn_on_entropy_estimate']/1000:.4f}T | {r['change_24h_pct']:+.2f}% | ${r['volume_24h_usd']/1e6:.3f}M | ${r['open_interest_usd']/1e6:.3f}M |")
history_table=['| Market | Available daily candles (UTC) | Candles | First trade open | Last trade close | Trade low–high | First open → last close |','|---|---|---:|---:|---:|---:|---:|']
for r in summary:
    history_table.append(f"| `{r['market']}` | {r['first_candle_date']} → {r['last_candle_date']} | {r['daily_candles']} | ${fmt(r['first_trade_open'])} | ${fmt(r['last_trade_close'])} | ${fmt(r['history_low'])}–${fmt(r['history_high'])} | {r['first_open_to_last_close_pct']:+.2f}% |")

report=f'''# Anthropic perpetuals on Hyperliquid: price history and implied valuation

**Snapshot retrieval started:** {snapshot[0]['observed_at']}. All dates are UTC unless stated otherwise.

## Bottom line

The current Hyperliquid native market and all 10 HIP-3 builder registries contain **four identifiable Anthropic contracts: three active, one delisted**. On **Entropy's published provisional 17.498334025-billion-share comparison basis**, the active markets imply approximately **$1.81–$1.82 trillion**. This is not a verified final issuer market capitalization.

The crucial unit distinction: **XYZ and Paragon quote USD per anticipated share; Entropy and Ventuals quote valuation in USD billions. A $104 share-price quote does not mean a $104B company.**

## Current snapshot

{chr(10).join(current_table)}

**Comparable valuation:** uses each valuation contract's native USD-billion scale, or a share-price contract multiplied by Entropy's published provisional share-count scalar. Ventuals is an archived API value, **not a current tradable valuation**. Its published final settlement was **$1,618.90**, equivalent to **$1.61890T**, on June 15, 2026. The API still shows a stale mark of $1,619.30 and oracle of $1,618.90; do not confuse the stale mark/last trade with the official settlement.

Open interest above is notional, computed as API `openInterest × markPx`; it is not margin deposited. Volume is reported 24-hour notional volume. Returns are current mark versus `prevDayPx`, not daily-candle returns. Snapshot requests are sequential/concurrent API observations, not an atomic cross-venue snapshot.

### How each price maps to valuation

| Contract | Contract's quoted unit | Valuation calculation |
|---|---|---|
| `xyz:ANT` | USD per anticipated Class A share | `mark × share count`; $104.25 × 17.498334025B = **$1.824201T** on Entropy's estimate |
| `para:ANTH` | USD per anticipated share | `mark × share count`; $103.70 × 17.498334025B = **$1.814577T** on the same basis |
| `io:ANTH` | USD billions of fully diluted valuation | $1,809.20 × $1B = **$1.809200T** directly |
| `vntl:ANTHROPIC` | USD billions of valuation | Official final settlement $1,618.90 × $1B = **$1.618900T**, historical only |

Paragon's current docs display the instrument as **ANT**, but Hyperliquid's actual API symbol is **`para:ANTH`**. The descriptions and parameters identify it as the Anthropic anticipated-share-price market.

Entropy's $1,809.20 is equivalent to approximately **$103.3927 per share** using its provisional scalar. XYZ is **0.83%** above Entropy on that basis; Paragon is **0.30%** above. These are mark comparisons, not executable arbitrage spreads. In particular, Paragon has very little volume and its latest trade is older than the snapshot; its current mark, midpoint and last trade differ.

## Price history

These are **traded OHLC candles**, not historical marks or oracle prices. The latest daily candle is partial. First observed candle means the earliest candle returned by Hyperliquid, not a separately verified listing timestamp.

{chr(10).join(history_table)}

Ventuals started trading November 25, 2025 and last traded June 15, 2026; its close-to-close history ends there. It must not be carried forward as an active November quote. The 203 returned daily candles are non-empty candles, not a complete calendar-day grid.

XYZ's first observed trade was $138, versus a documented launch reference of $125. Paragon's first observed trade was $112, versus a documented launch reference of $110. The return column uses actual first observed candle opens, **not launch references**. These returns exclude funding and fees.

### All available daily valuation-comparison history

![Anthropic valuation history](anthropic_valuation_history.svg)

### Active markets over their shared history

![Active Anthropic market comparison](anthropic_active_comparison.svg)

These charts apply **today's Entropy estimate retrospectively** to XYZ/Paragon share prices. They are constant-share-count contract comparisons, not a reconstruction of Anthropic's actual historical cap table. Entropy/Ventuals retain their native valuation scales. The gap between the end of Ventuals and start of Entropy is deliberately not filled. Daily closes are sparse trades where a market is illiquid.

Raw-price charts: [XYZ](xyz_ANT_price_history.svg), [Paragon](para_ANTH_price_history.svg), [Entropy](io_ANTH_price_history.svg), [Ventuals](vntl_ANTHROPIC_price_history.svg).

## Share-count caveat: there is no single unqualified market cap

1. **Contract normalization basis:** Entropy's current asset directory explicitly publishes **17,498,334,025 shares**, or **17.498334025** as the estimated transition multiplier. It says this may change pending the final 424(b) prospectus. This report uses that exact number to compare contracts, not an invented round-number multiplier.
2. **Basic post-offering basis:** The November 10 S-1/A's “The Offering” section gives **7,427,991,791 Class A** plus **5,658,680,800 Class N** economic shares, totaling **{BASIC_SHARES:,}** without the underwriters' option. The single Class T and Class F control shares have no economic rights and are excluded. At XYZ's $104.25 this produces **${104.25*BASIC_SHARES/1e12:.4f}T**, rather than $1.8242T. This is a legal post-offering economic-share basis; it is not the same as an accounting-consolidated or fully diluted basis, particularly because of Public Benefit Fund treatment.
3. **Unresolved documentation discrepancy:** I could **not independently reconcile Entropy's 17.498334025B estimate to the retrieved November 10 S-1/A**. The filing's later capitalization bridge lists 7,430,143,944 Class A, 7,804,580,273 Class N, 1,704,567,865 option shares after treasury-stock adjustment, and 1,073,701,297 RSU shares. Adding these gives **18,012,993,379**, not Entropy's estimate. This bridge includes additional adjustments (including rollover notes and donation/public-benefit items) and is not automatically the contract's final scalar. Applied mechanically to XYZ's mark, it would give **$1.8779T**. Do **not** silently treat either provisional scalar as a settled final fully diluted issuer count.
4. **Final IPO terms can change:** Entropy says its final scalar is set at the IPO using the final 424(b), or the most recent S-1/A before the first official opening trade if no 424(b) is available. It then remains fixed; future issuances/buybacks can make its quoted valuation diverge from actual market cap.

Thus **$1.81–$1.82T is the answer on Entropy's currently published contract-comparison basis**, while an actual issuer market-cap answer must specify basic versus diluted shares, Public Benefit Fund treatment, and the final IPO terms. None of these perps gives ownership of Anthropic shares.

## Talos report: what “Class A-only denominator” means

I reviewed Talos's November 10 report, [Countdown to ANT](https://www.talos.com/insights/countdown-to-ant-what-the-pre-ipo-perps-markets-say-about-anthropics-ipo). It explicitly describes XYZ's post-conversion per-share denominator as Class A only, contrasting that with common-share and fully diluted conversions on other venues. This is a claim about contract reference/conversion units; the report does not provide a numerical XYZ reference-share-count field establishing a company-wide market-cap denominator.

XYZ's own linked specification says one contract references one Class A share. Thus its price is directly comparable to the listed Class A share price. It does not follow that company-wide equity value should exclude Class N. The S-1/A says Class A and Class N rights are identical except for voting and conversion.

At the snapshot's $104.25, multiplying by the filing's 7,427,991,791 post-offering Class A shares gives **$774.4B of Class A capitalization**. Multiplying by basic Class A plus Class N gives **$1.3643T**. Applying Entropy's provisional diluted estimate gives **$1.8242T**. These are different capitalization bases, not three different XYZ share prices. The $1.8242T number in this report is an explicitly selected comparison basis, **not an independently verified XYZ-published market cap**.

There is also an important qualification to Talos's discussion of Entropy's conversion: Entropy's current primary documentation says the contract **remains in market-cap units after IPO**, with `contract price = listed share price × fixed fully diluted share count / 1B`. A share-equivalent price may be computed by dividing out that scalar, but the traded quote does not itself rebase to a single-share quote. Therefore the report's general language about markets converting to per-share valuation should not be read as a literal Entropy quote rebase.

## IPO context

Anthropic's November 10 roadshow announcement gives an expected **$70–$78/share** offering range. XYZ's $104.25 mark is **33.7% above the top** of that range and **40.9% above the $74 midpoint**. An anticipated post-listing trading price need not equal an offering allocation price. XYZ's spec anticipates November 20, 2026, but explicitly warns the date can change.

## Data, scope and reproducibility

- Enumerated `perpDexs`, then `metaAndAssetCtxs` for native perps and every returned HIP-3 builder: native, xyz, flx, vntl, hyna, km, abcd, cash, para, mkts, io. Searched names for ANTH/CLAUDE and exact ticker ANT. Includes the delisted Ventuals listing. Does not prove a never-returned or permanently removed historical instrument never existed, or capture unidentified aliases; excludes spot/prediction markets and other exchanges.
- Requested `candleSnapshot` with `startTime=0` through the retrieval time at both **1d and 1h** intervals. Every series returned fewer than Hyperliquid's 5,000-candle cap, so no cap truncation is evident. Missing/no-trade periods are not forward-filled. No ticks or historical marks were downloaded.
- Raw API responses and CSVs are under [data/](data/). Daily and hourly files are named `<dex>_<symbol>_1d.csv` and `_1h.csv`.
- [Market summary](data/market_summary.csv): snapshot, liquidity and historical statistics.
- [Normalized daily history](data/daily_normalized.csv): raw daily OHLC plus normalized USD-billion OHLC and the explicit conversion multiplier.
- [Market snapshot](data/snapshot.json), [all metadata](data/all_metadata.json), and [perpetual DEX registry](data/perp_dexes.json) preserve discovery evidence.
- Source text snapshots are in [research/](research/).
- Reproduce this downloaded snapshot's tables/charts: `python analyze_anthropic.py`. `python fetch_anthropic.py` fetches new raw prices, but the narrative examples and contract constants in this analysis are snapshot-specific and must be reviewed/updated before generating a fresh report. Published contract mechanics, share-count estimates and filing updates do not automatically refresh from websites.

## Primary sources

1. [Hyperliquid public info API](https://api.hyperliquid.xyz/info) — POST queries `perpDexs`, `metaAndAssetCtxs`, `candleSnapshot`; [API documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint).
2. [XYZ pre-IPO specification index](https://docs.trade.xyz/perpetuals/specifications-and-schedules/pre-ipo-specification-index) and [pre-IPO mechanics](https://docs.trade.xyz/perpetuals/markets/pre-ipo-perpetuals).
3. [Paragon specifications](https://docs.paragon.trade/resources/specifications) and [pre-listing pricing](https://docs.paragon.trade/markets/equities/pre-listing-pricing).
4. [Entropy asset specifications — exact estimated share scalar](https://docs.entropy.io/asset-directory/pre-ipo-assets) and [valuation units, final share-count and transition rules](https://docs.entropy.io/market-types/pre-ipo-perpetuals).
5. [Ventuals valuation units](https://docs.ventuals.com/perp-specifications/private-companies) and [sunset/official Anthropic settlement](https://docs.ventuals.com/sunset-guide).
6. [Anthropic November 10 roadshow announcement](https://www.anthropic.com/news/roadshow-launch).
7. [Anthropic November 10, 2026 S-1/A, accession 0001628280-26-072484](https://www.sec.gov/Archives/edgar/data/2130357/000162828026072484/anthropicpbc-sx1ax2.htm), “The Offering,” pp. 20–25, and [SEC submissions index](https://data.sec.gov/submissions/CIK0002130357.json).
8. [Talos, Countdown to ANT, November 10, 2026](https://www.talos.com/insights/countdown-to-ant-what-the-pre-ipo-perps-markets-say-about-anthropics-ipo), especially “XYZ - The Baseline for ANT valuation” and “Entropy’s Persistent Popularity.”
'''
Path('Anthropic perps - price history and valuation.md').write_text(report,encoding='utf-8')
print('Wrote research note, 6 SVG charts, summary CSV and normalized daily CSV.')
print('\n'.join(current_table))
