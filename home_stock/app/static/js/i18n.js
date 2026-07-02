/* Home Stock - Internationalization (NL/EN) */

const TRANSLATIONS = {
  nl: {
    app_title:      'Voorraad',
    nav_stock:      'Voorraad',
    nav_shopping:   'Boodschappen',
    nav_settings:   'Instellingen',

    // Stock
    stock_title:    'Voorraad',
    total_items:    'Producten',
    low_items:      'Bijna op',
    out_items:      'Op',
    all_categories: 'Alles',
    empty_stock:    'Nog geen producten',
    empty_stock_sub:'Tik op + om producten toe te voegen',
    add_products:   'Producten toevoegen',
    low_badge:      'Bijna op',
    out_badge:      'Op',

    // Shopping
    shopping_title: 'Boodschappen',
    empty_shopping: 'Alles op voorraad! 🎉',
    empty_shopping_sub: 'Er staat niets op de boodschappenlijst',
    send_to_ha:     'Stuur naar HA lijst',
    sync_done:      'items naar Home Assistant gestuurd',
    sync_none_new:  'Alles stond al op de lijst',
    sync_not_connected: 'Geen verbinding met Home Assistant',
    got_it:         'Gekocht',
    need:           'Nog nodig',

    // Catalog / add
    add_title:      'Product toevoegen',
    search:         'Zoeken...',
    custom_item:    'Eigen product',
    custom_add:     'Zelf toevoegen',
    item_name:      'Naam',
    item_emoji:     'Emoji',
    item_category:  'Categorie',
    item_threshold: 'Waarschuw bij (of minder)',
    item_added:     'toegevoegd',
    already_added:  'staat al in je voorraad',

    // Item edit
    edit_title:     'Product bewerken',
    save:           'Opslaan',
    cancel:         'Annuleren',
    delete:         'Verwijderen',
    confirm_delete: 'Dit product verwijderen?',
    saved:          'Opgeslagen!',
    deleted:        'Verwijderd',

    // Settings
    settings_title: 'Instellingen',
    household_name: 'Naam huishouden',
    language:       'Taal',
    ha_integration: 'Home Assistant',
    todo_list:      'Boodschappenlijst (to-do)',
    todo_hint:      'Waar de boodschappenlijst naartoe wordt gestuurd',
    auto_sync:      'Automatisch synchroniseren',
    expose_sensors: 'Sensoren tonen in HA',
    sensors_hint:   'Maakt sensor.home_stock_* aan voor dashboards en automatiseringen',
    no_todo_lists:  'Geen to-do lijsten gevonden in Home Assistant',
    not_connected:  'Niet verbonden met Home Assistant (standalone modus)',
    settings_saved: 'Instellingen opgeslagen!',

    // Generic
    loading:        'Laden...',
    error:          'Er ging iets mis',
    items:          'items',
  },

  en: {
    app_title:      'Home Stock',
    nav_stock:      'Stock',
    nav_shopping:   'Shopping',
    nav_settings:   'Settings',

    stock_title:    'Stock',
    total_items:    'Products',
    low_items:      'Low',
    out_items:      'Out',
    all_categories: 'All',
    empty_stock:    'No products yet',
    empty_stock_sub:'Tap + to add products',
    add_products:   'Add products',
    low_badge:      'Low',
    out_badge:      'Out',

    shopping_title: 'Shopping',
    empty_shopping: 'Fully stocked! 🎉',
    empty_shopping_sub: 'Nothing on the shopping list',
    send_to_ha:     'Send to HA list',
    sync_done:      'items sent to Home Assistant',
    sync_none_new:  'Everything was already on the list',
    sync_not_connected: 'Not connected to Home Assistant',
    got_it:         'Bought',
    need:           'Still needed',

    add_title:      'Add product',
    search:         'Search...',
    custom_item:    'Custom product',
    custom_add:     'Add your own',
    item_name:      'Name',
    item_emoji:     'Emoji',
    item_category:  'Category',
    item_threshold: 'Warn at (or below)',
    item_added:     'added',
    already_added:  'is already in your stock',

    edit_title:     'Edit product',
    save:           'Save',
    cancel:         'Cancel',
    delete:         'Delete',
    confirm_delete: 'Delete this product?',
    saved:          'Saved!',
    deleted:        'Deleted',

    settings_title: 'Settings',
    household_name: 'Household name',
    language:       'Language',
    ha_integration: 'Home Assistant',
    todo_list:      'Shopping list (to-do)',
    todo_hint:      'Where the shopping list is sent',
    auto_sync:      'Auto-sync',
    expose_sensors: 'Show sensors in HA',
    sensors_hint:   'Creates sensor.home_stock_* for dashboards and automations',
    no_todo_lists:  'No to-do lists found in Home Assistant',
    not_connected:  'Not connected to Home Assistant (standalone mode)',
    settings_saved: 'Settings saved!',

    loading:        'Loading...',
    error:          'Something went wrong',
    items:          'items',
  },
};

let currentLang = 'nl';

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('hs_lang', lang);
  applyTranslations();
}

function t(key) {
  return (TRANSLATIONS[currentLang] || TRANSLATIONS.nl)[key] || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

window.t = t;
window.setLang = setLang;
window.TRANSLATIONS = TRANSLATIONS;
window.getCurrentLang = () => currentLang;
