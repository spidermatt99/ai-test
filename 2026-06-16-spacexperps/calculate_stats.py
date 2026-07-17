import json
import math

def calculate_stats(data_list, ipo_date):
    # Split into pre-IPO and post-IPO
    pre_ipo = [d for d in data_list if d["Date"] < ipo_date]
    post_ipo = [d for d in data_list if d["Date"] >= ipo_date]
    
    # Pre-IPO stats
    last_pre_ipo_price = pre_ipo[-1]["Perp_Close"] if pre_ipo else None
    
    # Find the stock price on day 1 of trading (first trading day on or after IPO date)
    first_stock_day = None
    for d in post_ipo:
        if d["Stock_Close"] is not None:
            first_stock_day = d
            break
            
    first_stock_price = first_stock_day["Stock_Close"] if first_stock_day else None
    
    pre_ipo_deviation = None
    if last_pre_ipo_price and first_stock_price:
        pre_ipo_deviation = round(((last_pre_ipo_price - first_stock_price) / first_stock_price) * 100, 2)
        
    # Post-IPO comparison stats (matching days where both are present)
    matching = [d for d in post_ipo if d["Stock_Close"] is not None and d["Perp_Close"] is not None]
    
    n = len(matching)
    correlation = None
    mean_premium = None
    mean_abs_premium = None
    
    if n > 1:
        x = [d["Perp_Close"] for d in matching]
        y = [d["Stock_Close"] for d in matching]
        
        # Mean of x and y
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        # Covariance and Variance
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (n - 1)
        var_x = sum((xi - mean_x) ** 2 for xi in x) / (n - 1)
        var_y = sum((yi - mean_y) ** 2 for yi in y) / (n - 1)
        
        if var_x > 0 and var_y > 0:
            correlation = cov / (math.sqrt(var_x) * math.sqrt(var_y))
            
        premiums = [((xi - yi) / yi) * 100 for xi, yi in zip(x, y)]
        mean_premium = sum(premiums) / n
        mean_abs_premium = sum(abs(p) for p in premiums) / n
        
    return {
        "pre_ipo_length_days": len(pre_ipo),
        "last_pre_ipo_price": last_pre_ipo_price,
        "first_stock_price": first_stock_price,
        "pre_ipo_deviation_pct": pre_ipo_deviation,
        "post_ipo_matched_days": n,
        "correlation": round(correlation, 4) if correlation is not None else None,
        "avg_premium_pct": round(mean_premium, 2) if mean_premium is not None else None,
        "mean_abs_deviation_pct": round(mean_abs_premium, 2) if mean_abs_premium is not None else None
    }

def main():
    with open("all_prices.json", "r") as f:
        data = json.load(f)
        
    stats = {}
    for company, info in data.items():
        comp_stats = calculate_stats(info["data"], info["ipo_date"])
        stats[company] = comp_stats
        print(f"\nStats for {company}:")
        for k, v in comp_stats.items():
            print(f"  {k}: {v}")
            
    with open("all_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

if __name__ == "__main__":
    main()
