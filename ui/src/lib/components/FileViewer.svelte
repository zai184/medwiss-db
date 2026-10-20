<script lang="ts">
	import { Loader2, FileWarning, Download, FileText, Image, Music, File, Maximize, X, Play, Pause } from 'lucide-svelte';
	import { renderMermaid } from '$lib/mermaid.js';
	import { apiClient } from '$lib/api';
	import TranscribeModal from './TranscribeModal.svelte';
	import { entryViewer } from '$lib/stores/entryViewer';
	import { marked } from 'marked';
	import DOMPurify from 'isomorphic-dompurify';
	import type { PDFDocumentLoadingTask } from 'pdfjs-dist';

	// pdf.js is imported lazily on first PDF (chunk + ~1MB worker only when needed).
	// Mobile browsers render no PDFs inside iframes, so we draw pages to canvas.
	let pdfjsP: Promise<typeof import('pdfjs-dist')> | null = null;
	function getPdfjs() {
		pdfjsP ??= (async () => {
			const pdfjs = await import('pdfjs-dist');
			pdfjs.GlobalWorkerOptions.workerSrc = (
				await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
			).default;
			return pdfjs;
		})();
		return pdfjsP;
	}

	interface FileInfo {
		exists: boolean;
		mime_type: string | null;
		size: number | null;
		can_inline: boolean;
	}

	interface Props {
		entryId: number;
	}

	let { entryId }: Props = $props();

	// When this FileViewer is opened inside the gallery overlay, render
	// prev/next navigation — including inside native fullscreen, where only
	// the fullscreen element's subtree is displayed (the overlay's own buttons
	// would be invisible there).
	const viewer = $derived($entryViewer);
	const galleryPrevAvailable = $derived(viewer != null && viewer.gallery.length > 1 && viewer.index > 0);
	const galleryNextAvailable = $derived(viewer != null && viewer.gallery.length > 1 && viewer.index < viewer.gallery.length - 1);

	let fileInfo: FileInfo | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);
	let transcribeModalOpen = $state(false);
	let markdownContent = $state('');
	let loadingMarkdown = $state(false);
	let isMarkdown = $state(false);
	let imageContainer: HTMLDivElement | undefined = $state();
	let pdfContainer: HTMLDivElement | undefined = $state();
	let markdownContainer: HTMLDivElement | undefined = $state();
	let audioEl: HTMLAudioElement | undefined = $state();
	let audioTime = $state(0);
	let audioDuration = $state(0);
	let audioPlaying = $state(false);
	let audioRate = $state(1);
	const AUDIO_RATES = [1, 1.25, 1.5, 2] as const;

	function formatClock(seconds: number): string {
		if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
		const total = Math.floor(seconds);
		const h = Math.floor(total / 3600);
		const m = Math.floor((total % 3600) / 60);
		const s = total % 60;
		const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
		const ss = String(s).padStart(2, '0');
		return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
	}

	function seekBy(delta: number) {
		if (!audioEl) return;
		const end = Number.isFinite(audioEl.duration) ? audioEl.duration : 0;
		const next = Math.min(Math.max(0, audioEl.currentTime + delta), end || audioEl.currentTime + delta);
		audioEl.currentTime = Math.max(0, next);
		audioTime = audioEl.currentTime;
	}

	function setAudioRate(rate: number) {
		audioRate = rate;
		if (audioEl) audioEl.playbackRate = rate;
	}

	function onAudioSeek(e: Event) {
		const value = Number((e.currentTarget as HTMLInputElement).value);
		if (audioEl) audioEl.currentTime = value;
		audioTime = value;
	}

	function toggleAudio() {
		if (!audioEl) return;
		if (audioEl.paused) void audioEl.play();
		else audioEl.pause();
	}

	$effect(() => {
		void entryId;
		audioTime = 0;
		audioDuration = 0;
		audioPlaying = false;
	});

	const ZOOM_MAX = 8;
	let zoom = $state(1);
	const TypeIcon = $derived.by(() => getFileTypeIcon(fileInfo && fileInfo.mime_type));
	let panX = $state(0);
	let panY = $state(0);
	let dragging = false;
	let lastX = 0;
	let lastY = 0;
	let cssFullscreen = $state(false);
	let nativeFullscreen = $state(false);
	let isFullscreen = $derived(cssFullscreen || nativeFullscreen);

	// Active pointers for the two-finger pinch gesture.
	const activePointers = new Map<number, { x: number; y: number }>();
	let pinchStartDist = 0;
	let pinchStartZoom = 1;
	let pinchLastMidX = 0;
	let pinchLastMidY = 0;

	function pointerDist(a: { x: number; y: number }, b: { x: number; y: number }) {
		return Math.hypot(b.x - a.x, b.y - a.y);
	}

	function pointerMid(a: { x: number; y: number }, b: { x: number; y: number }) {
		return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
	}

	function applyWheelZoom(e: WheelEvent) {
		e.preventDefault();
		const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
		zoom = Math.min(ZOOM_MAX, Math.max(1, zoom * factor));
		if (zoom === 1) {
			panX = 0;
			panY = 0;
		}
	}

	let moveDist = 0;

	function handleImageClick() {
		// Click toggles fullscreen only in the unzoomed state; zoomed clicks pan.
		// A drag/swipe (gallery swipe, drag-pan) must not count as a click —
		// some browsers still synthesize one after a touch drag, which would
		// exit the fullscreen the swipe happened in.
		if (moveDist > 10) return;
		if (zoom === 1) toggleImageFullscreen();
	}

	function startPinch() {
		const pts = [...activePointers.values()];
		pinchStartDist = pointerDist(pts[0], pts[1]);
		pinchStartZoom = zoom;
		const m = pointerMid(pts[0], pts[1]);
		pinchLastMidX = m.x;
		pinchLastMidY = m.y;
	}

	function handlePointerDown(e: PointerEvent) {
		const el = e.currentTarget as HTMLElement;
		// Gesture / scroll interplay (mobile):
		// - At zoom === 1 the <img> carries touch-action: pan-y, so the browser
		//   keeps single-finger vertical drags and the .image-scroll container
		//   scrolls natively (a tall image stays fully reachable by swiping).
		//   Capturing the pointer there would steal that gesture, so we skip
		//   capture for touch while unzoomed.
		// - A diagonal/two-finger pinch still reaches us (pan-y does not let the
		//   browser claim horizontal gestures) and zooms in; once zoom > 1 the
		//   img switches to touch-action: none and touch pointers are captured
		//   again so the existing drag-pan keeps full control.
		// - Desktop is unaffected: mouse always captures for drag at zoom > 1,
		//   and wheel zoom lives on the container's onwheel handler.
		const isTouch = e.pointerType === 'touch';
		if (zoom > 1 || !isTouch) {
			try {
				el.setPointerCapture(e.pointerId);
			} catch {
				/* pointer may already be gone */
			}
		}
		activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
		lastX = e.clientX;
		lastY = e.clientY;
		moveDist = 0;
		if (activePointers.size === 2 && e.pointerType !== 'mouse') {
			// Second finger down begins a pinch; don't drag.
			startPinch();
			dragging = false;
		} else {
			dragging = activePointers.size === 1 && zoom > 1;
		}
	}

	function handlePointerMove(e: PointerEvent) {
		const p = activePointers.get(e.pointerId);
		if (!p) return;
		p.x = e.clientX;
		p.y = e.clientY;
		moveDist += Math.hypot(e.clientX - lastX, e.clientY - lastY);

		if (activePointers.size === 2 && e.pointerType !== 'mouse') {
			// Pinch: scale by the pointer-distance ratio, pan by the midpoint delta.
			const pts = [...activePointers.values()];
			if (pinchStartDist > 0) {
				zoom = Math.min(ZOOM_MAX, Math.max(1, pinchStartZoom * (pointerDist(pts[0], pts[1]) / pinchStartDist)));
			}
			const m = pointerMid(pts[0], pts[1]);
			panX += m.x - pinchLastMidX;
			panY += m.y - pinchLastMidY;
			pinchLastMidX = m.x;
			pinchLastMidY = m.y;
			if (zoom === 1) {
				panX = 0;
				panY = 0;
			}
			return;
		}

		if (!dragging) return;
		panX += e.clientX - lastX;
		panY += e.clientY - lastY;
		lastX = e.clientX;
		lastY = e.clientY;
	}

	function handlePointerUp(e: PointerEvent) {
		activePointers.delete(e.pointerId);
		dragging = false;
		pinchStartDist = 0;
		if (activePointers.size === 1 && zoom > 1) {
			// Two fingers lifted to one: re-anchor drag to the remaining pointer.
			const [rem] = [...activePointers.values()];
			lastX = rem.x;
			lastY = rem.y;
			dragging = true;
		}
	}

	function resetZoom() {
		zoom = 1;
		panX = 0;
		panY = 0;
	}

	function toggleImageFullscreen() {
		if (!imageContainer) return;
		if (cssFullscreen) {
			exitCssFullscreen();
		} else if (document.fullscreenElement) {
			void document.exitFullscreen();
		} else if (imageContainer.requestFullscreen) {
			void imageContainer.requestFullscreen();
		} else {
			cssFullscreen = true;
		}
	}

	function exitCssFullscreen() {
		cssFullscreen = false;
		resetZoom();
	}

	function closeFullscreen() {
		if (cssFullscreen) {
			exitCssFullscreen();
		} else if (document.fullscreenElement) {
			void document.exitFullscreen();
		}
	}

	function enterPdfFullscreen() {
		if (!pdfContainer || document.fullscreenElement) return;
		if (pdfContainer.requestFullscreen) {
			// Native fullscreen is preferred; fall back to a CSS overlay if denied/unavailable.
			Promise.resolve(pdfContainer.requestFullscreen()).catch(() => {
				cssFullscreen = true;
			});
		} else {
			cssFullscreen = true;
		}
	}

	function exitPdfFullscreen() {
		if (cssFullscreen) {
			cssFullscreen = false;
		} else if (document.fullscreenElement) {
			void document.exitFullscreen();
		}
	}

	let pdfScroll: HTMLDivElement | undefined = $state();
	let pdfStatus = $state<'idle' | 'loading' | 'ready' | 'error'>('idle');
	let pdfError = $state('');
	let pdfNumPages = $state(0);
	let pageCanvases: (HTMLCanvasElement | undefined)[] = $state([]);
	// pdf.js v6: documents are torn down via their loading task, not the doc.
	let pdfTask: PDFDocumentLoadingTask | null = null;
	// loadGen invalidates in-flight document loads (entry switch), renderSeq
	// invalidates in-flight page renders (entry switch or width change).
	let loadGen = 0;
	let renderSeq = 0;

	function destroyPdf() {
		loadGen++;
		renderSeq++;
		const task = pdfTask;
		pdfTask = null;
		pdfNumPages = 0;
		pageCanvases = [];
		pdfStatus = 'idle';
		pdfError = '';
		void task?.destroy();
	}

	async function loadPdf() {
		const gen = ++loadGen;
		const seq = ++renderSeq;
		const prev = pdfTask;
		pdfTask = null;
		pdfNumPages = 0;
		pageCanvases = [];
		pdfStatus = 'loading';
		pdfError = '';
		void prev?.destroy();
		try {
			const pdfjs = await getPdfjs();
			if (gen !== loadGen) return;
			const task = pdfjs.getDocument({ url: `/api/v1/files/entries/${entryId}/view` });
			pdfTask = task;
			const doc = await task.promise;
			if (gen !== loadGen) return;
			pdfNumPages = doc.numPages;
			// Let the {#each} create the page canvases before rendering into them.
			await new Promise((r) => setTimeout(r, 0));
			await renderPdfPages(gen, seq);
			if (gen === loadGen && seq === renderSeq) pdfStatus = 'ready';
		} catch (e) {
			if (gen !== loadGen) return;
			pdfStatus = 'error';
			pdfError =
				(e as { name?: string })?.name === 'PasswordException'
					? 'PDF ist passwortgeschützt'
					: 'PDF konnte nicht geladen werden';
		}
	}

	async function renderPdfPages(gen: number, seq: number) {
		const task = pdfTask;
		const scroll = pdfScroll;
		if (!task || !scroll) return;
		const cssWidth = scroll.clientWidth || 600;
		if (cssWidth <= 0) return;
		const doc = await task.promise;
		for (let i = 1; i <= doc.numPages; i++) {
			if (gen !== loadGen || seq !== renderSeq) return;
			const canvas = pageCanvases[i - 1];
			if (!canvas) return;
			try {
				const page = await doc.getPage(i);
				if (gen !== loadGen || seq !== renderSeq) return;
				const base = page.getViewport({ scale: 1 });
				const viewport = page.getViewport({ scale: cssWidth / base.width });
				// Cap pixel count: iOS Safari silently drops canvases > ~16M px.
				const outScale = Math.min(
					window.devicePixelRatio || 1,
					2,
					Math.sqrt(16_000_000 / (viewport.width * viewport.height))
				);
				canvas.width = Math.floor(viewport.width * outScale);
				canvas.height = Math.floor(viewport.height * outScale);
				await page.render({
					canvas,
					viewport,
					transform: outScale !== 1 ? [outScale, 0, 0, outScale, 0, 0] : undefined
				}).promise;
				page.cleanup();
			} catch (e) {
				if (gen !== loadGen || seq !== renderSeq) return;
				pdfStatus = 'error';
				pdfError = 'PDF-Seite konnte nicht gerendert werden';
				return;
			}
		}
	}

	// Re-render at the new width when the container resizes (fullscreen toggle,
	// device rotation) — canvases are drawn once at a fixed pixel width.
	$effect(() => {
		if (pdfNumPages === 0 || !pdfScroll) return;
		const scroll = pdfScroll;
		let lastWidth = scroll.clientWidth;
		let t: ReturnType<typeof setTimeout> | undefined;
		const ro = new ResizeObserver(() => {
			if (Math.abs(scroll.clientWidth - lastWidth) < 40) return;
			clearTimeout(t);
			t = setTimeout(() => {
				lastWidth = scroll.clientWidth;
				void renderPdfPages(loadGen, ++renderSeq);
			}, 200);
		});
		ro.observe(scroll);
		return () => {
			clearTimeout(t);
			ro.disconnect();
		};
	});

	// Release the worker/document when the component unmounts.
	$effect(() => {
		return () => {
			loadGen++;
			void pdfTask?.destroy();
			pdfTask = null;
		};
	});

	$effect(() => {
		const onChange = () => {
			nativeFullscreen = !!document.fullscreenElement;
			if (!document.fullscreenElement) resetZoom();
		};
		document.addEventListener('fullscreenchange', onChange);
		return () => document.removeEventListener('fullscreenchange', onChange);
	});

	async function loadMarkdownContent() {
		try {
			loadingMarkdown = true;
			const response = await apiClient.get(`/files/entries/${entryId}/view`, {
				responseType: 'text'
			});
			markdownContent = DOMPurify.sanitize(marked.parse(response.data) as string);
		} catch (e: any) {
			console.error('Failed to load markdown:', e);
			markdownContent = '<p>Fehler beim Laden der Markdown-Datei</p>';
		} finally {
			loadingMarkdown = false;
		}
	}

	$effect(() => {
		if (markdownContent && markdownContainer) void renderMermaid(markdownContainer);
	});

	let loadedOnce = false;

	async function loadFileInfo() {
		try {
			// First load shows a spinner; later entry switches (gallery next/prev)
			// keep the current content visible so a fullscreen element is never
			// unmounted mid-swipe.
			loading = !loadedOnce;
			error = null;
			const response = await apiClient.get(`/files/entries/${entryId}/info`);
			loadedOnce = true;
			fileInfo = response.data;
			isMarkdown = fileInfo?.mime_type === 'text/markdown' || fileInfo?.mime_type === 'text/x-markdown';
			if (isMarkdown) {
				destroyPdf();
				markdownContent = '';
				await loadMarkdownContent();
			} else if (fileInfo?.mime_type === 'application/pdf') {
				void loadPdf();
			} else {
				destroyPdf();
			}
		} catch (e: any) {
			if (e.response?.status === 404) {
				error = 'Datei nicht gefunden';
			} else if (e.response?.status === 403) {
				error = 'Zugriff verweigert';
			} else {
				error = e.message || 'Fehler beim Laden der Dateiinformationen';
			}
		} finally {
			loading = false;
		}
	}

	function formatFileSize(bytes: number | null): string {
		if (bytes === null || bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	function getFileTypeIcon(mimeType: string | null) {
		if (!mimeType) return File;
		if (mimeType === 'application/pdf') return FileText;
		if (mimeType.startsWith('image/')) return Image;
		if (mimeType.startsWith('audio/')) return Music;
		return File;
	}

	function handleTranscribeCancel() {
		transcribeModalOpen = false;
	}

	// Reload per entryId (gallery navigation). Plain lastLoadedId keeps the
	// effect from re-running on its own state writes.
	let lastLoadedId: number | null = null;
	$effect(() => {
		const id = entryId;
		if (id === lastLoadedId) return;
		lastLoadedId = id;
		resetZoom();
		void loadFileInfo();
	});
</script>

<div class="file-viewer">
	{#snippet galleryNav()}
		{#if galleryPrevAvailable}
			<button
				type="button"
				class="gallery-nav gallery-prev"
				aria-label="Vorheriges Bild"
				onclick={(e) => {
					e.stopPropagation();
					entryViewer.prev();
				}}
				onkeydown={(e) => e.stopPropagation()}
			>‹</button>
		{/if}
		{#if galleryNextAvailable}
			<button
				type="button"
				class="gallery-nav gallery-next"
				aria-label="Nächstes Bild"
				onclick={(e) => {
					e.stopPropagation();
					entryViewer.next();
				}}
				onkeydown={(e) => e.stopPropagation()}
			>›</button>
		{/if}
	{/snippet}

	{#if loading}
		<div class="loading-state">
			<div class="spinner">
				<Loader2 size={32} />
			</div>
			<span>Datei wird geladen...</span>
		</div>
	{:else if error}
		<div class="error-state">
			<FileWarning size={32} />
			<p>{error}</p>
			<button class="retry-btn" onclick={loadFileInfo}>
				Erneut versuchen
			</button>
		</div>
	{:else if fileInfo?.exists}
		<div class="file-content">
			<div class="file-actions">
				<div class="file-info">
					<TypeIcon size={20} />
					<span class="file-type">
					{#if fileInfo.mime_type === 'application/pdf'}
						PDF-Dokument
					{:else if fileInfo.mime_type?.startsWith('image/')}
						Bild
					{:else if fileInfo.mime_type?.startsWith('audio/')}
						Audiodatei
					{:else if isMarkdown}
						Markdown
					{:else if fileInfo.mime_type?.startsWith('text/')}
						Textdatei
					{:else}
						{fileInfo.mime_type || 'Unbekannter Dateityp'}
					{/if}
					</span>
					{#if fileInfo.size}
						<span class="file-size">({formatFileSize(fileInfo.size)})</span>
					{/if}
				</div>
				<a
					href="/api/v1/files/entries/{entryId}/download"
					class="download-btn"
					download
				>
					<Download size={18} />
					Herunterladen
				</a>
				<button
					type="button"
					class="transcribe-btn"
					onclick={() => transcribeModalOpen = true}
				>
					Transkribieren
				</button>
			</div>
			<div class="file-preview">
				{#if fileInfo.mime_type === 'application/pdf'}
					<div class="pdf-block">
						{#if !isFullscreen}
							<div class="pdf-toolbar">
								<button
									type="button"
									class="pdf-expand-btn"
									onclick={enterPdfFullscreen}
									aria-label="PDF im Vollbild öffnen"
									title="Vollbild"
								>
									<Maximize size={18} />
								</button>
							</div>
						{/if}
						<div
							class="pdf-container"
							class:css-fullscreen={cssFullscreen}
							bind:this={pdfContainer}
						>
							{#if pdfStatus === 'error'}
								<div class="pdf-error">
									<FileWarning size={24} />
									<p>{pdfError}</p>
									<a href="/api/v1/files/entries/{entryId}/view" target="_blank" rel="noopener">
										Im Tab öffnen
									</a>
								</div>
							{:else}
								<div class="pdf-scroll" bind:this={pdfScroll}>
									{#if pdfStatus === 'loading' && pdfNumPages === 0}
										<div class="loading-state">
											<div class="spinner">
												<Loader2 size={24} />
											</div>
											<span>PDF wird geladen...</span>
										</div>
									{/if}
									{#each { length: pdfNumPages } as _, i (i)}
										<canvas
											bind:this={pageCanvases[i]}
											class="pdf-page-canvas"
											aria-label={'Seite ' + (i + 1)}
										></canvas>
									{/each}
								</div>
							{/if}
							{#if isFullscreen}
								<button
									class="fullscreen-close"
									onclick={exitPdfFullscreen}
									aria-label="Vollbild schließen"
								>
									<X size={20} />
								</button>
							{/if}
							{@render galleryNav()}
						</div>
					</div>
				{:else if fileInfo.mime_type?.startsWith('image/')}
					<div
						class="image-scroll"
						class:css-fullscreen={cssFullscreen}
						data-zoomed={zoom > 1}
						bind:this={imageContainer}
						role="button"
						tabindex="0"
						onclick={handleImageClick}
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.preventDefault();
								toggleImageFullscreen();
							}
						}}
						onwheel={applyWheelZoom}
						ondblclick={resetZoom}
						onpointerdown={handlePointerDown}
						onpointermove={handlePointerMove}
						onpointerup={handlePointerUp}
						onpointercancel={handlePointerUp}
						onlostpointercapture={handlePointerUp}
						title="Bild — Klick: Vollbild · Scrollen/Zoom: Zoom · Doppelklick: zurücksetzen"
					>
						<img
							src="/api/v1/files/entries/{entryId}/view"
							alt="Dateivorschau"
							class="image-viewer"
						style="transform: translate({panX}px, {panY}px) scale({zoom}); touch-action: {zoom > 1 ? 'none' : 'pan-y'}; cursor: {zoom > 1 ? 'grab' : 'zoom-in'}"
						/>
						{#if isFullscreen}
							<button
								class="fullscreen-close"
								onclick={(e) => {
									e.stopPropagation();
									closeFullscreen();
								}}
								aria-label="Vollbild schließen"
							>
								<X size={20} />
							</button>
						{:else}
							<div class="fullscreen-hint">
								<Maximize size={16} />
							</div>
						{/if}
						{@render galleryNav()}
					</div>
				{:else if fileInfo.mime_type?.startsWith('audio/')}
					<div class="audio-container">
						<audio
							bind:this={audioEl}
							preload="metadata"
							src="/api/v1/files/entries/{entryId}/view"
							ontimeupdate={() => { audioTime = audioEl?.currentTime ?? 0; }}
							onloadedmetadata={() => {
								audioDuration = audioEl?.duration ?? 0;
								if (audioEl) audioEl.playbackRate = audioRate;
							}}
							ondurationchange={() => { audioDuration = audioEl?.duration ?? 0; }}
							onplay={() => { audioPlaying = true; }}
							onpause={() => { audioPlaying = false; }}
							onended={() => { audioPlaying = false; }}
						></audio>
						<div class="audio-controls">
							<div class="audio-transport">
								<button type="button" class="audio-skip" onclick={() => seekBy(-20)} aria-label="20 Sekunden zurück">&lt;&lt;</button>
								<button type="button" class="audio-play" onclick={toggleAudio} aria-label={audioPlaying ? 'Pause' : 'Abspielen'}>
									{#if audioPlaying}
										<Pause size={20} />
									{:else}
										<Play size={20} />
									{/if}
								</button>
								<button type="button" class="audio-skip" onclick={() => seekBy(20)} aria-label="20 Sekunden vor">&gt;&gt;</button>
								<span class="audio-clock">{formatClock(audioTime)} / {formatClock(audioDuration)}</span>
							</div>
							<input
								class="audio-seek"
								type="range"
								min="0"
								max={audioDuration || 0}
								step="1"
								value={audioTime}
								oninput={onAudioSeek}
								aria-label="Wiedergabeposition"
								aria-valuetext="{formatClock(audioTime)} von {formatClock(audioDuration)}"
								disabled={!audioDuration}
							/>
							<div class="audio-rates" role="group" aria-label="Geschwindigkeit">
								{#each AUDIO_RATES as rate (rate)}
									<button
										type="button"
										class:active={audioRate === rate}
										onclick={() => setAudioRate(rate)}
									>{String(rate).replace('.', ',')}×</button>
								{/each}
							</div>
						</div>
					</div>
				{:else if isMarkdown}
					{#if loadingMarkdown}
						<div class="loading-state">
							<div class="spinner">
								<Loader2 size={24} />
							</div>
							<span>Markdown wird geladen...</span>
						</div>
					{:else}
					<div class="markdown-content" bind:this={markdownContainer}>{@html markdownContent}</div>
					{/if}
				{:else if fileInfo.mime_type?.startsWith('text/')}
					<iframe
						src="/api/v1/files/entries/{entryId}/view"
						title="Textvorschau"
						class="text-viewer"
					>
						<p>Ihr Browser unterstützt keine Textvorschau.</p>
					</iframe>
				{:else}
					<div class="unsupported-type">
						<TypeIcon size={48} />
						<p>Vorschau für diesen Dateityp nicht verfügbar</p>
						{#if fileInfo.mime_type}
							<span class="mime-type">{fileInfo.mime_type}</span>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<div class="empty-state">
			<File size={48} />
			<p>Keine Quelldatei verfügbar</p>
			<span class="empty-hint">Dieser Eintrag hat keine angehängte Datei</span>
		</div>
	{/if}
</div>

<TranscribeModal
	entryId={entryId}
	open={transcribeModalOpen}
	oncancel={handleTranscribeCancel}
/>

<style>
	.file-viewer {
		width: 100%;
	}

	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-4);
		color: var(--color-text-secondary);
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
	}

	.spinner {
		animation: spin 1s linear infinite;
		color: var(--color-primary);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-4);
		color: var(--color-error);
		text-align: center;
		background: var(--color-error-subtle);
		border: 1px solid var(--color-error);
		border-radius: var(--radius-lg);
	}

	.retry-btn {
		margin-top: var(--space-4);
		padding: var(--space-2) var(--space-4);
		background: var(--color-background-primary);
		border: 1px solid var(--color-error);
		color: var(--color-error);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.retry-btn:hover {
		background: var(--color-error);
		color: white;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-4);
		color: var(--color-text-secondary);
		text-align: center;
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		border-style: dashed;
	}

	.empty-hint {
		font-size: var(--font-size-sm);
		color: var(--color-text-tertiary);
	}

	.file-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.file-preview {
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
		overflow: hidden;
		min-height: 200px;
	}

	.pdf-container {
		position: relative;
	}

	.pdf-container:fullscreen,
	.pdf-container.css-fullscreen {
		width: 100vw;
		height: 100vh;
		display: flex;
		align-items: stretch;
		background: #000;
		border-radius: 0;
	}

	.pdf-container.css-fullscreen {
		position: fixed;
		inset: 0;
		z-index: 300;
	}

	.pdf-container:fullscreen .pdf-scroll,
	.pdf-container.css-fullscreen .pdf-scroll {
		flex: 1 1 auto;
		width: 100%;
		height: 100%;
		max-height: none;
	}

	.pdf-scroll {
		width: 100%;
		max-height: 800px;
		overflow-y: auto;
		background: var(--color-background-primary);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2);
	}

	.pdf-page-canvas {
		width: 100%;
		height: auto;
		display: block;
		background: white;
		box-shadow: var(--shadow-md);
	}

	.pdf-error {
		width: 100%;
		min-height: 300px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: var(--space-8);
		color: var(--color-text-secondary);
		text-align: center;
	}

	.pdf-error a {
		color: var(--color-primary);
		font-weight: var(--font-weight-medium);
	}

	.image-scroll {
		position: relative;
		max-height: 800px;
		overflow-y: auto;
		cursor: zoom-in;
		background: var(--color-background-primary);
		border-radius: var(--radius-lg);
	}

	.image-viewer {
		width: 100%;
		height: auto;
		display: block;
	}

	/* Gallery prev/next — inside the scroll container so they survive native
		fullscreen (only the fullscreen element's subtree renders there). */
	.gallery-nav {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		z-index: 310;
		width: 2.6rem;
		height: 2.6rem;
		border: 1px solid rgba(255, 255, 255, 0.6);
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.55);
		color: #fff;
		font-size: 1.8rem;
		line-height: 1;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding-bottom: 0.2rem;
	}
	.gallery-nav:hover {
		background: rgba(0, 0, 0, 0.8);
	}
	.gallery-prev {
		left: var(--space-2);
	}
	.gallery-next {
		right: var(--space-2);
	}
	@media (max-width: 768px) {
		.gallery-nav {
			width: 2.2rem;
			height: 2.2rem;
		}
	}

	.image-scroll.css-fullscreen {
		position: fixed;
		inset: 0;
		z-index: 300;
		background: #000;
		border-radius: 0;
	}

	.image-scroll:fullscreen,
	.image-scroll.css-fullscreen {
		max-height: none;
		width: 100vw;
		height: 100vh;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		overflow: auto;
		cursor: zoom-out;
	}

	.image-scroll:fullscreen .image-viewer,
	.image-scroll.css-fullscreen .image-viewer {
		width: auto;
		max-width: 100%;
		height: auto;
		margin: auto;
	}

	.fullscreen-close {
		position: absolute;
		top: 12px;
		right: 12px;
		z-index: 301;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		padding: 0;
		background: none;
		border: none;
		color: #000;
		cursor: pointer;
		transition: opacity var(--transition-fast);
	}

	.fullscreen-close:hover {
		opacity: 0.55;
	}

	.pdf-block {
		display: flex;
		flex-direction: column;
	}

	.pdf-toolbar {
		display: flex;
		justify-content: flex-end;
		padding: var(--space-2);
		background: var(--color-background-secondary);
		border-bottom: 1px solid var(--color-border);
	}

	.pdf-expand-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-primary);
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.pdf-expand-btn:hover {
		background: var(--color-background);
		border-color: var(--color-primary);
		color: var(--color-primary);
	}

	.fullscreen-hint {
		position: absolute;
		top: 8px;
		right: 8px;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 8px;
		font-size: var(--font-size-xs);
		color: var(--color-text-secondary);
		background: var(--color-background-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		pointer-events: none;
		opacity: 0.8;
	}

	.text-viewer {
		width: 100%;
		height: 600px;
		border: none;
		display: block;
		background: var(--color-background-primary);
	}

	.markdown-content {
		padding: var(--space-5);
		font-size: var(--font-size-base);
		line-height: 1.7;
		color: var(--color-text-primary);
	}
	.markdown-content :global(h1) { font-size: 1.4rem; margin: 0 0 0.75rem; }
	.markdown-content :global(h2) { font-size: 1.2rem; margin: 1rem 0 0.5rem; }
	.markdown-content :global(h3) { font-size: 1.05rem; margin: 0.9rem 0 0.4rem; }
	.markdown-content :global(p) { margin: 0 0 0.6rem; }
	.markdown-content :global(p:last-child) { margin-bottom: 0; }
	.markdown-content :global(ul),
	.markdown-content :global(ol) { margin: 0 0 0.6rem; padding-left: 1.5rem; }
	.markdown-content :global(li) { margin-bottom: 0.25rem; }
	.markdown-content :global(strong) { font-weight: 600; }
	.markdown-content :global(code) {
		background: var(--color-background);
		border-radius: 4px;
		padding: 0.1rem 0.3rem;
		font-size: 0.85em;
	}
	.markdown-content :global(.mermaid-diagram) {
		margin: 0.75rem 0;
		overflow-x: auto;
		text-align: center;
	}

	.markdown-content :global(.mermaid-diagram svg) {
		max-width: 100%;
		height: auto;
	}

	.markdown-content :global(pre) {
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 0.75rem;
		overflow-x: auto;
		margin: 0 0 0.6rem;
	}

	.audio-container {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-6);
		background: var(--color-background-secondary);
	}

	.audio-container audio {
		display: none;
	}

	.audio-controls {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		width: 100%;
	}

	.audio-transport {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.audio-skip,
	.audio-play,
	.audio-rates button {
		border: 1px solid var(--color-border);
		background: var(--color-background-primary);
		color: var(--color-text-primary);
		border-radius: var(--radius-md);
		cursor: pointer;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
	}

	.audio-skip {
		padding: var(--space-2) var(--space-3);
	}

	.audio-play {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: 999px;
		background: var(--color-primary);
		color: white;
		border-color: transparent;
	}

	.audio-clock {
		margin-left: auto;
		font-variant-numeric: tabular-nums;
		font-size: var(--font-size-sm);
		color: var(--color-text-secondary);
	}

	.audio-seek {
		-webkit-appearance: none;
		appearance: none;
		width: 100%;
		height: 32px;
		margin: 0;
		background: transparent;
		cursor: pointer;
	}

	.audio-seek::-webkit-slider-runnable-track {
		height: 8px;
		background: var(--color-border);
		border-radius: 999px;
	}

	.audio-seek::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 20px;
		height: 20px;
		margin-top: -6px;
		border-radius: 50%;
		background: var(--color-primary);
	}

	.audio-seek::-moz-range-track {
		height: 8px;
		background: var(--color-border);
		border-radius: 999px;
	}

	.audio-seek::-moz-range-thumb {
		width: 20px;
		height: 20px;
		border: none;
		border-radius: 50%;
		background: var(--color-primary);
	}

	.audio-seek:disabled {
		cursor: default;
		opacity: 0.6;
	}

	.audio-rates {
		display: flex;
		gap: var(--space-2);
	}

	.audio-rates button {
		padding: var(--space-1) var(--space-3);
	}

	.audio-rates button.active {
		background: var(--color-primary);
		color: white;
		border-color: transparent;
	}

	.unsupported-type {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12);
		gap: var(--space-3);
		color: var(--color-text-secondary);
		background: var(--color-background-secondary);
	}

	.mime-type {
		font-size: var(--font-size-sm);
		color: var(--color-text-tertiary);
		font-family: monospace;
	}

	.file-actions {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--space-4);
		margin-bottom: var(--space-4);
		background: var(--color-background-secondary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
	}

	.file-info {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		color: var(--color-text-secondary);
		font-size: var(--font-size-sm);
	}

	.file-type {
		font-weight: var(--font-weight-medium);
	}

	.file-size {
		color: var(--color-text-tertiary);
	}

	.download-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		background: var(--color-primary);
		color: white;
		text-decoration: none;
		border-radius: var(--radius-md);
		font-weight: var(--font-weight-medium);
		font-size: var(--font-size-sm);
		transition: all var(--transition-fast);
	}

	.download-btn:hover {
		background: var(--color-primary-dark);
	}

	.transcribe-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-4);
		background: #1e40af;
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-weight: var(--font-weight-medium);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.transcribe-btn:hover {
		background: #1e3a8a;
	}

	@media (max-width: 768px) {
		.pdf-scroll {
			max-height: 400px;
		}

		.image-scroll {
			max-height: 400px;
		}

		.text-viewer {
			height: 400px;
		}

		.file-actions {
			flex-direction: row;
			flex-wrap: wrap;
			align-items: center;
			gap: var(--space-3);
		}

		.file-info {
			flex: 1 1 100%;
			min-width: 0;
		}

		.download-btn,
		.transcribe-btn {
			flex: 1 1 0;
			min-width: 0;
			justify-content: center;
			white-space: nowrap;
			padding: var(--space-2) var(--space-2);
		}
	}
</style>
