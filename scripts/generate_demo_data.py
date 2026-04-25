"""
Generate 66,000 realistic synthetic products across 5 sources.
Output: data/demo/demo_products.jsonl
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ── Output ─────────────────────────────────────────────────────────────────────
OUT = Path(__file__).parent.parent / "data" / "demo"
OUT.mkdir(parents=True, exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def rand_date(days_back=60):
    base = datetime.utcnow() - timedelta(days=days_back)
    return (base + timedelta(
        days=random.uniform(0, days_back),
        hours=random.uniform(0, 24),
        minutes=random.uniform(0, 60),
    )).strftime("%Y-%m-%dT%H:%M:%SZ")

def jitter(val, pct=0.12):
    return round(val * random.uniform(1 - pct, 1 + pct), 2)

def rating():
    # Slightly biased toward good ratings (3.5–5)
    return round(random.choices(
        [round(random.uniform(1.0, 3.4), 1),
         round(random.uniform(3.5, 4.4), 1),
         round(random.uniform(4.5, 5.0), 1)],
        weights=[0.15, 0.50, 0.35]
    )[0], 1)

AVAILABILITY = ["In stock", "In stock", "In stock", "In stock",
                "1 available", "2 available", "3 available",
                "Out of stock", "Pre-order"]

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — books.toscrape.com  (20 000 books)
# ══════════════════════════════════════════════════════════════════════════════
BOOK_CATEGORIES = [
    "Mystery", "Historical Fiction", "Sequential Art", "Classics",
    "Philosophy", "Romance", "Womens Fiction", "Fiction", "Childrens",
    "Travel", "Mystery", "Nonfiction", "Music", "Default",
    "Science Fiction", "Sports and Games", "Add a comment", "Fantasy",
    "New Adult", "Young Adult", "Science", "Poetry", "Paranormal",
    "Art", "Psychology", "Adult Fiction", "Humor", "Horror",
    "History", "Food and Drink", "Christian Fiction", "Business",
    "Biography", "Thriller", "Contemporary", "Spirituality",
    "Academic", "Self Help", "Historical", "Christian",
    "Suspense", "Short Stories", "Novels", "Health",
    "Politics", "Cultural", "Erotica", "Crime",
]

BOOK_ADJECTIVES = [
    "The Lost", "A Brief", "Silent", "Broken", "Dark", "Golden",
    "The Last", "Hidden", "Forgotten", "Rising", "Fallen", "Wild",
    "Beautiful", "Eternal", "Burning", "Infinite", "The Great",
    "Perfect", "Secret", "Shattered", "The Art of", "Beyond",
    "Between", "After", "Before", "Little", "Big", "Strange",
]

BOOK_NOUNS = [
    "World", "Journey", "Stars", "Fire", "Light", "Shadow", "Heart",
    "Mind", "Soul", "Dream", "Night", "Day", "Voice", "Story",
    "History", "Time", "Truth", "Promise", "Path", "Way",
    "Kingdom", "Empire", "Land", "Sea", "Sky", "River", "Mountain",
    "Memory", "Future", "Past", "Love", "War", "Peace", "Hope",
]

def book_title():
    return f"{random.choice(BOOK_ADJECTIVES)} {random.choice(BOOK_NOUNS)}"

books = []
for i in range(20_000):
    cat = random.choice(BOOK_CATEGORIES)
    price = round(random.triangular(1.0, 59.99, 14.0), 2)
    books.append({
        "product_id":   f"bk_{i:06d}",
        "title":        book_title(),
        "price":        price,
        "currency":     "GBP",
        "source":       "books_toscrape",
        "category":     cat,
        "availability": random.choices(AVAILABILITY, weights=[6,4,3,2,2,1,1,1,0.5])[0],
        "rating":       rating(),
        "scraped_at":   rand_date(60),
    })

print(f"  books_toscrape: {len(books):,}")

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — scrapeme.live  (11 000 grocery / food)
# ══════════════════════════════════════════════════════════════════════════════
GROCERY_CATS = [
    "Fruits & Vegetables", "Dairy & Eggs", "Bakery", "Meat & Seafood",
    "Frozen Food", "Beverages", "Snacks & Sweets", "Breakfast Cereal",
    "Condiments & Sauces", "Pasta & Rice", "Canned Goods", "Baby Food",
    "Health & Organic", "International Foods", "Pet Food",
]

GROCERY_PREFIXES = [
    "Organic", "Fresh", "Premium", "Farm", "Natural", "Classic",
    "Traditional", "Home-style", "Bio", "Local", "Select",
]

GROCERY_ITEMS = [
    "Apples", "Milk", "Cheese", "Bread", "Chicken Breast", "Pasta",
    "Rice", "Yogurt", "Butter", "Eggs", "Orange Juice", "Cereal",
    "Soup", "Tomatoes", "Potatoes", "Salmon", "Tuna Can",
    "Olive Oil", "Coffee", "Tea", "Sparkling Water", "Cookies",
    "Chocolate", "Jam", "Honey", "Peanut Butter", "Granola",
    "Oats", "Flour", "Sugar", "Salt", "Pepper", "Sauce",
    "Muesli", "Crackers", "Chips", "Frozen Pizza", "Ice Cream",
]

grocery = []
for i in range(11_000):
    cat = random.choice(GROCERY_CATS)
    price = round(random.triangular(0.49, 49.99, 4.5), 2)
    grocery.append({
        "product_id":   f"sc_{i:06d}",
        "title":        f"{random.choice(GROCERY_PREFIXES)} {random.choice(GROCERY_ITEMS)}",
        "price":        price,
        "currency":     "GBP",
        "source":       "scrapeme_live",
        "category":     cat,
        "availability": random.choices(AVAILABILITY, weights=[8,4,3,2,2,1,1,0.5,0.3])[0],
        "rating":       rating(),
        "scraped_at":   rand_date(30),
    })

print(f"  scrapeme_live:  {len(grocery):,}")

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — jumia.ma  (20 000 — fashion, electronics, home)
# ══════════════════════════════════════════════════════════════════════════════
JUMIA_CATS = [
    "Smartphones", "Laptops & Computers", "TVs & Monitors",
    "Fashion - Men", "Fashion - Women", "Fashion - Kids",
    "Home & Kitchen", "Beauty & Health", "Sports & Outdoors",
    "Toys & Games", "Automotive", "Books & Stationery",
    "Cameras & Photography", "Tablets & E-readers",
    "Audio & Headphones", "Smart Watches", "Appliances",
    "Baby & Toddler", "Garden & Outdoor", "Office Supplies",
]

JUMIA_BRANDS = [
    "Samsung", "Huawei", "Xiaomi", "Tecno", "Infinix", "Itel",
    "LG", "Hisense", "TCL", "Philips", "Bosch", "Ariston",
    "Nike", "Adidas", "Puma", "Reebok", "New Balance",
    "Apple", "Lenovo", "HP", "Dell", "Acer", "Asus",
    "Sony", "JBL", "Anker", "Baseus", "Oraimo",
]

JUMIA_PRODUCTS = [
    "Smartphone Pro", "Laptop Ultra", "Smart TV", "Headphones",
    "Running Shoes", "T-Shirt", "Dress", "Jeans", "Jacket",
    "Blender", "Rice Cooker", "Air Fryer", "Electric Kettle",
    "Watch", "Tablet", "Power Bank", "Earbuds", "Camera",
    "Gaming Mouse", "Mechanical Keyboard", "Monitor", "Printer",
    "Backpack", "Wallet", "Sunglasses", "Perfume", "Face Cream",
]

jumia = []
for i in range(20_000):
    cat   = random.choice(JUMIA_CATS)
    brand = random.choice(JUMIA_BRANDS)
    prod  = random.choice(JUMIA_PRODUCTS)
    # Price in MAD — varies a lot by category
    if "Smartphone" in cat or "Laptop" in cat:
        price = round(random.triangular(1_500, 25_000, 4_500), 2)
    elif "Fashion" in cat:
        price = round(random.triangular(50, 2_500, 350), 2)
    elif "Appliance" in cat or "TV" in cat:
        price = round(random.triangular(500, 15_000, 2_500), 2)
    else:
        price = round(random.triangular(30, 8_000, 500), 2)
    jumia.append({
        "product_id":   f"jm_{i:06d}",
        "title":        f"{brand} {prod} {random.randint(2019,2025)}",
        "price":        price,
        "currency":     "MAD",
        "source":       "jumia_ma",
        "category":     cat,
        "availability": random.choices(AVAILABILITY, weights=[7,4,3,2,2,1,1,1,0.5])[0],
        "rating":       rating(),
        "scraped_at":   rand_date(45),
    })

print(f"  jumia_ma:       {len(jumia):,}")

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 4 — ultrapc.ma  (8 000 — PC hardware & peripherals)
# ══════════════════════════════════════════════════════════════════════════════
PC_CATS = [
    "Processors (CPU)", "Graphics Cards (GPU)", "Motherboards",
    "RAM Memory", "SSDs & HDDs", "PC Cases", "Power Supplies",
    "Cooling Systems", "Monitors", "Keyboards", "Mice",
    "Headsets", "Webcams", "Networking", "Cables & Adapters",
    "Gaming Chairs", "Laptops", "Gaming PCs",
]

CPU_MODELS = ["Core i3", "Core i5", "Core i7", "Core i9",
              "Ryzen 3", "Ryzen 5", "Ryzen 7", "Ryzen 9"]
GPU_MODELS = ["RTX 3060", "RTX 3070", "RTX 3080", "RTX 4060", "RTX 4070",
              "RX 6600", "RX 6700", "RX 7600", "Arc A750"]
PC_BRANDS  = ["Intel", "AMD", "ASUS", "MSI", "Gigabyte", "Corsair",
              "Kingston", "Samsung", "Western Digital", "Seagate",
              "Logitech", "Razer", "SteelSeries", "HyperX", "NZXT",
              "be quiet!", "Cooler Master", "Thermaltake", "Fractal"]

def pc_title(cat):
    if "CPU" in cat:
        return f"Processeur {random.choice(CPU_MODELS)} {random.randint(10,14)}th Gen"
    if "GPU" in cat:
        return f"Carte Graphique {random.choice(GPU_MODELS)} {random.randint(8,24)}Go"
    if "RAM" in cat:
        return f"{random.choice(['Corsair','Kingston','G.Skill','HyperX'])} DDR{random.choice([4,5])} {random.choice([8,16,32,64])}Go {random.randint(3200,6400)}MHz"
    if "SSD" in cat:
        return f"{random.choice(['Samsung','WD','Crucial','Kingston'])} SSD {random.choice([256,512,1000,2000])}Go NVMe"
    return f"{random.choice(PC_BRANDS)} {cat.split('(')[0].strip()} {random.randint(100,999)}"

ultrapc = []
for i in range(8_000):
    cat = random.choice(PC_CATS)
    if "GPU" in cat:
        price = round(random.triangular(2_500, 18_000, 5_000), 2)
    elif "CPU" in cat:
        price = round(random.triangular(800, 12_000, 2_000), 2)
    elif "Laptop" in cat or "Gaming PC" in cat:
        price = round(random.triangular(4_000, 30_000, 9_000), 2)
    elif "Monitor" in cat:
        price = round(random.triangular(900, 8_000, 2_200), 2)
    else:
        price = round(random.triangular(80, 3_000, 450), 2)
    ultrapc.append({
        "product_id":   f"up_{i:06d}",
        "title":        pc_title(cat),
        "price":        price,
        "currency":     "MAD",
        "source":       "ultrapc_ma",
        "category":     cat,
        "availability": random.choices(AVAILABILITY, weights=[6,4,3,2,2,1,1,1,0.5])[0],
        "rating":       rating(),
        "scraped_at":   rand_date(30),
    })

print(f"  ultrapc_ma:     {len(ultrapc):,}")

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 5 — micromagma.ma  (7 000 — smartphones, tablets, accessories)
# ══════════════════════════════════════════════════════════════════════════════
MM_CATS = [
    "Smartphones", "Tablettes", "Accessoires Téléphone", "Chargeurs",
    "Coques & Protection", "Écouteurs & Casques", "Smartwatches",
    "Batteries Externes", "Câbles", "Caméras de Surveillance",
    "Routeurs & Réseaux", "Clés USB & Stockage",
]

MM_BRANDS = ["Apple", "Samsung", "Xiaomi", "Oppo", "Vivo", "OnePlus",
             "Realme", "Huawei", "Honor", "Motorola", "Nokia", "Sony",
             "Tecno", "Infinix", "Anker", "Baseus", "Ugreen"]

MM_PHONE_MODELS = [
    "iPhone 14", "iPhone 15", "iPhone 15 Pro", "Galaxy S23", "Galaxy A54",
    "Galaxy A34", "Redmi Note 12", "Redmi Note 13", "POCO X5",
    "Reno 10", "V25", "12R", "C55", "Nova 11", "90 Lite",
    "Moto G73", "G32", "Xperia 10 V",
]

def mm_title(cat):
    if "Smartphone" in cat:
        return f"{random.choice(MM_BRANDS)} {random.choice(MM_PHONE_MODELS)}"
    if "Tablette" in cat:
        return f"{random.choice(['Samsung','Apple','Xiaomi','Lenovo'])} Tab {random.choice(['S7','S8','S9','A8','A9','P11','M10'])} {random.choice(['64Go','128Go','256Go'])}"
    if "Écouteur" in cat or "Casque" in cat:
        return f"{random.choice(['JBL','Sony','Samsung','Apple','Anker','QCY'])} {random.choice(['AirPods','Buds2','WH-1000','Tune','SoundCore'])} Pro"
    if "Chargeur" in cat:
        return f"Chargeur Rapide {random.choice([20,25,33,45,65,120])}W USB-C {random.choice(MM_BRANDS)}"
    if "Batterie" in cat:
        return f"{random.choice(['Anker','Baseus','Xiaomi','Ugreen'])} Power Bank {random.choice([10000,20000,25000,30000])}mAh"
    return f"{random.choice(MM_BRANDS)} {cat} {random.randint(100,999)}"

micromagma = []
for i in range(7_000):
    cat = random.choice(MM_CATS)
    if "Smartphone" in cat:
        price = round(random.triangular(1_200, 18_000, 3_500), 2)
    elif "Tablette" in cat:
        price = round(random.triangular(1_000, 10_000, 2_500), 2)
    elif "Écouteur" in cat:
        price = round(random.triangular(100, 3_500, 600), 2)
    else:
        price = round(random.triangular(30, 2_000, 250), 2)
    micromagma.append({
        "product_id":   f"mm_{i:06d}",
        "title":        mm_title(cat),
        "price":        price,
        "currency":     "MAD",
        "source":       "micromagma_ma",
        "category":     cat,
        "availability": random.choices(AVAILABILITY, weights=[6,4,3,2,2,1,1,0.5,0.3])[0],
        "rating":       rating(),
        "scraped_at":   rand_date(30),
    })

print(f"  micromagma_ma:  {len(micromagma):,}")

# ══════════════════════════════════════════════════════════════════════════════
# Write JSONL
# ══════════════════════════════════════════════════════════════════════════════
all_products = books + grocery + jumia + ultrapc + micromagma
random.shuffle(all_products)

out_file = OUT / "demo_products.jsonl"
with open(out_file, "w", encoding="utf-8") as f:
    for p in all_products:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

total = len(all_products)
print(f"\n✓  {total:,} products written to {out_file}")
print(f"   File size: {out_file.stat().st_size / 1_048_576:.1f} MB")
