import json
import random
import sys
from itertools import combinations
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 42
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "base"
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
for old in OUT.glob("*.csv"):
    old.unlink()
R = random.Random(SEED)

# column names differ per variant; "holdout" uses names the system was never tuned on
N = {"base": dict(cust_fk="client_ref", prod_fk="prod_code", order_pay="order_ref", order_ship="order_no",
                  order_ret="ord_ref", sku="sku", sup_fk="supplier_ref"),
     "holdout": dict(cust_fk="buyer_id", prod_fk="item_no", order_pay="ref_order", order_ship="ord_id",
                     order_ret="orig_order", sku="item_code", sup_fk="vendor_id")}[VARIANT]

FIRST = ("Asha Riya Neha Kiran Amit Priya Rahul Sneha Vikram Pooja Rohan Anjali Karan Meera Arjun Divya "
         "Nikhil Isha Varun Tanvi Manish Kavya Sahil Nisha Deepak Swati Harsh Komal Yash Ritu Aditya "
         "Bhavna Mohit Shreya Gaurav Pallavi Tarun Ekta Jay Hetal").split()
LAST = ("Patel Shah Desai Mehta Joshi Soni Trivedi Pandya Modi Parekh Thakkar Vyas Dave Bhatt Gandhi "
        "Kapadia Amin Chauhan Rana Solanki Sharma Verma Gupta Iyer Nair Reddy Rao Kulkarni Deshmukh Jain "
        "Agarwal Malhotra Kapoor Bose Sen Das Roy Ghosh Singh Khan").split()
CITIES = ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Mumbai", "Pune", "Delhi", "Bengaluru"]


def day(y0=2022, span=700):
    return (pd.Timestamp(f"{y0}-01-01") + pd.Timedelta(days=R.randint(0, span))).strftime("%Y-%m-%d")


def customer(cid):
    f, l = R.choice(FIRST), R.choice(LAST)
    return {"customer_id": cid, "full_name": f"{f} {l}", "email": f"{f}.{l}{cid}@mail.com".lower(),
            "phone": f"+91 9{R.randint(10**8, 10**9 - 1)}", "city": R.choice(CITIES),
            "created_at": day(), "total_spent": round(R.uniform(50, 5000), 2)}


def save(name, rows):
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    df.to_csv(OUT / name, index=False)


c1 = pd.DataFrame([customer(c) for c in range(1001, 1301)])
c2 = c1.copy()
idx = list(range(300))
R.shuffle(idx)
for i in idx[:25]:
    c2.loc[i, "city"] = R.choice([c for c in CITIES if c != c2.loc[i, "city"]])
for i in idx[25:30]:
    c2.loc[i, "created_at"] = R.choice(["2023-13-45", "2023-00-10", "2022-02-31"])
for i in idx[30:33]:
    c2.loc[i, "total_spent"] = -abs(c2.loc[i, "total_spent"])
conflicts = {col: int((c1[col].astype(str) != c2[col].astype(str)).sum())
             for col in ["full_name", "email", "phone", "city", "created_at", "total_spent"]}
conflicts = {k: v for k, v in conflicts.items() if v}

new = [customer(c) for c in range(1301, 1341)]
clusters = {int(c): [f"customers.csv:{c}", f"customers_v2.csv:{c}"] for c in c1.customer_id}
dups = []
for k, i in enumerate(R.sample(range(300), 15)):
    base = c1.iloc[i]
    f, l = base.full_name.split()
    row = base.to_dict()
    row.update(customer_id=1341 + k, full_name=f"{f[0]}. {l}" if k % 2 == 0 else base.full_name.upper(),
               created_at=day(), total_spent=round(R.uniform(50, 5000), 2))
    dups.append(row)
    clusters[int(base.customer_id)].append(f"customers_v2.csv:{1341 + k}")
v2 = pd.concat([c2, pd.DataFrame(new), pd.DataFrame(dups)], ignore_index=True)
save("customers.csv", c1)
save("customers_v2.csv", v2)

sup_ids = list(range(3001, 3016))
save("suppliers.csv", [{"supplier_id": s, "supplier_name": f"{R.choice(LAST)} Traders",
                        "contact_mail": f"sales{s}@supplier.example.com",
                        "country": R.choice(["India", "UAE", "China", "Germany"])} for s in sup_ids])
prods = [{"product_id": f"P{n:03d}", "product_name": f"Widget {R.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])} {n}",
          N["sup_fk"]: R.choice(sup_ids), "unit_price": round(R.uniform(5, 500), 2)} for n in range(1, 61)]
save("products.csv", prods)
emp = []
for n in range(40):
    f, l = R.choice(FIRST), R.choice(LAST)
    emp.append({"employee_id": 2001 + n, "name": f"{f} {l}", "email_address": f"{f}.{l}@corp.example.com".lower(),
                "department": R.choice(["Sales", "Ops", "Finance", "HR", "IT"]), "hire_date": day(2015, 2500)})
save("employees.csv", emp)

cust_ids = list(range(1001, 1341))
pids = [p["product_id"] for p in prods]
orders = [{"order_id": 50001 + n, N["cust_fk"]: R.choice(cust_ids), N["prod_fk"]: R.choice(pids),
           "order_date": day(2023, 500), "quantity": R.randint(1, 9)} for n in range(800)]
for k, i in enumerate(R.sample(range(800), 12)):
    orders[i][N["cust_fk"]] = 9001 + k
save("orders.csv", orders)

pay, n = [], 70001
for o in orders:
    if R.random() < 0.9:
        for _ in range(R.choice([1, 1, 1, 2])):
            pay.append({"payment_id": n, N["order_pay"]: o["order_id"], "amount": round(R.uniform(10, 2000), 2),
                        "paid_on": day(2023, 520)})
            n += 1
for k in range(6):
    pay[R.randrange(len(pay))][N["order_pay"]] = 59001 + k
save("payments.csv", pay)
save("shipping.csv", [{"shipment_id": 80001 + i, N["order_ship"]: o["order_id"],
                       "carrier": R.choice(["BlueDart", "DTDC", "Delhivery", "FedEx"]), "shipped_on": day(2023, 520)}
                      for i, o in enumerate(o for o in orders if R.random() < 0.85)])
save("returns.csv", [{"return_id": 90001 + k, N["order_ret"]: R.choice(orders)["order_id"],
                      "reason": R.choice(["damaged", "wrong item", "late", "changed mind"])} for k in range(60)])

units = {}
for o in orders:
    units[o[N["prod_fk"]]] = units.get(o[N["prod_fk"]], 0) + o["quantity"]
price = {p["product_id"]: p["unit_price"] for p in prods}
save("sales_report.csv", [{N["sku"]: k, "units_sold": v, "revenue": round(v * price[k], 2)}
                          for k, v in sorted(units.items())])

g = lambda f, c: [f, c]
groups = [
    [g("customers.csv", "customer_id"), g("customers_v2.csv", "customer_id"), g("orders.csv", N["cust_fk"])],
    [g("orders.csv", "order_id"), g("payments.csv", N["order_pay"]), g("shipping.csv", N["order_ship"]),
     g("returns.csv", N["order_ret"])],
    [g("products.csv", "product_id"), g("orders.csv", N["prod_fk"]), g("sales_report.csv", N["sku"])],
    [g("suppliers.csv", "supplier_id"), g("products.csv", N["sup_fk"])],
] + [[g("customers.csv", c), g("customers_v2.csv", c)]
     for c in ["full_name", "email", "phone", "city", "created_at", "total_spent"]]
truth = {
    "versions": {"customers_v2.csv": "customers.csv"},
    "column_groups": groups,
    "fks": [["customers.csv", "customer_id", "orders.csv", N["cust_fk"]],
            ["orders.csv", "order_id", "payments.csv", N["order_pay"]],
            ["orders.csv", "order_id", "shipping.csv", N["order_ship"]],
            ["orders.csv", "order_id", "returns.csv", N["order_ret"]],
            ["products.csv", "product_id", "orders.csv", N["prod_fk"]],
            ["suppliers.csv", "supplier_id", "products.csv", N["sup_fk"]]],
    "acceptable_fks": [["sales_report.csv", N["sku"], "orders.csv", N["prod_fk"]],
                       ["products.csv", "product_id", "sales_report.csv", N["sku"]],
                       ["sales_report.csv", N["sku"], "products.csv", "product_id"]],
    "entity_clusters": list(clusters.values()),
    "lineage": [["customers.csv", "customers_v2.csv"]],
    "anomalies": [["customers_v2.csv", "created_at", "invalid_date"],
                  ["customers_v2.csv", "total_spent", "negative_amount"],
                  ["orders.csv", N["cust_fk"], "broken_reference"],
                  ["payments.csv", N["order_pay"], "broken_reference"]],
    "conflicts": conflicts,
}
(HERE / "ground_truth.json").write_text(json.dumps(truth, indent=1))
print(f"variant={VARIANT} seed={SEED} files:", sorted(p.name for p in OUT.glob("*.csv")))
print("true conflicts:", conflicts, "| true entity clusters:", len(clusters))