<script lang="ts" module>
  let uidCounter = 0;
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  
  export let accept = '.png,.jpg,.jpeg,.pdf,.mp3,.wav,.m4a,.txt,.md';
  export let maxSizeMB = 50;
  export let label = 'Datei hochladen';
  export let description = 'Ziehen Sie Dateien hierher oder klicken Sie zum Auswählen';
  
  const dispatch = createEventDispatcher<{
    upload: { file: File; progress: number };
    error: { message: string };
    remove: void;
  }>();
  
  let dragActive = false;
  let file: File | null = null;
  let uploadProgress = 0;
  let isUploading = false;
  let errorMessage = '';
  
  const validTypes = ['image/png', 'image/jpeg', 'application/pdf', 'audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/mp4', 'text/plain', 'text/markdown'];
  const validExtensions = ['.png', '.jpg', '.jpeg', '.pdf', '.mp3', '.wav', '.m4a', '.txt', '.md'];
  
  function validateFile(file: File): string | null {
    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!validExtensions.includes(fileExtension) && !validTypes.includes(file.type)) {
      return 'Ungültiges Dateiformat. Erlaubt: PNG, JPG, PDF, MP3, WAV, M4A, TXT, MD';
    }
    
    // Check file size
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      return `Datei zu groß. Maximum: ${maxSizeMB}MB`;
    }
    
    return null;
  }
  
  function handleDragEnter(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = true;
  }
  
  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = false;
  }
  
  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = true;
  }
  
  function handleDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    dragActive = false;
    
    errorMessage = '';
    
    const droppedFiles = e.dataTransfer?.files;
    if (droppedFiles && droppedFiles.length > 0) {
      const droppedFile = droppedFiles[0];
      const error = validateFile(droppedFile);
      
      if (error) {
        errorMessage = error;
        dispatch('error', { message: error });
        return;
      }
      
      file = droppedFile;
      startUpload();
    }
  }
  
  function handleFileSelect(e: Event) {
    const input = e.target as HTMLInputElement;
    errorMessage = '';
    
    if (input.files && input.files.length > 0) {
      const selectedFile = input.files[0];
      const error = validateFile(selectedFile);
      
      if (error) {
        errorMessage = error;
        dispatch('error', { message: error });
        return;
      }
      
      file = selectedFile;
      startUpload();
    }
  }
  
  function startUpload() {
    if (!file) return;
    
    isUploading = true;
    uploadProgress = 0;
    
    // Simulate upload progress (in real app, this would be actual upload)
    const interval = setInterval(() => {
      uploadProgress += Math.random() * 15;
      if (uploadProgress >= 100) {
        uploadProgress = 100;
        clearInterval(interval);
        isUploading = false;
        dispatch('upload', { file: file!, progress: 100 });
      }
    }, 200);
  }
  
  function removeFile() {
    file = null;
    uploadProgress = 0;
    isUploading = false;
    errorMessage = '';
    dispatch('remove');
  }
  
  function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  function getFileIcon(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['png', 'jpg', 'jpeg'].includes(ext || '')) return '🖼️';
    if (ext === 'pdf') return '📄';
    if (['mp3', 'wav', 'm4a'].includes(ext || '')) return '🎵';
    return '📎';
  }
  const uid = `file-upload-${++uidCounter}`;
</script>

<div class="file-upload">
  <label class="file-upload__label" for={uid}>{label}</label>
  
  {#if !file}
    <div
      class="file-upload__dropzone"
      class:file-upload__dropzone--active={dragActive}
      class:file-upload__dropzone--error={errorMessage}
      on:dragenter={handleDragEnter}
      on:dragleave={handleDragLeave}
      on:dragover={handleDragOver}
      on:drop={handleDrop}
      role="button"
      tabindex="0"
      aria-label="Datei hier ablegen oder klicken zum Auswählen"
    >
      <input
        type="file"
        id={uid}
        {accept}
        class="file-upload__input"
        on:change={handleFileSelect}
        aria-label="Datei auswählen"
      />
      
      <div class="file-upload__content">
        <div class="file-upload__icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <p class="file-upload__description">{description}</p>
        <p class="file-upload__hint">PNG, JPG, PDF, MP3, WAV, M4A, TXT, MD (max. {maxSizeMB}MB)</p>
      </div>
    </div>
    
    {#if errorMessage}
      <p class="file-upload__error" role="alert">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        {errorMessage}
      </p>
    {/if}
  {:else}
    <div class="file-upload__file" class:file-upload__file--uploading={isUploading}>
      <div class="file-upload__file-icon">{getFileIcon(file.name)}</div>
      <div class="file-upload__file-info">
        <p class="file-upload__file-name">{file.name}</p>
        <p class="file-upload__file-size">{formatFileSize(file.size)}</p>
        
        {#if isUploading}
          <div class="file-upload__progress">
            <div class="file-upload__progress-bar" style="width: {uploadProgress}%"></div>
          </div>
          <p class="file-upload__progress-text">{Math.round(uploadProgress)}% hochgeladen...</p>
        {:else}
          <p class="file-upload__success">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            Hochladen abgeschlossen
          </p>
        {/if}
      </div>
      <button
        type="button"
        class="file-upload__remove"
        on:click={removeFile}
        aria-label="Datei entfernen"
        disabled={isUploading}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  {/if}
</div>

<style>
  .file-upload {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  
  .file-upload__label {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
  }
  
  .file-upload__dropzone {
    position: relative;
    border: 2px dashed var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-8);
    text-align: center;
    cursor: pointer;
    transition: all var(--transition-normal);
    background-color: var(--color-background-secondary);
  }
  
  .file-upload__dropzone:hover {
    border-color: var(--color-border-hover);
    background-color: var(--color-background-tertiary);
  }
  
  .file-upload__dropzone--active {
    border-color: var(--color-primary);
    background-color: var(--color-primary-subtle);
  }
  
  .file-upload__dropzone--error {
    border-color: var(--color-error);
    background-color: var(--color-error-subtle);
  }
  
  .file-upload__input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
  }
  
  .file-upload__content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    pointer-events: none;
  }
  
  .file-upload__icon {
    color: var(--color-text-tertiary);
  }
  
  .file-upload__description {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
  }
  
  .file-upload__hint {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
  }
  
  .file-upload__error {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-sm);
    color: var(--color-error);
    padding: var(--space-3);
    background-color: var(--color-error-subtle);
    border-radius: var(--radius-md);
  }
  
  .file-upload__file {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-4);
    background-color: var(--color-background-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    transition: all var(--transition-normal);
  }
  
  .file-upload__file--uploading {
    background-color: var(--color-primary-subtle);
    border-color: var(--color-primary);
  }
  
  .file-upload__file-icon {
    font-size: var(--font-size-2xl);
    flex-shrink: 0;
  }
  
  .file-upload__file-info {
    flex: 1;
    min-width: 0;
  }
  
  .file-upload__file-name {
    font-weight: var(--font-weight-medium);
    color: var(--color-text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .file-upload__file-size {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    margin-top: var(--space-1);
  }
  
  .file-upload__progress {
    width: 100%;
    height: 4px;
    background-color: var(--color-gray-200);
    border-radius: var(--radius-full);
    margin-top: var(--space-2);
    overflow: hidden;
  }
  
  .file-upload__progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-primary-light) 100%);
    border-radius: var(--radius-full);
    transition: width var(--transition-fast);
  }
  
  .file-upload__progress-text {
    font-size: var(--font-size-xs);
    color: var(--color-primary);
    margin-top: var(--space-1);
  }
  
  .file-upload__success {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--font-size-sm);
    color: var(--color-success);
    margin-top: var(--space-1);
  }
  
  .file-upload__remove {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background-color: var(--color-background-primary);
    color: var(--color-text-secondary);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }
  
  .file-upload__remove:hover:not(:disabled) {
    background-color: var(--color-error-subtle);
    color: var(--color-error);
  }
  
  .file-upload__remove:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
