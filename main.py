# all necessary imports
import re
import requests
import json
from rapidfuzz import fuzz
import random
from collections import defaultdict
import unicodedata


# helper function to remove accents from characters
# used when normalizing product names
def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

# helper function to normalize product names for better matching
def normalize_name(name):
    # convert to lowercase, unify decimal separator and remove accents
    name = remove_accents(name.lower().replace(",", "."))

    # remove special characters except dots and spaces
    name = re.sub(r"[^\w. ]", "", name, flags=re.UNICODE)
    
    # remove extra spaces
    name = re.sub(r"\s+", " ", name).strip()

    # check if the name is of a certain pattern
    pattern = r"(\d+(?:\.\d+)?)\s*(ml|l|lt|g|kg)"
    match = re.search(pattern, name)

    if match:
        name = name[:match.end()]

    # return normalized name without spaces
    # before or after for better matching
    return name.strip()

# helper fucntion to extract size information
# to group products more accurately based on size
def extract_size(name):
    # convert to lowercase and unify decimal separator
    name = name.lower().replace(",", ".")

    # check if the name is of a certain pattern
    pattern = r"(\d+(?:\.\d+)?)\s*(ml|l|lt|g|kg)"
    match = re.search(pattern, name)

    if match:
        # amount is the size of the product in ml or g
        amount = float(match.group(1))
        unit = match.group(2)

        if unit in ["l", "lt", "kg"]:
            amount *= 1000

        return int(amount)

    return None

# helper function to check if 2 products are the same
# based on product size and name similarity using fuzzy matching
def same_product(a, b):
    if extract_size(a) != extract_size(b):
        return False

    return fuzz.token_set_ratio(normalize_name(a), normalize_name(b)) > 80

# helper function to help the AI find the correct product
# based on user search
def find_product_group(search):
    # extract size from the search term
    searchSize = extract_size(search)
    # normalize the search term
    search = normalize_name(search)

    # loop where we find the best matching product
    maxScore = 0
    bestGroup = None

    for groupId, name in groupName.items():
        # if product size is different from the search term size, continue
        if extract_size(name) != searchSize:
            continue

        # calculating similarity using fuzzy matching
        score = fuzz.token_set_ratio(search, normalize_name(name))

        # finding max score
        if score > maxScore:
            maxScore = score
            bestGroup = groupId

    # return the best matching product
    # if the similarity score is above a certain threshold
    if maxScore > 70:
        return bestGroup

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
allMerchants = result["merchants"]

# all_categories contains all categories and details
allCategories = result["categories"]

# all_suppliers contains all supplier names and details
allSuppliers = result["suppliers"]

# all_products contains all products and details
allProducts = result["products"]
print(allProducts[0])


# creating a smaller dataset with 150 products and 50 suppliers
productNames = list(set(p["name"] for p in allProducts))
productsSelected = random.sample(productNames, 150)
products = [p for p in allProducts if p["name"] in productsSelected]

supplierIds = set(p["supplier"] for p in products)
suppliers = [s for s in allSuppliers if s["id"] in supplierIds]

# temporary dataset to store the lesser data
# with the product name, supermarket name, price and category
merchants = {m["merchant_uuid"]: m["name"] for m in allMerchants}
categories = {c["uuid"]: c["name"] for c in allCategories}

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

for product in databaseClean[1:]:
    placed = False

    for group in groups:
        if same_product(product["product"], group[0]):
            group.append(product["product"])
            placed = True
            break

    if not placed:
        groups.append([product["product"]])

# giving an id to each group for easier reference
referenceIds = {}

for i, group in enumerate(groups):
    for name in group:
        referenceIds[name] = i

# creating a group id for each group
for item in databaseClean:
    item["group_id"] = referenceIds[item["product"]]

# adding the group id to each group
groupedProducts = defaultdict(list)

for item in databaseClean:
    groupedProducts[item["group_id"]].append(item)

print(groupedProducts[0])

# renaming each group with the name of the first product in that group
groupName = {}

for i, group in enumerate(groups):
    groupName[i] = group[0]

# creating a new dataset with the group id for each product
with open("products_grouped_final.json", "w") as f:
    json.dump(groupedProducts, f, indent=2)