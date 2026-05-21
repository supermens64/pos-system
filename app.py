
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="雲端 POS 系統", layout="wide")

TOKEN = "123456"
API_URL = "https://script.google.com/macros/s/AKfycbyH_TkFMglBT5QFAp_0XS81_UQS7vBbcAqNVahmW9mScyXlDvMsovB0xRk7CXx11TM1VA/exec"

st.sidebar.title("雲端 POS 系統")
st.sidebar.caption("已內建 Google Apps Script 正式網址")
page = st.sidebar.radio("選擇功能", ["點餐", "銷售統計"])

def get_json(url):
    r = requests.get(url, timeout=20, allow_redirects=True)
    text = r.text.strip()
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}\n{text[:500]}")
    if not text:
        raise Exception("Google Apps Script 回傳空白內容")
    try:
        return r.json()
    except Exception:
        raise Exception("回傳內容不是 JSON：\n" + text[:500])

@st.cache_data(ttl=30)
def load_products():
    return pd.DataFrame(get_json(f"{API_URL}?action=products&token={TOKEN}"))

@st.cache_data(ttl=30)
def load_sales():
    return pd.DataFrame(get_json(f"{API_URL}?action=sales&token={TOKEN}"))

def save_order(records):
    payload = {"token": TOKEN, "records": records}
    r = requests.post(API_URL, json=payload, timeout=20, allow_redirects=True)
    text = r.text.strip()
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}\n{text[:500]}")
    try:
        return r.json()
    except Exception:
        raise Exception("寫入回傳內容不是 JSON：\n" + text[:500])

if "cart" not in st.session_state:
    st.session_state.cart = {}

try:
    products = load_products()
except Exception as e:
    st.error("讀取 Google Sheet 商品資料失敗")
    st.code(str(e))
    st.stop()

products["price"] = pd.to_numeric(products["price"], errors="coerce").fillna(0).astype(int)
products["cost"] = pd.to_numeric(products["cost"], errors="coerce").fillna(0).astype(int)

if page == "點餐":
    st.title("點餐 / 結帳")
    left, right = st.columns([2, 1])

    with left:
        st.subheader("商品列表")
        categories = ["全部"] + sorted(products["category"].dropna().astype(str).unique().tolist())
        selected_category = st.selectbox("商品分類", categories)
        display_products = products if selected_category == "全部" else products[products["category"].astype(str) == selected_category]

        for _, row in display_products.iterrows():
            product = str(row["product"])
            price = int(row["price"])
            cost = int(row["cost"])
            category = str(row["category"])

            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"### {product}")
                st.caption(f"分類：{category}")
            with c2:
                st.markdown(f"### ${price}")
            with c3:
                if st.button("加入", key=f"add_{product}", use_container_width=True):
                    if product not in st.session_state.cart:
                        st.session_state.cart[product] = {"quantity": 0, "price": price, "cost": cost}
                    st.session_state.cart[product]["quantity"] += 1
                    st.rerun()
            st.divider()

    with right:
        st.subheader("本次訂單")

        if len(st.session_state.cart) == 0:
            st.info("尚未選擇商品")
        else:
            total_amount = 0
            for product, item in list(st.session_state.cart.items()):
                quantity = int(item["quantity"])
                price = int(item["price"])
                total = quantity * price
                total_amount += total

                st.write(f"**{product}**")
                st.write(f"{quantity} 份 × ${price} = **${total}**")

                p1, p2, p3 = st.columns(3)
                if p1.button("＋", key=f"plus_{product}", use_container_width=True):
                    st.session_state.cart[product]["quantity"] += 1
                    st.rerun()
                if p2.button("－", key=f"minus_{product}", use_container_width=True):
                    st.session_state.cart[product]["quantity"] -= 1
                    if st.session_state.cart[product]["quantity"] <= 0:
                        del st.session_state.cart[product]
                    st.rerun()
                if p3.button("刪除", key=f"delete_{product}", use_container_width=True):
                    del st.session_state.cart[product]
                    st.rerun()
                st.divider()

            st.markdown(f"# 總金額：${total_amount}")
            payment_method = st.selectbox("付款方式", ["現金", "Line Pay", "街口支付", "信用卡", "其他"])

            st.subheader("收款 / 找零")
            default_paid = total_amount if payment_method != "現金" else 0
            paid_amount = st.number_input("客人付款金額", min_value=0, step=10, value=default_paid)
            change_amount = paid_amount - total_amount

            if paid_amount == 0:
                st.info("請輸入客人付款金額")
            elif change_amount < 0:
                st.error(f"付款不足，還差 ${abs(change_amount)}")
            else:
                st.success(f"應找零：${change_amount}")

            can_checkout = paid_amount >= total_amount

            if st.button("結帳", type="primary", use_container_width=True, disabled=not can_checkout):
                order_id = datetime.now().strftime("%Y%m%d%H%M%S")
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                records = []
                for product, item in st.session_state.cart.items():
                    quantity = int(item["quantity"])
                    price = int(item["price"])
                    cost = int(item["cost"])
                    total = quantity * price
                    gross_profit = total - quantity * cost
                    records.append({
                        "order_id": order_id,
                        "datetime": now,
                        "product": product,
                        "quantity": quantity,
                        "price": price,
                        "cost": cost,
                        "total": total,
                        "gross_profit": gross_profit,
                        "payment_method": payment_method,
                        "paid_amount": int(paid_amount),
                        "change_amount": int(change_amount)
                    })

                try:
                    result = save_order(records)
                    if result.get("success") == True:
                        st.session_state.cart = {}
                        load_sales.clear()
                        st.success("結帳完成！銷售資料已寫入 Google Sheet。")
                        st.rerun()
                    else:
                        st.error("寫入失敗")
                        st.write(result)
                except Exception as e:
                    st.error("寫入 Google Sheet 失敗")
                    st.code(str(e))

            if st.button("清空訂單", use_container_width=True):
                st.session_state.cart = {}
                st.rerun()

elif page == "銷售統計":
    st.title("銷售統計")
    if st.button("重新整理資料"):
        load_sales.clear()
        st.rerun()

    try:
        sales = load_sales()
    except Exception as e:
        st.error("讀取銷售資料失敗")
        st.code(str(e))
        st.stop()

    if sales.empty or "datetime" not in sales.columns:
        st.info("目前還沒有銷售資料")
    else:
        sales["datetime"] = pd.to_datetime(sales["datetime"], errors="coerce")
        for col in ["quantity", "total", "gross_profit", "paid_amount", "change_amount"]:
            if col in sales.columns:
                sales[col] = pd.to_numeric(sales[col], errors="coerce").fillna(0).astype(int)

        selected_date = st.date_input("選擇日期", datetime.today())
        day_sales = sales[sales["datetime"].dt.date == selected_date]

        if len(day_sales) == 0:
            st.warning("這一天沒有銷售資料")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("營收", f"${day_sales['total'].sum():,.0f}")
            c2.metric("毛利", f"${day_sales['gross_profit'].sum():,.0f}")
            c3.metric("訂單數", f"{day_sales['order_id'].nunique()}")
            c4.metric("售出份數", f"{day_sales['quantity'].sum()}")

            st.subheader("商品銷售排行")
            summary = day_sales.groupby("product").agg(
                總銷量=("quantity", "sum"),
                總營收=("total", "sum"),
                總毛利=("gross_profit", "sum")
            ).reset_index().sort_values("總銷量", ascending=False)
            st.dataframe(summary, use_container_width=True)

            st.subheader("付款方式統計")
            payment_summary = day_sales.groupby("payment_method").agg(
                營收=("total", "sum"),
                訂單數=("order_id", "nunique")
            ).reset_index()
            st.dataframe(payment_summary, use_container_width=True)

            st.subheader("銷售明細")
            st.dataframe(day_sales.sort_values("datetime", ascending=False), use_container_width=True)
