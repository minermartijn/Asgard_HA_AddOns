/* Home Stock - preset catalog of common household supplies.
   Each category has an id + emoji + nl/en label.
   Each product has nl/en names, an emoji, its category id, and a default low threshold. */

const CATEGORIES = [
  { id: 'dairy',      emoji: '🧀', nl: 'Zuivel',        en: 'Dairy' },
  { id: 'produce',    emoji: '🥦', nl: 'Groente & fruit', en: 'Produce' },
  { id: 'meat_fish',  emoji: '🍗', nl: 'Vlees & vis',   en: 'Meat & fish' },
  { id: 'bakery',     emoji: '🍞', nl: 'Brood & bakkerij', en: 'Bakery' },
  { id: 'pantry',     emoji: '🥫', nl: 'Voorraadkast',  en: 'Pantry' },
  { id: 'frozen',     emoji: '🧊', nl: 'Diepvries',     en: 'Frozen' },
  { id: 'drinks',     emoji: '🥤', nl: 'Dranken',       en: 'Drinks' },
  { id: 'snacks',     emoji: '🍫', nl: 'Snacks',        en: 'Snacks' },
  { id: 'breakfast',  emoji: '🥣', nl: 'Ontbijt',       en: 'Breakfast' },
  { id: 'cleaning',   emoji: '🧽', nl: 'Schoonmaak',    en: 'Cleaning' },
  { id: 'toiletries', emoji: '🧴', nl: 'Verzorging',    en: 'Toiletries' },
  { id: 'paper',      emoji: '🧻', nl: 'Papierwaren',   en: 'Paper goods' },
  { id: 'baby',       emoji: '🍼', nl: 'Baby',          en: 'Baby' },
  { id: 'pet',        emoji: '🐾', nl: 'Huisdier',      en: 'Pet' },
  { id: 'household',  emoji: '🔋', nl: 'Huishouden',    en: 'Household' },
  { id: 'other',      emoji: '📦', nl: 'Overig',        en: 'Other' },
];

const CATALOG = [
  // Dairy
  { nl: 'Melk', en: 'Milk', emoji: '🥛', cat: 'dairy', th: 1 },
  { nl: 'Kaas', en: 'Cheese', emoji: '🧀', cat: 'dairy', th: 1 },
  { nl: 'Eieren', en: 'Eggs', emoji: '🥚', cat: 'dairy', th: 1 },
  { nl: 'Boter', en: 'Butter', emoji: '🧈', cat: 'dairy', th: 1 },
  { nl: 'Yoghurt', en: 'Yoghurt', emoji: '🥛', cat: 'dairy', th: 1 },
  { nl: 'Room', en: 'Cream', emoji: '🥛', cat: 'dairy', th: 0 },
  // Produce
  { nl: 'Appels', en: 'Apples', emoji: '🍎', cat: 'produce', th: 2 },
  { nl: 'Bananen', en: 'Bananas', emoji: '🍌', cat: 'produce', th: 2 },
  { nl: 'Tomaten', en: 'Tomatoes', emoji: '🍅', cat: 'produce', th: 1 },
  { nl: 'Uien', en: 'Onions', emoji: '🧅', cat: 'produce', th: 1 },
  { nl: 'Aardappels', en: 'Potatoes', emoji: '🥔', cat: 'produce', th: 1 },
  { nl: 'Sla', en: 'Lettuce', emoji: '🥬', cat: 'produce', th: 0 },
  { nl: 'Wortels', en: 'Carrots', emoji: '🥕', cat: 'produce', th: 1 },
  { nl: 'Paprika', en: 'Bell pepper', emoji: '🫑', cat: 'produce', th: 1 },
  { nl: 'Citroen', en: 'Lemon', emoji: '🍋', cat: 'produce', th: 0 },
  // Meat & fish
  { nl: 'Kipfilet', en: 'Chicken', emoji: '🍗', cat: 'meat_fish', th: 1 },
  { nl: 'Gehakt', en: 'Minced meat', emoji: '🥩', cat: 'meat_fish', th: 0 },
  { nl: 'Vis', en: 'Fish', emoji: '🐟', cat: 'meat_fish', th: 0 },
  { nl: 'Vleeswaren', en: 'Cold cuts', emoji: '🥓', cat: 'meat_fish', th: 1 },
  // Bakery
  { nl: 'Brood', en: 'Bread', emoji: '🍞', cat: 'bakery', th: 1 },
  { nl: 'Broodjes', en: 'Rolls', emoji: '🥖', cat: 'bakery', th: 0 },
  { nl: 'Beschuit', en: 'Rusk', emoji: '🍘', cat: 'bakery', th: 1 },
  { nl: 'Crackers', en: 'Crackers', emoji: '🍘', cat: 'bakery', th: 1 },
  // Pantry
  { nl: 'Pasta', en: 'Pasta', emoji: '🍝', cat: 'pantry', th: 1 },
  { nl: 'Rijst', en: 'Rice', emoji: '🍚', cat: 'pantry', th: 1 },
  { nl: 'Bloem', en: 'Flour', emoji: '🌾', cat: 'pantry', th: 1 },
  { nl: 'Suiker', en: 'Sugar', emoji: '🍬', cat: 'pantry', th: 1 },
  { nl: 'Zout', en: 'Salt', emoji: '🧂', cat: 'pantry', th: 1 },
  { nl: 'Olie', en: 'Oil', emoji: '🫒', cat: 'pantry', th: 1 },
  { nl: 'Tomatensaus', en: 'Tomato sauce', emoji: '🥫', cat: 'pantry', th: 2 },
  { nl: 'Bonen (blik)', en: 'Beans (can)', emoji: '🥫', cat: 'pantry', th: 2 },
  { nl: 'Soep', en: 'Soup', emoji: '🥫', cat: 'pantry', th: 1 },
  { nl: 'Koffie', en: 'Coffee', emoji: '☕', cat: 'pantry', th: 1 },
  { nl: 'Thee', en: 'Tea', emoji: '🍵', cat: 'pantry', th: 1 },
  // Frozen
  { nl: 'Diepvriesgroente', en: 'Frozen veg', emoji: '🥦', cat: 'frozen', th: 1 },
  { nl: 'Pizza', en: 'Pizza', emoji: '🍕', cat: 'frozen', th: 1 },
  { nl: 'IJs', en: 'Ice cream', emoji: '🍦', cat: 'frozen', th: 0 },
  { nl: 'Frikandel/snacks', en: 'Frozen snacks', emoji: '🍟', cat: 'frozen', th: 1 },
  // Drinks
  { nl: 'Water', en: 'Water', emoji: '💧', cat: 'drinks', th: 2 },
  { nl: 'Frisdrank', en: 'Soda', emoji: '🥤', cat: 'drinks', th: 1 },
  { nl: 'Sap', en: 'Juice', emoji: '🧃', cat: 'drinks', th: 1 },
  { nl: 'Bier', en: 'Beer', emoji: '🍺', cat: 'drinks', th: 1 },
  { nl: 'Wijn', en: 'Wine', emoji: '🍷', cat: 'drinks', th: 0 },
  // Snacks
  { nl: 'Chips', en: 'Crisps', emoji: '🍟', cat: 'snacks', th: 1 },
  { nl: 'Koekjes', en: 'Cookies', emoji: '🍪', cat: 'snacks', th: 1 },
  { nl: 'Chocolade', en: 'Chocolate', emoji: '🍫', cat: 'snacks', th: 1 },
  { nl: 'Noten', en: 'Nuts', emoji: '🥜', cat: 'snacks', th: 1 },
  // Breakfast
  { nl: 'Cornflakes', en: 'Cereal', emoji: '🥣', cat: 'breakfast', th: 1 },
  { nl: 'Havermout', en: 'Oats', emoji: '🌾', cat: 'breakfast', th: 1 },
  { nl: 'Jam', en: 'Jam', emoji: '🍓', cat: 'breakfast', th: 1 },
  { nl: 'Hagelslag', en: 'Sprinkles', emoji: '🍫', cat: 'breakfast', th: 1 },
  { nl: 'Pindakaas', en: 'Peanut butter', emoji: '🥜', cat: 'breakfast', th: 1 },
  // Cleaning
  { nl: 'Afwasmiddel', en: 'Dish soap', emoji: '🧴', cat: 'cleaning', th: 1 },
  { nl: 'Vaatwastabletten', en: 'Dishwasher tabs', emoji: '🧼', cat: 'cleaning', th: 1 },
  { nl: 'Allesreiniger', en: 'All-purpose cleaner', emoji: '🧽', cat: 'cleaning', th: 1 },
  { nl: 'Wasmiddel', en: 'Laundry detergent', emoji: '🧺', cat: 'cleaning', th: 1 },
  { nl: 'Wasverzachter', en: 'Fabric softener', emoji: '🧴', cat: 'cleaning', th: 1 },
  { nl: 'Vuilniszakken', en: 'Bin bags', emoji: '🗑️', cat: 'cleaning', th: 1 },
  { nl: 'Sponsjes', en: 'Sponges', emoji: '🧽', cat: 'cleaning', th: 1 },
  { nl: 'Toiletreiniger', en: 'Toilet cleaner', emoji: '🚽', cat: 'cleaning', th: 1 },
  // Toiletries
  { nl: 'Tandpasta', en: 'Toothpaste', emoji: '🪥', cat: 'toiletries', th: 1 },
  { nl: 'Shampoo', en: 'Shampoo', emoji: '🧴', cat: 'toiletries', th: 1 },
  { nl: 'Douchegel', en: 'Shower gel', emoji: '🧴', cat: 'toiletries', th: 1 },
  { nl: 'Zeep', en: 'Soap', emoji: '🧼', cat: 'toiletries', th: 1 },
  { nl: 'Deodorant', en: 'Deodorant', emoji: '🧴', cat: 'toiletries', th: 1 },
  { nl: 'Scheermesjes', en: 'Razors', emoji: '🪒', cat: 'toiletries', th: 1 },
  // Paper goods
  { nl: 'Toiletpapier', en: 'Toilet paper', emoji: '🧻', cat: 'paper', th: 2 },
  { nl: 'Keukenrol', en: 'Kitchen roll', emoji: '🧻', cat: 'paper', th: 1 },
  { nl: 'Tissues', en: 'Tissues', emoji: '🤧', cat: 'paper', th: 1 },
  { nl: 'Servetten', en: 'Napkins', emoji: '🧻', cat: 'paper', th: 1 },
  // Baby
  { nl: 'Luiers', en: 'Diapers', emoji: '🧷', cat: 'baby', th: 1 },
  { nl: 'Billendoekjes', en: 'Wet wipes', emoji: '🧻', cat: 'baby', th: 1 },
  { nl: 'Flesvoeding', en: 'Formula', emoji: '🍼', cat: 'baby', th: 1 },
  // Pet
  { nl: 'Kattenvoer', en: 'Cat food', emoji: '🐱', cat: 'pet', th: 1 },
  { nl: 'Hondenvoer', en: 'Dog food', emoji: '🐶', cat: 'pet', th: 1 },
  { nl: 'Kattenbakvulling', en: 'Cat litter', emoji: '🐾', cat: 'pet', th: 1 },
  // Household
  { nl: 'Batterijen', en: 'Batteries', emoji: '🔋', cat: 'household', th: 1 },
  { nl: 'Lampen', en: 'Light bulbs', emoji: '💡', cat: 'household', th: 1 },
  { nl: 'Aanstekers', en: 'Lighters', emoji: '🔥', cat: 'household', th: 0 },
  { nl: 'Aluminiumfolie', en: 'Foil', emoji: '🧻', cat: 'household', th: 1 },
];

window.CATEGORIES = CATEGORIES;
window.CATALOG = CATALOG;
window.categoryMeta = (id) => CATEGORIES.find(c => c.id === id) || CATEGORIES[CATEGORIES.length - 1];
