# all necessary imports
import re
import requests
import json
from rapidfuzz import fuzz
import random
from collections import defaultdict


# helper function to normalize product names for better matching
def normalize_name(name):
    name = name.lower() # convert to lowercase
    name = name.replace(",", ".") # unify decimal separator
    name = re.sub(r"[^a-z0-9. ]", "", name) # remove special characters except dots and spaces
    name = re.sub(r"\s+", " ", name) # replace multiple spaces with a single space

    return name.strip()
    # return normalized name without spaces
    # before or after for better matching

# helper fucntion to extract size information
# to group products more accurately based on size
def extract_size(name):
    pattern = r"(\d+(?:\.\d+)?)\s*(ml|l|lt|g|kg)"
    match = re.search(pattern, name)

    if match:
        amount = float(match.group(1))
        unit = match.group(2)

        if unit in ["l", "lt", "L", "LT", "Lt",
                    "kg", "KG", "Kg",
                    ]:
            amount *= 1000

        return int(amount)

    return None


# url to fetch the data from
url = "https://warply.s3.amazonaws.com/applications/ed840ad545884deeb6c6b699176797ed/basket-retailers/prices.json?cid=1773057600000"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
data = response.json()


# searching inside the data to find all of the information we need
# through result
result = data["context"]["MAPP_PRODUCTS"]["result"]

# initial data extraction
# all_merchants contains all supermarket names and details
all_merchants = result["merchants"]

# all_categories contains all categories and details
all_categories = result["categories"]

# all_suppliers contains all supplier names and details
all_suppliers = result["suppliers"]

# all_products contains all products and details
all_products = result["products"]
print(all_products[0])

# # base_url contains the base url for product images
# base_url = result["img_base_url"]


# creating a smaller dataset with 150 products and 50 suppliers
products = random.sample(all_products, 150)
suppliers = random.sample(all_suppliers, 50)

# temporary dataset to store the lesser data
# with the product name, supermarket name, price and category
merchants = {m["merchant_uuid"]: m["name"] for m in all_merchants}
categories = {c["uuid"]: c["name"] for c in all_categories}

dataset = []
for p in products:
    for price in p.get("prices", []):
        dataset.append({
            "product": p["name"],
            "supermarket": merchants.get(price["merchant_uuid"], "Unknown"),
            "price": price["price"],
            "category": p["category"]
        })

# saving the new temporary dataset
with open("dataset_clean.json", "w") as f:
    json.dump(dataset, f, indent=2)

# checking the length of the dataset to see how many entries we have
print("Dataset created:", len(dataset), "entries")


productsClean = defaultdict(list)

for item in dataset:
    productsClean[item["product"]].append({
        "supermarket": item["supermarket"],
        "price": item["price"]
    })

databaseClean = []

for name, prices in productsClean.items():
    databaseClean.append({
        "product": name,
        "prices": prices
    })

with open("products_grouped.json", "w") as f:
    json.dump(databaseClean, f, indent=2)


# grouping similar products together using fuzzy matching
groups = [[databaseClean[0]["product"]]]

for product in databaseClean:
    placed = False
    
    for group in groups:
        if fuzz.token_sort_ratio(product["product"], group[0]) > 85:
            group.append(product["product"])
            placed = True
            break

    if not placed:
        groups.append([product["product"]])

print(groups)