---
layout: default
title: Walmart Parser
description: Simple and effective Walmart scraper
theme: jekyll-theme-cayman
show_downloads: false
github:
  is_project_page: false
---

# Walmart Parser

<style>
.btn[href*="github.com"] {
  display: none !important;
}
</style>

Parsing Walmart products using API.
<br>
Works with UPC/EAN or Product ID. Saves results to Excel.

## 🔧 Features:
- Search for products by UPC/EAN
- Saving results data to Excel
- Multithreading
- Easy to use interface

## 🧑‍💻 Hot to use:
1. Launch the application
2. Select search mode
4. Select .csv or Excel-file with Product ID or UPC/EAN
5. Press "Start"
6. Open results in Excel

## 🖼 Screenshots


## ❓ FAQ

**Q:** What input data is needed?  
**A:** Just a list of product IDs or UPCs with prices.

**Q:** What results will I get?
**A:** You will receive an Excel file with columns that you can customize via Settings → Configure Columns.

**Q:** How fast is the parsing?  
**A:** Around 100 products in 5 minutes. The parsing speed is limited by Walmart API throughput and possible rate limiting or blocks from the site.