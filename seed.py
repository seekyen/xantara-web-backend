"""
Seeder — inserts Category and SubCategory.
Run AFTER truncating the tables in your DB IDE.

Usage:
    py manage.py shell -c "exec(open('seed.py').read())"
"""

from django.db import transaction
from apps.settings_app.models import Category, SubCategory

CATEGORIES = [
    'Beverages',
    'Snacks',
    'Dairy',
    'Bakery',
    'Meat & Poultry',
    'Seafood',
    'Fruits & Vegetables',
    'Frozen Foods',
    'Canned Goods',
    'Condiments & Sauces',
    'Rice & Grains',
    'Noodles & Pasta',
    'Cooking Oil',
    'Spices & Seasoning',
    'Personal Care',
    'Household Supplies',
    'Baby Products',
    'Tobacco',
    'Liquor',
    'Confectionery',
]

SUBCATEGORIES = [
    # Beverages
    ('Softdrinks',             'Beverages'),
    ('Juice',                  'Beverages'),
    ('Soft Drinks',            'Beverages'),
    ('Water',                  'Beverages'),
    ('Coffee & Tea',           'Beverages'),
    ('Energy Drinks',          'Beverages'),

    # Snacks
    ('Chips & Crisps',         'Snacks'),
    ('Nuts & Seeds',           'Snacks'),
    ('Biscuits & Crackers',    'Snacks'),
    ('Popcorn',                'Snacks'),

    # Dairy
    ('Milk',                   'Dairy'),
    ('Cheese',                 'Dairy'),
    ('Butter & Margarine',     'Dairy'),
    ('Yogurt',                 'Dairy'),
    ('Eggs',                   'Dairy'),

    # Bakery
    ('Bread',                  'Bakery'),
    ('Cakes & Pastries',       'Bakery'),
    ('Rolls & Buns',           'Bakery'),

    # Meat & Poultry
    ('Chicken',                'Meat & Poultry'),
    ('Pork',                   'Meat & Poultry'),
    ('Beef',                   'Meat & Poultry'),
    ('Processed Meat',         'Meat & Poultry'),

    # Seafood
    ('Fish',                   'Seafood'),
    ('Shrimp & Prawns',        'Seafood'),
    ('Squid & Crab',           'Seafood'),
    ('Dried Seafood',          'Seafood'),

    # Fruits & Vegetables
    ('Fresh Fruits',           'Fruits & Vegetables'),
    ('Fresh Vegetables',       'Fruits & Vegetables'),
    ('Root Crops',             'Fruits & Vegetables'),

    # Frozen Foods
    ('Frozen Meat',            'Frozen Foods'),
    ('Frozen Vegetables',      'Frozen Foods'),
    ('Ice Cream',              'Frozen Foods'),
    ('Frozen Meals',           'Frozen Foods'),

    # Canned Goods
    ('Canned Meat',            'Canned Goods'),
    ('Canned Fish',            'Canned Goods'),
    ('Canned Vegetables',      'Canned Goods'),
    ('Canned Fruits',          'Canned Goods'),

    # Condiments & Sauces
    ('Ketchup & Sauces',       'Condiments & Sauces'),
    ('Vinegar & Soy Sauce',    'Condiments & Sauces'),
    ('Mayonnaise',             'Condiments & Sauces'),
    ('Hot Sauce',              'Condiments & Sauces'),

    # Rice & Grains
    ('White Rice',             'Rice & Grains'),
    ('Brown Rice',             'Rice & Grains'),
    ('Oats & Cereals',         'Rice & Grains'),

    # Noodles & Pasta
    ('Instant Noodles',        'Noodles & Pasta'),
    ('Pasta',                  'Noodles & Pasta'),
    ('Vermicelli',             'Noodles & Pasta'),

    # Cooking Oil
    ('Vegetable Oil',          'Cooking Oil'),
    ('Olive Oil',              'Cooking Oil'),
    ('Coconut Oil',            'Cooking Oil'),

    # Spices & Seasoning
    ('Salt & Pepper',          'Spices & Seasoning'),
    ('Garlic & Onion',         'Spices & Seasoning'),
    ('Herbs & Spices',         'Spices & Seasoning'),
    ('Bouillon & Broth',       'Spices & Seasoning'),

    # Personal Care
    ('Soap & Body Wash',       'Personal Care'),
    ('Shampoo & Conditioner',  'Personal Care'),
    ('Toothpaste & Oral Care', 'Personal Care'),
    ('Deodorant',              'Personal Care'),

    # Household Supplies
    ('Detergent',              'Household Supplies'),
    ('Dishwashing',            'Household Supplies'),
    ('Cleaning Supplies',      'Household Supplies'),
    ('Trash Bags & Wraps',     'Household Supplies'),

    # Baby Products
    ('Baby Food',              'Baby Products'),
    ('Diapers',                'Baby Products'),
    ('Baby Care',              'Baby Products'),

    # Tobacco
    ('Cigarettes',             'Tobacco'),
    ('Vape & E-Cigs',          'Tobacco'),

    # Liquor
    ('Beer',                   'Liquor'),
    ('Wine',                   'Liquor'),
    ('Spirits',                'Liquor'),
    ('Cocktail Mixes',         'Liquor'),

    # Confectionery
    ('Chocolates',             'Confectionery'),
    ('Candies & Gummies',      'Confectionery'),
    ('Jellies & Marshmallows', 'Confectionery'),
    ('Chewing Gum',            'Confectionery'),
]

with transaction.atomic():

    print("Inserting categories...")
    cat_map = {}
    for name in CATEGORIES:
        cat = Category.objects.create(name=name, is_active=True)
        cat_map[name] = cat.code
        print(f"  {cat.code} — {name}")
    print(f"Done. {len(CATEGORIES)} categories inserted.\n")

    print("Inserting subcategories...")
    for sub_name, cat_name in SUBCATEGORIES:
        sub = SubCategory.objects.create(
            name=sub_name,
            category_code=cat_map[cat_name],
            is_active=True,
        )
        print(f"  {sub.code} — {sub_name} → {cat_map[cat_name]}")
    print(f"Done. {len(SUBCATEGORIES)} subcategories inserted.\n")

print("All done — transaction committed.")