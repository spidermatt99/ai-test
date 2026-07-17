import json

def main():
    with open("all_prices.json", "r") as f:
        prices = json.load(f)
    with open("all_stats.json", "r") as f:
        stats = json.load(f)
    try:
        with open("listing_day_hourly.json", "r") as f:
            hourly_data = json.load(f)
    except Exception:
        hourly_data = {}
        
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hyperliquid Pre-IPO vs. Stock Performance Dashboard</title>
    <!-- Inter & Outfit Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js"></script>
    <!-- Luxon Date Adapter -->
    <script src="https://cdn.jsdelivr.net/npm/luxon@3.4.4/build/global/luxon.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon@1.3.0/dist/chartjs-adapter-luxon.umd.min.js"></script>
    <!-- Chart.js Financial Candlestick Plugin -->
    <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial@0.2.0/dist/chartjs-chart-financial.umd.min.js"></script>
    <style>
        :root {{
            --bg-color: #0d0f14;
            --card-bg: rgba(22, 26, 37, 0.65);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-purple: #a855f7;
            --accent-orange: #f97316;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --glow-color: rgba(168, 85, 247, 0.15);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            padding: 2rem 1.5rem;
            line-height: 1.6;
            background-image: 
                radial-gradient(at 0% 0%, rgba(124, 58, 237, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(249, 115, 22, 0.08) 0px, transparent 50%);
        }}

        header {{
            max-width: 1400px;
            margin: 0 auto 3rem auto;
            text-align: center;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.75rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.75rem;
            letter-spacing: -0.025em;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.15rem;
            max-width: 800px;
            margin: 0 auto;
            font-weight: 400;
        }}

        .dashboard-grid {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 3rem;
        }}

        .company-section {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2rem;
            backdrop-filter: blur(16px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .company-section::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--accent-purple), var(--accent-orange));
            opacity: 0.7;
        }}

        .company-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 1.5rem;
        }}

        .company-title-area h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .ticker-badge {{
            font-size: 0.85rem;
            font-weight: 600;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            background: rgba(168, 85, 247, 0.15);
            border: 1px solid rgba(168, 85, 247, 0.3);
            color: #d8b4fe;
        }}

        .company-meta {{
            display: flex;
            gap: 1.5rem;
            margin-top: 0.5rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}

        .meta-item strong {{
            color: var(--text-primary);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            width: 100%;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 16px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            transition: background 0.2s ease;
        }}

        .stat-card:hover {{
            background: rgba(255, 255, 255, 0.04);
        }}

        .stat-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 500;
        }}

        .stat-value {{
            font-size: 1.6rem;
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
        }}

        .stat-value.up {{
            color: var(--accent-green);
        }}

        .stat-value.down {{
            color: var(--accent-red);
        }}

        .chart-container {{
            position: relative;
            height: 450px;
            width: 100%;
            margin-bottom: 1.5rem;
        }}

        .chart-controls {{
            display: flex;
            justify-content: flex-end;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }}

        .btn-toggle {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .btn-toggle:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}

        .btn-toggle.active {{
            background: var(--accent-purple);
            border-color: var(--accent-purple);
            box-shadow: 0 0 12px rgba(168, 85, 247, 0.3);
        }}

        .analysis-text {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 1.25rem;
            font-size: 0.95rem;
            color: var(--text-secondary);
            border-left: 4px solid var(--accent-purple);
        }}

        .analysis-text p strong {{
            color: var(--text-primary);
        }}

        footer {{
            max-width: 1400px;
            margin: 4rem auto 0 auto;
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 2rem;
        }}

        @media (max-width: 768px) {{
            .company-header {{
                flex-direction: column;
                align-items: stretch;
            }}
            .chart-container {{
                height: 350px;
            }}
        }}
    </style>
</head>
<body>

    <header>
        <h1>Hyperliquid Pre-IPO price tracking</h1>
        <p class="subtitle">An analysis of the alignment and efficiency of Trade.xyz synthetic perpetual contracts compared to actual NASDAQ stock listings before and after IPO dates.</p>
    </header>

    <main class="dashboard-grid">
"""

    # Generate section for each company
    company_descriptions = {
        "Cerebras": "Cerebras Systems (CBRS) represented a highly efficient pre-IPO price discovery phase. The Hyperliquid contract closed at $289.00 on the eve of the IPO, within 7.09% of the eventual Nasdaq debut close of $311.07. Post-IPO, the perpetual contract has tracked the spot stock with a 0.9890 correlation, demonstrating robust arbitrage alignment.",
        "SpaceX": "SpaceX (SPCX) pre-IPO perpetual contract traded for nearly four weeks, acting as an active sentiment barometer. The perpetual contract converged to $172.84 prior to the IPO, aligning closely with the opening trading range ($160.95 close on debut). Post-IPO, arbitrage maintained a near-perfect correlation of 0.9906.",
        "Quantinuum": "Quantinuum (QNT) experienced significant pre-IPO speculation, driving the perpetual price to a peak of $97.43 on thin volume before listing. The actual IPO priced conservatively at $60.00, resulting in a large initial divergence (+61.36%) which rapidly corrected post-listing. Post-IPO correlation stabilized at 0.9961."
    }

    for company, info in prices.items():
        comp_stats = stats[company]
        desc = company_descriptions[company]
        
        # Color formats
        dev_class = "up" if comp_stats["pre_ipo_deviation_pct"] > 0 else "down"
        dev_sign = "+" if comp_stats["pre_ipo_deviation_pct"] > 0 else ""
        
        html_content += f"""
        <!-- {company} Section -->
        <section class="company-section" id="section-{company.lower()}">
            <div class="company-header">
                <div class="company-title-area">
                    <h2>{company} <span class="ticker-badge">Perp: {info["ticker_hl"]} &bull; Stock: {info["ticker_stock"]}</span></h2>
                    <div class="company-meta">
                        <div class="meta-item">Listing Date: <strong>{info["ipo_date"]}</strong></div>
                        <div class="meta-item">Pre-IPO Trading: <strong>{comp_stats["pre_ipo_length_days"]} days</strong></div>
                    </div>
                </div>
                <div class="chart-controls">
                    <button class="btn-toggle active" id="btn-full-{company.lower()}" onclick="toggleView('{company.lower()}', 'full')">Full History</button>
                    <button class="btn-toggle" id="btn-post-{company.lower()}" onclick="toggleView('{company.lower()}', 'post')">Post-IPO Only</button>
                    <button class="btn-toggle" id="btn-hourly-{company.lower()}" onclick="toggleView('{company.lower()}', 'hourly')">Listing Day Hourly</button>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-label">Correlation (Post-IPO)</span>
                    <span class="stat-value" style="color: var(--accent-purple);">{comp_stats["correlation"]:.4f}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Last Pre-IPO Price</span>
                    <span class="stat-value">${comp_stats["last_pre_ipo_price"]:.2f}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">IPO Day Close</span>
                    <span class="stat-value">${comp_stats["first_stock_price"]:.2f}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Pre-IPO Deviation</span>
                    <span class="stat-value {dev_class}">{dev_sign}{comp_stats["pre_ipo_deviation_pct"]:.2f}%</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Mean Abs. Deviation</span>
                    <span class="stat-value" style="color: var(--accent-orange);">{comp_stats["mean_abs_deviation_pct"]:.2f}%</span>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="chart-{company.lower()}"></canvas>
            </div>

            <div class="analysis-text">
                <p><strong>Market Dynamics:</strong> {desc}</p>
            </div>
        </section>
        """

    # Add raw data array and charts initiation scripts
    html_content += f"""
    </main>

    <footer>
        <p>&copy; 2026 Antigravity Analytics. Data sourced via Hyperliquid Info API and Yahoo Finance API.</p>
    </footer>

    <script>
        const rawData = {json.dumps(prices)};
        const hourlyData = {json.dumps(hourly_data)};
        const charts = {{}};

        function initChart(compId, ipoDate, data, isHourly = false) {{
            const ctx = document.getElementById('chart-' + compId).getContext('2d');
            
            // Find index of IPO Date to add vertical line
            const ipoIndex = isHourly ? -1 : data.map(d => d.Date).indexOf(ipoDate);

            let chartConfig;

            if (isHourly) {{
                // Checking if chartjs financial is loaded, if not, fallback to dual line chart
                const canUseCandles = (typeof Chart.registry !== 'undefined' && Chart.registry.controllers.items && Chart.registry.controllers.items.candlestick);
                
                const prepDate = (timeStr) => {{
                    const parts = timeStr.split(":");
                    const hour = parseInt(parts[0]);
                    const min = parseInt(parts[1]);
                    const ipoParts = ipoDate.split("-");
                    const year = parseInt(ipoParts[0]);
                    const month = parseInt(ipoParts[1]);
                    const day = parseInt(ipoParts[2]);
                    return luxon.DateTime.utc(year, month, day, hour, min).valueOf();
                }};

                if (canUseCandles) {{
                    const perpCandles = data.map(d => ({{
                        x: prepDate(d.Time),
                        o: d.Perp_O,
                        h: d.Perp_H,
                        l: d.Perp_L,
                        c: d.Perp_C
                    }}));

                    const stockCandles = data.map(d => ({{
                        x: prepDate(d.Time),
                        o: d.Stock_O,
                        h: d.Stock_H,
                        l: d.Stock_L,
                        c: d.Stock_C
                    }}));

                    chartConfig = {{
                        type: 'candlestick',
                        data: {{
                            datasets: [
                                {{
                                    label: 'Hyperliquid Perpetual Future',
                                    data: perpCandles,
                                    color: {{
                                        up: '#10b981',
                                        down: '#ef4444',
                                        unchanged: '#a855f7',
                                    }},
                                    borderColor: {{
                                        up: '#10b981',
                                        down: '#ef4444',
                                        unchanged: '#a855f7',
                                    }}
                                }},
                                {{
                                    label: 'Nasdaq Stock',
                                    data: stockCandles,
                                    color: {{
                                        up: '#3b82f6',
                                        down: '#f97316',
                                        unchanged: '#9ca3af',
                                    }},
                                    borderColor: {{
                                        up: '#3b82f6',
                                        down: '#f97316',
                                        unchanged: '#9ca3af',
                                    }}
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'bottom',
                                    labels: {{ color: '#9ca3af', font: {{ family: 'Inter', size: 12 }} }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                    titleFont: {{ family: 'Outfit', size: 13, weight: 'bold' }},
                                    bodyFont: {{ family: 'Inter', size: 12 }},
                                    borderColor: 'rgba(255, 255, 255, 0.1)',
                                    borderWidth: 1,
                                    padding: 12
                                }}
                            }},
                            scales: {{
                                x: {{
                                    type: 'time',
                                    time: {{
                                        unit: 'minute',
                                        stepSize: 15,
                                        displayFormats: {{
                                            minute: 'HH:mm'
                                        }},
                                        tooltipFormat: 'HH:mm UTC'
                                    }},
                                    grid: {{ color: 'rgba(255, 255, 255, 0.03)', drawBorder: false }},
                                    ticks: {{ color: '#9ca3af', font: {{ family: 'Inter', size: 11 }} }}
                                }},
                                y: {{
                                    grid: {{ color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }},
                                    ticks: {{
                                        color: '#9ca3af',
                                        font: {{ family: 'Inter', size: 11 }},
                                        callback: function(value) {{ return '$' + value; }}
                                    }}
                                }}
                            }}
                        }}
                    }};
                }} else {{
                    // Fallback to highly granular dual line chart using OHLC Close prices
                    const labels = data.map(d => d.Time);
                    const perpData = data.map(d => d.Perp_C);
                    const stockData = data.map(d => d.Stock_C);

                    chartConfig = {{
                        type: 'line',
                        data: {{
                            labels: labels,
                            datasets: [
                                {{
                                    label: 'Hyperliquid Perp Close',
                                    data: perpData,
                                    borderColor: '#10b981',
                                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6,
                                    tension: 0.15,
                                    fill: true
                                }},
                                {{
                                    label: 'Nasdaq Stock Close',
                                    data: stockData,
                                    borderColor: '#3b82f6',
                                    backgroundColor: 'transparent',
                                    borderWidth: 3,
                                    pointRadius: 4,
                                    pointHoverRadius: 6,
                                    tension: 0.15
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'bottom',
                                    labels: {{ color: '#9ca3af', font: {{ family: 'Inter', size: 12 }} }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                    titleFont: {{ family: 'Outfit', size: 13, weight: 'bold' }},
                                    bodyFont: {{ family: 'Inter', size: 12 }},
                                    borderColor: 'rgba(255, 255, 255, 0.1)',
                                    borderWidth: 1,
                                    padding: 12,
                                    displayColors: true,
                                    callbacks: {{
                                        label: function(context) {{
                                            let label = context.dataset.label || '';
                                            if (label) {{
                                                label += ': ';
                                            }}
                                            if (context.parsed.y !== null) {{
                                                label += '$' + context.parsed.y.toFixed(2);
                                            }}
                                            return label;
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    grid: {{ color: 'rgba(255, 255, 255, 0.03)', drawBorder: false }},
                                    ticks: {{ color: '#9ca3af', font: {{ family: 'Inter', size: 11 }} }}
                                }},
                                y: {{
                                    grid: {{ color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }},
                                    ticks: {{
                                        color: '#9ca3af',
                                        font: {{ family: 'Inter', size: 11 }},
                                        callback: function(value) {{ return '$' + value; }}
                                    }}
                                }}
                            }}
                        }}
                    }};
                }}
            }} else {{
                const labels = data.map(d => d.Date);
                const perpData = data.map(d => d.Perp_Close);
                const stockData = data.map(d => d.Stock_Close);

                chartConfig = {{
                    type: 'line',
                    data: {{
                        labels: labels,
                        datasets: [
                            {{
                                label: 'Hyperliquid Perpetual Close',
                                data: perpData,
                                borderColor: '#a855f7',
                                backgroundColor: 'rgba(168, 85, 247, 0.05)',
                                borderWidth: 3,
                                pointRadius: 2,
                                pointHoverRadius: 6,
                                tension: 0.15,
                                fill: true
                            }},
                            {{
                                label: 'Nasdaq Stock Close',
                                data: stockData,
                                borderColor: '#f97316',
                                backgroundColor: 'transparent',
                                borderWidth: 3,
                                pointRadius: data.map(d => d.Stock_Close !== null ? 3 : 0),
                                pointHoverRadius: 6,
                                spanGaps: true,
                                tension: 0.15
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{
                                    color: '#9ca3af',
                                    font: {{ family: 'Inter', size: 12 }}
                                }}
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                                titleFont: {{ family: 'Outfit', size: 13, weight: 'bold' }},
                                bodyFont: {{ family: 'Inter', size: 12 }},
                                borderColor: 'rgba(255, 255, 255, 0.1)',
                                borderWidth: 1,
                                padding: 12,
                                displayColors: true,
                                callbacks: {{
                                    label: function(context) {{
                                        let label = context.dataset.label || '';
                                        if (label) {{
                                            label += ': ';
                                        }}
                                        if (context.parsed.y !== null) {{
                                            label += '$' + context.parsed.y.toFixed(2);
                                        }} else {{
                                            label += 'N/A (Market Closed)';
                                        }}
                                        return label;
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            x: {{
                                grid: {{ color: 'rgba(255, 255, 255, 0.03)', drawBorder: false }},
                                ticks: {{ color: '#9ca3af', maxRotation: 45, font: {{ family: 'Inter', size: 11 }} }}
                            }},
                            y: {{
                                grid: {{ color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }},
                                ticks: {{
                                    color: '#9ca3af',
                                    font: {{ family: 'Inter', size: 11 }},
                                    callback: function(value) {{ return '$' + value; }}
                                }}
                            }}
                        }}
                    }}
                }};

                // Custom plugin to draw vertical line at IPO Date
                if (ipoIndex !== -1) {{
                    chartConfig.plugins = chartConfig.plugins || [];
                    chartConfig.plugins.push({{
                        id: 'ipoLine',
                        afterDraw: (chart) => {{
                            const ctx = chart.ctx;
                            const xAxis = chart.scales.x;
                            const yAxis = chart.scales.y;
                            const x = xAxis.getPixelForValue(ipoDate);

                            if (x >= xAxis.left && x <= xAxis.right) {{
                                ctx.save();
                                ctx.beginPath();
                                ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
                                ctx.lineWidth = 1.5;
                                ctx.setLineDash([5, 5]);
                                ctx.moveTo(x, yAxis.top);
                                ctx.lineTo(x, yAxis.bottom);
                                ctx.stroke();

                                // Draw "IPO Date" text label
                                ctx.fillStyle = '#ffffff';
                                ctx.font = 'bold 10px Outfit';
                                ctx.fillText('IPO: ' + ipoDate, x + 6, yAxis.top + 20);
                                ctx.restore();
                            }}
                        }}
                    }});
                }}
            }}

            charts[compId] = new Chart(ctx, chartConfig);
        }}

        function toggleView(compId, viewType) {{
            const compName = compId === 'cerebras' ? 'Cerebras' : compId === 'spacex' ? 'SpaceX' : 'Quantinuum';
            const companyInfo = rawData[compName];
            const ipoDate = companyInfo.ipo_date;
            
            // Update active button state
            document.getElementById('btn-full-' + compId).classList.toggle('active', viewType === 'full');
            document.getElementById('btn-post-' + compId).classList.toggle('active', viewType === 'post');
            document.getElementById('btn-hourly-' + compId).classList.toggle('active', viewType === 'hourly');

            let filteredData = companyInfo.data;
            let isHourly = false;
            if (viewType === 'post') {{
                filteredData = companyInfo.data.filter(d => d.Date >= ipoDate);
            }} else if (viewType === 'hourly') {{
                filteredData = hourlyData[compName].hourly_data;
                isHourly = true;
            }}

            // Destroy and rebuild chart
            if (charts[compId]) {{
                charts[compId].destroy();
            }}
            initChart(compId, ipoDate, filteredData, isHourly);
        }}

        // Initialize all charts on load
        window.addEventListener('DOMContentLoaded', () => {{
            initChart('cerebras', rawData['Cerebras'].ipo_date, rawData['Cerebras'].data);
            initChart('spacex', rawData['SpaceX'].ipo_date, rawData['SpaceX'].data);
            initChart('quantinuum', rawData['Quantinuum'].ipo_date, rawData['Quantinuum'].data);
        }});
    </script>
</body>
</html>
"""

    with open("index.html", "w") as f:
        f.write(html_content)
    print("Successfully generated index.html")

if __name__ == "__main__":
    main()
