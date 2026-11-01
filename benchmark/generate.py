import json
import random
from itertools import combinations
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
R = random.Random(42)

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


# ---- customers (v1) and customers_v2 (newer: edits, additions, duplicate people, faults)
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

# ---- suppliers, products, employees
sup_ids = list(range(3001, 3016))
save("suppliers.csv", [{"supplier_id": s, "supplier_name": f"{R.choice(LAST)} Traders",
                        "contact_mail": f"sales{s}@supplier.example.com",
                        "country": R.choice(["India", "UAE", "China", "Germany"])} for s in sup_ids])
prods = [{"product_id": f"P{n:03d}", "product_name": f"Widget {R.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])} {n}",
          "supplier_ref": R.choice(sup_ids), "unit_price": round(R.uniform(5, 500), 2)} for n in range(1, 61)]
save("products.csv", prods)
emp = []
for n in range(40):
    f, l = R.choice(FIRST), R.choice(LAST)
    emp.append({"employee_id": 2001 + n, "name": f"{f} {l}", "email_address": f"{f}.{l}@corp.example.com".lower(),
                "department": R.choice(["Sales", "Ops", "Finance", "HR", "IT"]), "hire_date": day(2015, 2500)})
save("employees.csv", emp)

# ---- orders (renamed FK columns, 12 orphan customer refs)
cust_ids = list(range(1001, 1341))
pids = [p["product_id"] for p in prods]
orders = [{"order_id": 50001 + n, "client_ref": R.choice(cust_ids), "prod_code": R.choice(pids),
           "order_date": day(2023, 500), "quantity": R.randint(1, 9)} for n in range(800)]
for k, i in enumerate(R.sample(range(800), 12)):
    orders[i]["client_ref"] = 9001 + k
save("orders.csv", orders)

# ---- payments (6 orphan order refs), shipping, returns
pay, n = [], 70001
for o in orders:
    if R.random() < 0.9:
        for _ in range(R.choice([1, 1, 1, 2])):
            pay.append({"payment_id": n, "order_ref": o["order_id"], "amount": round(R.uniform(10, 2000), 2),
                        "paid_on": day(2023, 520)})
            n += 1
for k in range(6):
    pay[R.randrange(len(pay))]["order_ref"] = 59001 + k
save("payments.csv", pay)
save("shipping.csv", [{"shipment_id": 80001 + i, "order_no": o["order_id"],
                       "carrier": R.choice(["BlueDart", "DTDC", "Delhivery", "FedEx"]), "shipped_on": day(2023, 520)}
                      for i, o in enumerate(o for o in orders if R.random() < 0.85)])
save("returns.csv", [{"return_id": 90001 + k, "ord_ref": R.choice(orders)["order_id"],
                      "reason": R.choice(["damaged", "wrong item", "late", "changed mind"])} for k in range(60)])

# ---- sales_report (derived aggregate of orders x products)
units = {}
for o in orders:
    units[o["prod_code"]] = units.get(o["prod_code"], 0) + o["quantity"]
price = {p["product_id"]: p["unit_price"] for p in prods}
save("sales_report.csv", [{"sku": k, "units_sold": v, "revenue": round(v * price[k], 2)}
                          for k, v in sorted(units.items())])

# ---- ground truth (the system never sees this)
col = lambda f, c: [f, c]
groups = [
    [col("customers.csv", "customer_id"), col("customers_v2.csv", "customer_id"), col("orders.csv", "client_ref")],
    [col("orders.csv", "order_id"), col("payments.csv", "order_ref"), col("shipping.csv", "order_no"),
     col("returns.csv", "ord_ref")],
    [col("products.csv", "product_id"), col("orders.csv", "prod_code"), col("sales_report.csv", "sku")],
    [col("suppliers.csv", "supplier_id"), col("products.csv", "supplier_ref")],
] + [[col("customers.csv", c), col("customers_v2.csv", c)]
     for c in ["full_name", "email", "phone", "city", "created_at", "total_spent"]]
truth = {
    "versions": {"customers_v2.csv": "customers.csv"},
    "column_groups": groups,
    "fks": [["customers.csv", "customer_id", "orders.csv", "client_ref"],
            ["orders.csv", "order_id", "payments.csv", "order_ref"],
            ["orders.csv", "order_id", "shipping.csv", "order_no"],
            ["orders.csv", "order_id", "returns.csv", "ord_ref"],
            ["products.csv", "product_id", "orders.csv", "prod_code"],
            ["suppliers.csv", "supplier_id", "products.csv", "supplier_ref"]],
    "acceptable_fks": [["sales_report.csv", "sku", "orders.csv", "prod_code"],
                       ["products.csv", "product_id", "sales_report.csv", "sku"],
                       ["sales_report.csv", "sku", "products.csv", "product_id"]],
    "entity_clusters": list(clusters.values()),
    "lineage": [["customers.csv", "customers_v2.csv"]],
    "anomalies": [["customers_v2.csv", "created_at", "invalid_date"],
                  ["customers_v2.csv", "total_spent", "negative_amount"],
                  ["orders.csv", "client_ref", "broken_reference"],
                  ["payments.csv", "order_ref", "broken_reference"]],
    "conflicts": conflicts,
}
(HERE / "ground_truth.json").write_text(json.dumps(truth, indent=1))
print("files:", sorted(p.name for p in OUT.glob("*.csv")))
print("true conflicts:", conflicts, "| true entity clusters:", len(clusters))