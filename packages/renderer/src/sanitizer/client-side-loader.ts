/**
 * Returns a <script> block that loads DOMPurify inside the preview iframe.
 * Injected by the preview-server into the served HTML response.
 * DOMPurify runs after the page loads — second sanitization pass.
 *
 * The __DOMPURIFY_INLINE__ placeholder is replaced at build time:
 * `npm run embed:dompurify` inlines the minified DOMPurify source.
 */
export function buildDOMPurifyScript(): string {
  return `
<script>
(function() {
  /* __DOMPURIFY_INLINE__ */

  if (typeof DOMPurify !== 'undefined') {
    document.querySelectorAll('[data-sanitize]').forEach(function(el) {
      el.innerHTML = DOMPurify.sanitize(el.innerHTML, {
        ALLOWED_TAGS: ['b','i','em','strong','p','br','span'],
        ALLOWED_ATTR: ['class'],
      });
    });
  }
})();
</script>`;
}
