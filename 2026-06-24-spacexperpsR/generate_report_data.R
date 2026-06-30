# C:/Users/matth/Downloads/spacexperpsR/generate_report_data.R
# Configure library path for headless execution
.libPaths("C:/Users/matth/Documents/R/win-library/4.6")
library(httr)
library(jsonlite)
library(ggplot2)

# Set working directory to workspace
setwd("C:/Users/matth/Downloads/spacexperpsR")

# 1. Fetch Hyperliquid perpetual data (xyz:SPCX)
print("Fetching Hyperliquid perpetual data...")
url_hl <- "https://api.hyperliquid.xyz/info"
body_hl <- toJSON(list(
  type = "candleSnapshot",
  req = list(
    coin = "xyz:SPCX",
    interval = "1d",
    startTime = 1776297600000  # May 1, 2026 (covers May 18 launch)
  )
), auto_unbox = TRUE)

res_hl <- POST(
  url = url_hl,
  add_headers("Content-Type" = "application/json"),
  body = body_hl
)

if (status_code(res_hl) != 200) {
  stop("Failed to fetch Hyperliquid data: ", status_code(res_hl))
}

content_hl <- content(res_hl, as = "text", encoding = "UTF-8")
candles_hl <- fromJSON(content_hl)

df_perps <- data.frame(
  Date = as.Date(as.POSIXct(candles_hl$t / 1000, origin = "1970-01-01", tz = "UTC")),
  Perp_Open = as.numeric(candles_hl$o),
  Perp_High = as.numeric(candles_hl$h),
  Perp_Low = as.numeric(candles_hl$l),
  Perp_Close = as.numeric(candles_hl$c),
  Perp_Volume = as.numeric(candles_hl$v),
  stringsAsFactors = FALSE
)
print(paste("Parsed", nrow(df_perps), "rows of perpetual data."))

# 2. Fetch Yahoo Finance Stock Data for SPCX
print("Fetching Yahoo Finance stock data...")
url_yf <- "https://query1.finance.yahoo.com/v8/finance/chart/SPCX"
now_ts <- as.character(as.integer(Sys.time()))

res_yf <- GET(
  url = url_yf,
  query = list(
    period1 = "1779020400",  # May 18, 2026
    period2 = now_ts,
    interval = "1d"
  ),
  user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
)

if (status_code(res_yf) != 200) {
  stop("Failed to fetch Yahoo Finance stock data: ", status_code(res_yf))
}

content_yf <- content(res_yf, as = "text", encoding = "UTF-8")
json_yf <- fromJSON(content_yf)
result_yf <- json_yf$chart$result

timestamps_yf <- result_yf$timestamp[[1]]
quote_yf <- result_yf$indicators$quote[[1]]

df_stock <- data.frame(
  Date = as.Date(as.POSIXct(timestamps_yf, origin = "1970-01-01", tz = "America/New_York")),
  Stock_Open = as.numeric(quote_yf$open[[1]]),
  Stock_High = as.numeric(quote_yf$high[[1]]),
  Stock_Low = as.numeric(quote_yf$low[[1]]),
  Stock_Close = as.numeric(quote_yf$close[[1]]),
  Stock_Volume = as.numeric(quote_yf$volume[[1]]),
  stringsAsFactors = FALSE
)

# Filter out empty rows (market holidays/weekends return NA)
df_stock <- df_stock[!is.na(df_stock$Stock_Close), ]
print(paste("Parsed", nrow(df_stock), "rows of stock data."))

# 3. Merge Datasets
print("Merging perpetual and stock data...")
df_merged <- merge(df_perps, df_stock, by = "Date", all.x = TRUE)

# Write output data
write.csv(df_merged, "spacex_prices.csv", row.names = FALSE)
print("Saved combined data to spacex_prices.csv")

# 4. Generate ggplot2 Chart for Post-IPO Period
print("Generating comparative performance chart...")
df_post_ipo <- df_merged[df_merged$Date >= as.Date("2026-06-12"), ]
df_stock_clean <- df_post_ipo[!is.na(df_post_ipo$Stock_Close), ]

p <- ggplot(df_post_ipo, aes(x = Date)) +
  # Plot perpetuals (continuous calendar days)
  geom_line(aes(y = Perp_Close, color = "Hyperliquid Perpetual (xyz:SPCX)"), linewidth = 1.2) +
  geom_point(aes(y = Perp_Close, color = "Hyperliquid Perpetual (xyz:SPCX)"), size = 2.5) +
  # Plot stock (trading days only, connecting non-NA values)
  geom_line(data = df_stock_clean, aes(y = Stock_Close, color = "Nasdaq Stock (SPCX)"), linewidth = 1.2) +
  geom_point(data = df_stock_clean, aes(y = Stock_Close, color = "Nasdaq Stock (SPCX)"), size = 2.5) +
  labs(
    title = "SpaceX (SPCX) Price Performance Comparison",
    subtitle = "Comparing Hyperliquid Perpetual (24/7) vs. Nasdaq Stock Close (June 12, 2026 - June 24, 2026)",
    x = "Date",
    y = "Closing Price (USD)",
    color = "Asset Type"
  ) +
  scale_color_manual(values = c(
    "Hyperliquid Perpetual (xyz:SPCX)" = "#8A2BE2", # Purple
    "Nasdaq Stock (SPCX)" = "#FF8C00"               # Orange
  )) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, hjust = 0.5, margin = margin(b = 8)),
    plot.subtitle = element_text(size = 10, hjust = 0.5, color = "#555555", margin = margin(b = 15)),
    legend.position = "bottom",
    legend.title = element_text(face = "bold"),
    panel.grid.major = element_line(color = "#EBEBEB"),
    panel.grid.minor = element_blank(),
    axis.title = element_text(face = "bold"),
    axis.text = element_text(color = "#333333"),
    plot.margin = margin(15, 15, 15, 15)
  )

ggsave("spacex_perp_vs_stock.png", plot = p, width = 10, height = 6, dpi = 300)
print("Saved comparison chart to spacex_perp_vs_stock.png")

# 5. Compute and print statistics
df_clean <- df_merged[!is.na(df_merged$Stock_Close), ]
correlation <- cor(df_clean$Perp_Close, df_clean$Stock_Close)
premium <- (df_clean$Perp_Close - df_clean$Stock_Close) / df_clean$Stock_Close * 100
mean_premium <- mean(premium)
mean_abs_premium <- mean(abs(premium))

cat("\n=========================================\n")
cat("        COMPARATIVE STATISTICS\n")
cat("=========================================\n")
cat(sprintf("Correlation (Perp vs Stock): %.4f\n", correlation))
cat(sprintf("Average Perp Premium:        %.2f%%\n", mean_premium))
cat(sprintf("Mean Absolute Deviation:     %.2f%%\n", mean_abs_premium))
cat("=========================================\n")

print("Process completed successfully.")
