import { writable, derived } from 'svelte/store';

export type Kategorie = 
  | 'sops' 
  | 'leitlinien' 
  | 'studien' 
  | 'red_flags' 
  | 'frageboegen' 
  | 'infoblaetter' 
  | 'faelle' 
  | 'fortbildung';

export interface EntryFormData {
  titel: string;
  kategorie: Kategorie | '';
  content: string;
  fachgebiete: number[];
  diagnosen: number[];
  symptome: number[];
  quelle: string;
  notizen: string;
}

export interface FormErrors {
  titel?: string;
  kategorie?: string;
  content?: string;
}

export interface LookupItem {
  id: number;
  label: string;
}

export const kategorieOptions: { value: Kategorie; label: string }[] = [
  { value: 'sops', label: 'SOPs' },
  { value: 'leitlinien', label: 'Leitlinien' },
  { value: 'studien', label: 'Studien' },
  { value: 'red_flags', label: 'Red Flags' },
  { value: 'frageboegen', label: 'Fragebögen' },
  { value: 'infoblaetter', label: 'Infoblätter' },
  { value: 'faelle', label: 'Fälle' },
  { value: 'fortbildung', label: 'Fortbildung' }
];

// Initial form state
const initialFormData: EntryFormData = {
  titel: '',
  kategorie: '',
  content: '',
  fachgebiete: [],
  diagnosen: [],
  symptome: [],
  quelle: '',
  notizen: ''
};

// Create stores
export const formData = writable<EntryFormData>({ ...initialFormData });
export const formErrors = writable<FormErrors>({});
export const isSubmitting = writable(false);
export const submitError = writable<string | null>(null);
export const submitSuccess = writable(false);

// Lookup data stores
export const fachgebieteOptions = writable<LookupItem[]>([]);
export const diagnosenOptions = writable<LookupItem[]>([]);
export const symptomeOptions = writable<LookupItem[]>([]);

// KI processing state
export const kiProcessingStatus = writable<'idle' | 'uploading' | 'processing' | 'completed' | 'error'>('idle');
export const kiProgress = writable(0);
export const kiError = writable<string | null>(null);

// Derived stores
export const isFormValid = derived([formData, formErrors], ([$formData, $formErrors]) => {
  // Check required fields
  const hasRequiredFields = 
    $formData.titel.trim() !== '' &&
    $formData.kategorie !== '' &&
    $formData.content.trim() !== '';
  
  // Check no errors
  const hasNoErrors = Object.keys($formErrors).length === 0;
  
  return hasRequiredFields && hasNoErrors;
});

export const hasChanges = derived(formData, ($formData) => {
  return JSON.stringify($formData) !== JSON.stringify(initialFormData);
});

// Validation functions
export function validateField(field: keyof EntryFormData, value: unknown): string | undefined {
  switch (field) {
    case 'titel':
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        return 'Titel ist erforderlich';
      }
      if (typeof value === 'string' && value.trim().length < 3) {
        return 'Titel muss mindestens 3 Zeichen haben';
      }
      if (typeof value === 'string' && value.trim().length > 255) {
        return 'Titel darf maximal 255 Zeichen haben';
      }
      break;
      
    case 'kategorie':
      if (!value || value === '') {
        return 'Kategorie ist erforderlich';
      }
      break;
      
    case 'content':
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        return 'Inhalt ist erforderlich';
      }
      if (typeof value === 'string' && value.trim().length < 10) {
        return 'Inhalt muss mindestens 10 Zeichen haben';
      }
      break;
  }
  
  return undefined;
}

export function validateForm(data: EntryFormData): FormErrors {
  const errors: FormErrors = {};
  
  const titelError = validateField('titel', data.titel);
  if (titelError) errors.titel = titelError;
  
  const kategorieError = validateField('kategorie', data.kategorie);
  if (kategorieError) errors.kategorie = kategorieError;
  
  const contentError = validateField('content', data.content);
  if (contentError) errors.content = contentError;
  
  return errors;
}

// Action functions
export function updateField(field: keyof EntryFormData, value: unknown) {
  formData.update(data => ({
    ...data,
    [field]: value
  }));
  
  // Validate field on change
  const error = validateField(field, value);
  formErrors.update(errors => {
    const newErrors = { ...errors };
    if (error) {
      newErrors[field as keyof FormErrors] = error;
    } else {
      delete newErrors[field as keyof FormErrors];
    }
    return newErrors;
  });
}

export function resetForm() {
  formData.set({ ...initialFormData });
  formErrors.set({});
  submitError.set(null);
  submitSuccess.set(false);
  kiProcessingStatus.set('idle');
  kiProgress.set(0);
  kiError.set(null);
}

export function applyKISuggestions(suggestions: {
  text?: string;
  fachgebiete?: number[];
  diagnosen?: number[];
  symptome?: number[];
  kategorie?: Kategorie;
  titel?: string;
}) {
  formData.update(data => ({
    ...data,
    content: suggestions.text || data.content,
    fachgebiete: suggestions.fachgebiete || data.fachgebiete,
    diagnosen: suggestions.diagnosen || data.diagnosen,
    symptome: suggestions.symptome || data.symptome,
    kategorie: suggestions.kategorie || data.kategorie,
    titel: suggestions.titel || data.titel
  }));
}

export async function submitForm(data: EntryFormData): Promise<{ success: boolean; error?: string }> {
  isSubmitting.set(true);
  submitError.set(null);
  submitSuccess.set(false);
  
  try {
    // Validate before submit
    const errors = validateForm(data);
    if (Object.keys(errors).length > 0) {
      formErrors.set(errors);
      isSubmitting.set(false);
      return { success: false, error: 'Bitte korrigieren Sie die markierten Felder' };
    }
    
    // Simulate API call (replace with actual API call)
    // const response = await fetch('/api/entries', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(data)
    // });
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Simulate success
    submitSuccess.set(true);
    isSubmitting.set(false);
    
    // Reset form after successful submission
    setTimeout(() => {
      resetForm();
    }, 2000);
    
    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Ein unerwarteter Fehler ist aufgetreten';
    submitError.set(errorMessage);
    isSubmitting.set(false);
    return { success: false, error: errorMessage };
  }
}

// Mock data loading (replace with actual API calls)
export async function loadLookupData() {
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 500));
  
  fachgebieteOptions.set([
    { id: 1, label: 'Allgemeinmedizin' },
    { id: 2, label: 'Kardiologie' },
    { id: 3, label: 'Pulmologie' },
    { id: 4, label: 'Gastroenterologie' },
    { id: 5, label: 'Neurologie' },
    { id: 6, label: 'Dermatologie' },
    { id: 7, label: 'Psychiatrie' },
    { id: 8, label: 'Orthopädie' },
    { id: 9, label: 'Onkologie' },
    { id: 10, label: 'Endokrinologie' }
  ]);
  
  diagnosenOptions.set([
    { id: 1, label: 'KHK' },
    { id: 2, label: 'COPD' },
    { id: 3, label: 'Depression' },
    { id: 4, label: 'Diabetes mellitus' },
    { id: 5, label: 'Hypertonie' },
    { id: 6, label: 'Asthma bronchiale' },
    { id: 7, label: 'Migräne' },
    { id: 8, label: 'Osteoarthritis' }
  ]);
  
  symptomeOptions.set([
    { id: 1, label: 'Atemnot' },
    { id: 2, label: 'Kopfschmerz' },
    { id: 3, label: 'Brustschmerz' },
    { id: 4, label: 'Übelkeit' },
    { id: 5, label: 'Schwindel' },
    { id: 6, label: 'Husten' },
    { id: 7, label: 'Fieber' },
    { id: 8, label: 'Müdigkeit' },
    { id: 9, label: 'Gewichtsverlust' },
    { id: 10, label: 'Schlafstörungen' }
  ]);
}
