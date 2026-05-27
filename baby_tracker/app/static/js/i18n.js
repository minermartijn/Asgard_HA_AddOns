/* Baby Tracker - Internationalization (NL/EN) */

const TRANSLATIONS = {
  nl: {
    // Navigation
    nav_home:      'Thuis',
    nav_feedings:  'Voedingen',
    nav_diapers:   'Luiers',
    nav_weight:    'Gewicht',
    nav_settings:  'Schema',

    // Header
    app_title:     'Baby Tracker',
    months:        'mnd',
    weeks:         'wk',
    days:          'dag',
    age_newborn:   'Pasgeboren',

    // Dashboard
    next_feeding:  'Volgende voeding over',
    overdue:       'Voeding te laat!',
    last_feeding:  'Laatste voeding',
    no_feeding_yet:'Nog niet gevoed vandaag',
    feedings_today:'Voedingen vandaag',
    schedule_today:'Schema vandaag',
    quick_log:     'Snel registreren',

    // Feeding types
    bottle:        'Fles',
    breast_left:   'Links',
    breast_right:  'Rechts',
    both_breasts:  'Beide',
    solid:         'Vast voedsel',

    // Diaper types
    wet:           'Nat',
    dirty:         'Vuil',
    both:          'Nat + Vuil',
    dry:           'Droog',

    // Quick buttons
    btn_feeding:   'Voeding',
    btn_wet:       'Nat',
    btn_dirty:     'Vuil',
    btn_both_diaper:'Beide',
    btn_weight:    'Gewicht',
    btn_sleep:     'Slaap',

    // Feedings section
    feedings_title:'Voedingen',
    add_feeding:   'Voeding toevoegen',
    feeding_time:  'Tijdstip',
    feeding_amount:'Hoeveelheid (ml)',
    feeding_type:  'Type voeding',
    feeding_notes: 'Notities',
    no_feedings:   'Geen voedingen gevonden',
    total_today:   'Totaal vandaag',
    avg_amount:    'Gemiddeld',

    // Diapers section
    diapers_title: 'Luierwissel',
    add_diaper:    'Luier toevoegen',
    diaper_time:   'Tijdstip',
    diaper_type_lbl:'Type luier',
    no_diapers:    'Geen luiers gevonden',
    wet_count:     'Nat',
    dirty_count:   'Vuil',

    // Weight section
    weight_title:  'Gewicht',
    add_weight:    'Gewicht toevoegen',
    weight_amount: 'Gewicht (gram)',
    weight_date:   'Datum & tijd',
    weight_notes:  'Notities',
    no_weight:     'Geen gewicht gevonden',
    current_weight:'Huidig gewicht',
    weight_change: 'Verandering',

    // Calculator
    calc_title:    'Voeding berekenen',
    calc_weight:   'Gewicht baby (gram)',
    calc_feedings: 'Aantal voedingen per dag',
    calc_result:   'Aanbevolen per fles',
    calc_total:    'Totaal per dag',
    calc_formula:  'Formule',
    calc_btn:      'Bereken',

    // Schedule
    schedule_title:'Voedingsschema',
    schedule_first:'Eerste voeding',
    schedule_last: 'Laatste voeding (optioneel)',
    schedule_num:  'Aantal voedingen',
    schedule_buf:  'Boer/ophoud buffer (min)',
    blocked_title: 'Geblokkeerde tijden',
    blocked_add:   'Tijd toevoegen',
    blocked_label: 'Omschrijving',
    blocked_start: 'Van',
    blocked_end:   'Tot',
    save_schedule: 'Schema opslaan',
    calc_schedule: 'Schema berekenen',
    schedule_saved:'Schema opgeslagen!',
    schedule_warnings: 'Aanpassingen',

    // Settings  
    settings_title:'Instellingen',
    baby_name:     'Naam baby',
    baby_birth:    'Geboortedatum',
    baby_gender:   'Geslacht',
    gender_boy:    'Jongen',
    gender_girl:   'Meisje',
    gender_other:  'Anders',
    save_settings: 'Opslaan',
    settings_saved:'Instellingen opgeslagen!',

    // Actions
    save:    'Opslaan',
    cancel:  'Annuleren',
    delete:  'Verwijderen',
    close:   'Sluiten',
    now:     'Nu',
    confirm_delete: 'Zeker weten dat je dit wilt verwijderen?',

    // Units
    ml:   'ml',
    gram: 'g',
    kg:   'kg',
    min:  'min',

    // Time ago
    just_now:    'Zojuist',
    min_ago:     'min geleden',
    hour_ago:    'uur geleden',
    hours_ago:   'uur geleden',
    today:       'Vandaag',
    yesterday:   'Gisteren',

    // Status
    sleeping:    'Slaapt',
    awake:       'Wakker',
    loading:     'Laden...',
    no_data:     'Geen gegevens',
    error:       'Er is een fout opgetreden',
  },

  en: {
    // Navigation
    nav_home:      'Home',
    nav_feedings:  'Feedings',
    nav_diapers:   'Diapers',
    nav_weight:    'Weight',
    nav_settings:  'Schedule',

    // Header
    app_title:     'Baby Tracker',
    months:        'mo',
    weeks:         'wk',
    days:          'd',
    age_newborn:   'Newborn',

    // Dashboard
    next_feeding:  'Next feeding in',
    overdue:       'Feeding overdue!',
    last_feeding:  'Last feeding',
    no_feeding_yet:'No feeding yet today',
    feedings_today:'Feedings today',
    schedule_today:'Today\'s schedule',
    quick_log:     'Quick log',

    // Feeding types
    bottle:        'Bottle',
    breast_left:   'Left',
    breast_right:  'Right',
    both_breasts:  'Both',
    solid:         'Solid food',

    // Diaper types
    wet:           'Wet',
    dirty:         'Dirty',
    both:          'Wet + Dirty',
    dry:           'Dry',

    // Quick buttons
    btn_feeding:   'Feeding',
    btn_wet:       'Wet',
    btn_dirty:     'Dirty',
    btn_both_diaper:'Both',
    btn_weight:    'Weight',
    btn_sleep:     'Sleep',

    // Feedings section
    feedings_title:'Feedings',
    add_feeding:   'Add feeding',
    feeding_time:  'Time',
    feeding_amount:'Amount (ml)',
    feeding_type:  'Feeding type',
    feeding_notes: 'Notes',
    no_feedings:   'No feedings found',
    total_today:   'Total today',
    avg_amount:    'Average',

    // Diapers section
    diapers_title: 'Diaper change',
    add_diaper:    'Add diaper',
    diaper_time:   'Time',
    diaper_type_lbl:'Diaper type',
    no_diapers:    'No diapers found',
    wet_count:     'Wet',
    dirty_count:   'Dirty',

    // Weight section
    weight_title:  'Weight',
    add_weight:    'Add weight',
    weight_amount: 'Weight (grams)',
    weight_date:   'Date & time',
    weight_notes:  'Notes',
    no_weight:     'No weight entries found',
    current_weight:'Current weight',
    weight_change: 'Change',

    // Calculator
    calc_title:    'Calculate feeding',
    calc_weight:   'Baby weight (grams)',
    calc_feedings: 'Number of feedings per day',
    calc_result:   'Recommended per bottle',
    calc_total:    'Total per day',
    calc_formula:  'Formula',
    calc_btn:      'Calculate',

    // Schedule
    schedule_title:'Feeding Schedule',
    schedule_first:'First feeding',
    schedule_last: 'Last feeding (optional)',
    schedule_num:  'Number of feedings',
    schedule_buf:  'Burp/upright buffer (min)',
    blocked_title: 'Blocked time windows',
    blocked_add:   'Add window',
    blocked_label: 'Description',
    blocked_start: 'From',
    blocked_end:   'Until',
    save_schedule: 'Save schedule',
    calc_schedule: 'Calculate schedule',
    schedule_saved:'Schedule saved!',
    schedule_warnings: 'Adjustments made',

    // Settings
    settings_title:'Settings',
    baby_name:     'Baby\'s name',
    baby_birth:    'Date of birth',
    baby_gender:   'Gender',
    gender_boy:    'Boy',
    gender_girl:   'Girl',
    gender_other:  'Other',
    save_settings: 'Save',
    settings_saved:'Settings saved!',

    // Actions
    save:    'Save',
    cancel:  'Cancel',
    delete:  'Delete',
    close:   'Close',
    now:     'Now',
    confirm_delete: 'Are you sure you want to delete this?',

    // Units
    ml:   'ml',
    gram: 'g',
    kg:   'kg',
    min:  'min',

    // Time ago
    just_now:    'Just now',
    min_ago:     'min ago',
    hour_ago:    'hour ago',
    hours_ago:   'hours ago',
    today:       'Today',
    yesterday:   'Yesterday',

    // Status
    sleeping:    'Sleeping',
    awake:       'Awake',
    loading:     'Loading...',
    no_data:     'No data',
    error:       'An error occurred',
  }
};

let currentLang = 'nl';

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('bt_lang', lang);
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

// Export
window.t = t;
window.setLang = setLang;
window.TRANSLATIONS = TRANSLATIONS;
window.getCurrentLang = () => currentLang;
