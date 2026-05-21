# 雲端 POS 找零版

已內建 Google Apps Script Web App URL：
https://script.google.com/macros/s/AKfycbyH_TkFMglBT5QFAp_0XS81_UQS7vBbcAqNVahmW9mScyXlDvMsovB0xRk7CXx11TM1VA/exec

## 啟動方式
python -m streamlit run app.py

## Google Sheet sales 第一列欄位請改成：
order_id, datetime, product, quantity, price, cost, total, gross_profit, payment_method, paid_amount, change_amount

## Apps Script
請把 Code.gs 改成 apps_script_code.txt 裡面的內容，然後重新部署 Web App。
