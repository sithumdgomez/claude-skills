# Motion Craft — Recipe Catalog

Organized by trigger. Each recipe is the minimal snippet — adapt selectors, tokens, and timing to the project it's used in.

## Page-Load

**Staggered entrance (GSAP)**
```js
gsap.from(".hero-el", { y: 24, opacity: 0, duration: 0.8, ease: "power3.out", stagger: 0.1 });
```

**CSS-only fade-up (no library)**
```css
@keyframes fadeUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: none; } }
.entrance { animation: fadeUp .7s cubic-bezier(.22,1,.36,1) both; }
.entrance:nth-child(2) { animation-delay: .1s; }
.entrance:nth-child(3) { animation-delay: .2s; }
```

## Scroll

**Lightweight reveal-on-scroll — IntersectionObserver + CSS (zero dependencies)**
Prefer this for simple fade/slide reveals. It's free, and this exact pattern is already implemented in this project's `main10-clean/styles.css` (`.reveal` / `.reveal-stagger` classes, gated behind an `html.js` toggle so content stays visible with no JS).
```css
.reveal { opacity: 0; transform: translateY(28px); transition: opacity .8s ease, transform .8s ease; }
.reveal.is-visible { opacity: 1; transform: none; }
```
```js
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => e.isIntersecting && e.target.classList.add("is-visible"));
}, { threshold: 0.2 });
document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
```

**GSAP ScrollTrigger — for anything scroll-position-driven**
```js
gsap.to(".parallax-layer", {
  y: -120, ease: "none",
  scrollTrigger: { trigger: ".parallax-section", start: "top bottom", end: "bottom top", scrub: true }
});
```

**Pin-and-reveal section**
```js
ScrollTrigger.create({ trigger: ".pin-section", start: "top top", end: "+=800", pin: true, scrub: 1 });
```

## Hover

**Magnetic button (GSAP)**
```js
btn.addEventListener("mousemove", (e) => {
  const r = btn.getBoundingClientRect();
  gsap.to(btn, { x: (e.clientX - r.left - r.width / 2) * 0.3, y: (e.clientY - r.top - r.height / 2) * 0.3, duration: 0.3 });
});
btn.addEventListener("mouseleave", () => gsap.to(btn, { x: 0, y: 0, duration: 0.4, ease: "elastic.out(1, 0.4)" }));
```

**Card lift (CSS only)**
```css
.card { transition: transform .35s cubic-bezier(.22,1,.36,1), box-shadow .35s; }
.card:hover { transform: translateY(-8px); box-shadow: 0 24px 40px -20px rgba(0,0,0,.35); }
```

**Underline-grow link (CSS only)**
```css
.link { position: relative; }
.link::after { content: ""; position: absolute; left: 0; bottom: -2px; width: 0; height: 2px; background: currentColor; transition: width .3s ease; }
.link:hover::after { width: 100%; }
```

## Click

**Accordion expand/collapse (CSS grid trick — no JS height measuring)**
```css
.acc-body { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .35s ease; }
.acc-item.open .acc-body { grid-template-rows: 1fr; }
.acc-body > div { overflow: hidden; }
```

## Loop

**Seamless infinite marquee (the Wix Studio "testimonial marquee" technique)**
Duplicate the track content once, animate a continuous `translateX`, and the loop point becomes invisible.
```css
.marquee-track { display: flex; width: max-content; animation: scroll 30s linear infinite; }
@keyframes scroll { to { transform: translateX(-50%); } }
.marquee-track:hover { animation-play-state: paused; }
```
```html
<div class="marquee-viewport" style="overflow:hidden">
  <div class="marquee-track">
    <!-- items -->
    <!-- same items again, aria-hidden="true", for the seamless loop -->
  </div>
</div>
```
An arrow-controlled variant of this exact pattern (GSAP-driven, with prev/next buttons instead of pure CSS) is already built in `main10-clean/index.html`'s `.hero-badges-track` — use it as a working reference rather than building from scratch.

**Ambient float**
```css
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
.floating { animation: float 4s ease-in-out infinite; }
```

## Accessibility (apply alongside every recipe above)

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
