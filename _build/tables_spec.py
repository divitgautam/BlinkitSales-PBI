"""Table and column declarations for the BlinkitSales-PBI semantic model (clean CSVs in data/clean)."""
RUPEE = "₹"
H = True
# table -> (description, [(source column, name, dataType, formatString, hidden, description)])
SPEC = {
    "fact_orders": ("One row per order (5,000): order header, its single item line, delivery and customer feedback merged 1:1. "
                    "Revenue = Order Total. Source: data/clean/fact_orders.csv.", [
        ("order_id", "Order Id", "int64", "0", False, "Order identifier (unique)."),
        ("customer_id", "Customer Id", "int64", "0", H, "Foreign key to dim_customer."),
        ("product_id", "Product Id", "int64", "0", H, "Foreign key to dim_product (one item per order)."),
        ("order_date", "Order Date", "dateTime", "dd-mmm-yyyy", H, "Order date. Foreign key to the Date table."),
        ("order_hour", "Order Hour", "int64", "0", False, "Hour of day the order was placed, 0-23."),
        ("order_total", "Order Total", "decimal", f"{RUPEE}#,##0.00", H, "Order header total in assumed INR. Source of Revenue."),
        ("line_value", "Line Amount", "decimal", f"{RUPEE}#,##0.00", H, "Quantity x unit price. Source of Line Value; does not reconcile to Order Total."),
        ("quantity", "Quantity", "int64", "0", H, "Units on the item line, 1-3."),
        ("unit_price", "Unit Price", "decimal", f"{RUPEE}#,##0.00", False, "Item unit price in assumed INR."),
        ("payment_method", "Payment Method", "string", None, False, "Card, Cash, UPI or Wallet."),
        ("delivery_status", "Delivery Status", "string", None, False, "On Time (up to 5 minutes late), Slightly Delayed or Significantly Delayed."),
        ("delivery_status_order", "Delivery Status Order", "int64", "0", H, "Sort order for Delivery Status (from Power Query source, not DAX, to avoid a circular sort-by)."),
        ("minutes_late", "Minutes Late", "int64", "0", False, "Actual minus promised delivery time in minutes; negative means early."),
        ("is_late", "Is Late", "boolean", None, False, "TRUE when the status is not On Time (more than 5 minutes late)."),
        ("distance_km", "Distance Km", "decimal", "0.00", False, "Delivery distance in kilometres."),
        ("rating", "Rating", "int64", "0", False, "Customer rating, 1 to 5 stars."),
        ("sentiment", "Sentiment", "string", None, False, "Feedback sentiment: Positive, Neutral or Negative."),
        ("feedback_category", "Feedback Category", "string", None, False, "Delivery, Customer Service, Product Quality or App Experience."),
        ("poor_experience", "Poor Experience", "boolean", None, False, "TRUE when the order was late or rated 1-2 stars. Basis of Revenue at Risk."),
    ]),
    "fact_marketing": ("One row per campaign record (5,400). No key to orders: attributed revenue is a separate star and is not order revenue. "
                       "Source: data/clean/fact_marketing.csv.", [
        ("campaign_name", "Campaign Name", "string", None, False, "Campaign name (9 campaigns)."),
        ("date", "Campaign Date", "dateTime", "dd-mmm-yyyy", H, "Record date. Foreign key to the Date table."),
        ("channel", "Channel", "string", None, False, "App, Email, SMS or Social Media."),
        ("target_audience", "Target Audience", "string", None, False, "All audiences (campaigns aimed at everyone, not a total), Inactive, New Users or Premium."),
        ("impressions", "Impressions", "int64", "#,##0", H, "Impressions served. Source of Total Impressions."),
        ("clicks", "Clicks", "int64", "#,##0", H, "Clicks. Source of Total Clicks."),
        ("conversions", "Conversions", "int64", "#,##0", H, "Conversions. Source of Total Conversions."),
        ("spend", "Spend", "decimal", f"{RUPEE}#,##0.00", H, "Campaign spend in assumed INR."),
        ("attributed_revenue", "Attributed Revenue", "decimal", f"{RUPEE}#,##0.00", H, "Revenue attributed to the campaign by the source (not order revenue)."),
    ]),
    "fact_inventory": ("Stock received and damaged per product and month (5,571 rows, from the monthly inventoryNew file). "
                       "Source: data/clean/fact_inventory.csv.", [
        ("product_id", "Product Id", "int64", "0", H, "Foreign key to dim_product."),
        ("month_start", "Month Start", "dateTime", "mmm yyyy", H, "First day of the month. Foreign key to the Date table."),
        ("stock_received", "Units Received", "int64", "#,##0", H, "Units received. Source of Stock Received."),
        ("damaged_stock", "Units Damaged", "int64", "#,##0", H, "Units damaged. Source of Damaged Stock."),
    ]),
    "dim_product": ("One row per product (268). Brand is almost one per product and product names repeat, so use Product Label or Category. "
                    "Source: data/clean/dim_product.csv.", [
        ("product_id", "Product Id", "int64", "0", H, "Product key."),
        ("product_name", "Product Name", "string", None, False, "Product name (51 distinct names across 268 products)."),
        ("product_label", "Product Label", "string", None, False, "Product name plus id; unique, use it in visuals."),
        ("category", "Category", "string", None, False, "Product category (11 categories)."),
        ("brand", "Brand", "string", None, False, "Brand (about one per product)."),
        ("price", "Price", "decimal", f"{RUPEE}#,##0.00", False, "List price in assumed INR."),
        ("mrp", "MRP", "decimal", f"{RUPEE}#,##0.00", False, "Maximum retail price in assumed INR."),
        ("margin_percentage", "Margin Percentage", "decimal", "0.0", False, "Stored margin as a percentage number, 15-40."),
        ("shelf_life_days", "Shelf Life Days", "int64", "0", False, "Shelf life in days."),
        ("min_stock_level", "Min Stock Level", "int64", "0", False, "Minimum stock level."),
        ("max_stock_level", "Max Stock Level", "int64", "0", False, "Maximum stock level."),
    ]),
    "dim_customer": ("One row per customer in the customer file (2,500; 2,172 have orders). Name, email, phone and address are not loaded. "
                     "Lifetime figures come from the orders table. Source: data/clean/dim_customer.csv.", [
        ("customer_id", "Customer Id", "int64", "0", H, "Customer key."),
        ("area", "Area", "string", None, False, "Customer area."),
        ("pincode", "Pincode", "string", None, False, "Postal code."),
        ("registration_date", "Registration Date", "dateTime", "dd-mmm-yyyy", False, "Stored registration date (unreliable: many orders precede it)."),
        ("segment", "Segment", "string", None, False, "Stored segment: Regular, Premium, New or Inactive."),
        ("first_order_date", "First Order Date", "dateTime", "dd-mmm-yyyy", False, "Date of the customer's first order; blank without orders."),
        ("orders", "Lifetime Orders", "int64", "0", False, "Orders placed over the whole period (not affected by slicers)."),
        ("revenue", "Lifetime Revenue", "decimal", f"{RUPEE}#,##0.00", False, "Order Total summed over the whole period (not affected by slicers)."),
        ("customer_type", "Customer Type", "string", None, False, "New (1 order), Repeat (2+ orders) or No orders."),
    ]),
    "Forecast": ("Monthly revenue on full months (Apr 2023 to Oct 2024, Actual) and the forecast to Dec 2025 with an 80% band. Disconnected from Date by design. "
                 "Source: data/clean/forecast.csv written by _build/forecast.py.", [
        ("month_start", "Month Start", "dateTime", "mmm yyyy", False, "First day of the month."),
        ("kind", "Kind", "string", None, H, "Actual or Forecast row."),
        ("actual", "Actual", "decimal", "#,##0", H, "Actual monthly revenue (full months only)."),
        ("forecast", "Forecast", "decimal", "#,##0", H, "Forecast monthly revenue; the last actual month repeats here so the lines join."),
        ("low80", "Low 80", "decimal", "#,##0", H, "Lower end of the 80% band."),
        ("high80", "High 80", "decimal", "#,##0", H, "Upper end of the 80% band."),
    ]),
    "Levers": ("Sized revenue levers (annual, basis: last 12 full months) with their assumptions. Disconnected by design. "
               "Source: data/clean/levers.csv written by _build/forecast.py.", [
        ("lever", "Lever", "string", None, False, "Lever name."),
        ("lever_label", "Lever Label", "string", None, False, "Lever with its value type, for chart labels."),
        ("lever_type", "Lever Type", "string", None, False, "Exposure removed, attributed revenue gained or stock value saved: not additive across types."),
        ("assumption", "Assumption", "string", None, False, "What is assumed and how the value was sized."),
        ("annual_value", "Annual Value", "decimal", "#,##0", H, "Annual value in assumed INR. Source of Lever Value."),
        ("pct_of_revenue", "Pct of Revenue", "decimal", "0.0%", H, "Annual value as a share of the last 12 full months of revenue."),
        ("confidence", "Confidence", "string", None, False, "How far to trust the sizing."),
        ("basis", "Basis", "string", None, False, "Period the lever was sized on."),
    ]),
}
KEYS = {("dim_product", "Product Id"), ("dim_customer", "Customer Id")}
CATEGORY = {("dim_customer", "Pincode"): "PostalCode"}
REL_FROM = {("fact_orders", "Customer Id"), ("fact_orders", "Product Id"), ("fact_orders", "Order Date"), ("fact_marketing", "Campaign Date"),
            ("fact_inventory", "Product Id"), ("fact_inventory", "Month Start")}
RELS = [("fact_orders_Date", "fact_orders.'Order Date'", "Date.Date"),
        ("fact_marketing_Date", "fact_marketing.'Campaign Date'", "Date.Date"),
        ("fact_inventory_Date", "fact_inventory.'Month Start'", "Date.Date"),
        ("fact_orders_Product", "fact_orders.'Product Id'", "dim_product.'Product Id'"),
        ("fact_inventory_Product", "fact_inventory.'Product Id'", "dim_product.'Product Id'"),
        ("fact_orders_Customer", "fact_orders.'Customer Id'", "dim_customer.'Customer Id'")]
# calculated columns: (name, dtype, expression, format, hidden, sortBy, description)
CALC = {"Forecast": [
    ("Month Label", "string", 'FORMAT ( Forecast[Month Start], "MMM yy", "en-US" )', None, False, "Month Start", "Month label, e.g. Nov 24."),
    ("Year", "int64", "YEAR ( Forecast[Month Start] )", "0", H, None, "Calendar year of the month (used to total 2025)."),
], "fact_orders": [
    ("Minutes Late Band", "string",
     'VAR m = fact_orders[Minutes Late] RETURN SWITCH ( TRUE (), m < 0, "Early", m <= 5, "0 to 5", m <= 10, "6 to 10", m <= 15, "11 to 15", m <= 20, "16 to 20", m <= 25, "21 to 25", "26 to 30" )',
     None, False, "Minutes Late Band Order", "Minutes late in 5-minute bands (Early, 0 to 5, ... 26 to 30)."),
    ("Minutes Late Band Order", "int64",
     "VAR m = fact_orders[Minutes Late] RETURN SWITCH ( TRUE (), m < 0, 1, m <= 5, 2, m <= 10, 3, m <= 15, 4, m <= 20, 5, m <= 25, 6, 7 )", "0", H, None,
     "Sort order for Minutes Late Band."),
    ("Experience Class", "string",
     'SWITCH ( TRUE (), fact_orders[Is Late] && fact_orders[Rating] <= 2, "Late and low rating", fact_orders[Is Late], "Late only", '
     'fact_orders[Rating] <= 2, "Low rating only", "Good experience" )', None, False, "Experience Class Order",
     "Why an order counts as a poor experience: late, rated 1-2 stars, both, or neither."),
    ("Experience Class Order", "int64",
     "SWITCH ( TRUE (), fact_orders[Is Late] && fact_orders[Rating] <= 2, 1, fact_orders[Is Late], 2, fact_orders[Rating] <= 2, 3, 4 )", "0", H, None,
     "Sort order for Experience Class."),
]}
# the Delivery Status Order sort column: attach to Delivery Status
SORT_BY = {("fact_orders", "Delivery Status"): "Delivery Status Order"}
